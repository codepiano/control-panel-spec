#!/usr/bin/env python3
"""Project-owned launchd adapter. Configuration contains identity, never credentials."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import time


class Service:
    def __init__(self, config, run=None):
        self.config = config
        self.deadline = time.monotonic() + 6
        self.start_timeout = config.get('startTimeoutSec', 30)
        if not isinstance(self.start_timeout, (int, float)) or isinstance(self.start_timeout, bool) or not 1 <= self.start_timeout <= 120:
            raise ValueError('startTimeoutSec must be between 1 and 120')
        self.label = config['label']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]+', self.label):
            raise ValueError('Invalid launchd label')
        self.plist = Path(config['plist']).expanduser().resolve()
        self.domain = 'gui/' + str(os.getuid())
        self.target = self.domain + '/' + self.label
        self.run = run or self.command
        with self.plist.open('rb') as stream:
            self.definition = plistlib.load(stream)
        if self.definition.get('Label') != self.label:
            raise ValueError('Plist label does not match configured service')
        probe = config.get('probe')
        if probe:
            if probe.get('type') != 'tunnel-client':
                raise ValueError('Unsupported readiness probe')
            args = self.definition.get('ProgramArguments', [])
            if len(args) < 2 or args[1] != 'run' or Path(args[0]).name != 'tunnel-client':
                raise ValueError('Expected tunnel-client run in plist')
            def flag(name):
                for i, arg in enumerate(args):
                    if arg == name and i + 1 < len(args):
                        return args[i + 1]
                    if arg.startswith(name + '='):
                        return arg.split('=', 1)[1]
                return None
            if flag('--profile') != probe['profile']:
                raise ValueError('Tunnel profile does not match configured service')

    def command(self, args):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(args, 6)
        return subprocess.run(args, capture_output=True, text=True, timeout=min(2, remaining))

    def job(self):
        result = self.run(['/bin/launchctl', 'print', self.target])
        if result.returncode:
            if 'Could not find service' in result.stderr:
                return None
            raise RuntimeError('Unable to query launchd service')
        match = re.search(r'^\s*path = (.+)$', result.stdout, re.M)
        if not match or Path(match[1]).resolve() != self.plist:
            raise ValueError('Loaded launchd job belongs to a different plist')
        match = re.search(r'^\s*pid = (\d+)\s*$', result.stdout, re.M)
        return int(match[1]) if match else 0

    def readiness(self, pid):
        if not self.config.get('probe'):
            return 'unknown'
        result = self.run(['/usr/sbin/lsof', '-nP', '-a', '-p', str(pid), '-iTCP', '-sTCP:LISTEN', '-Fn'])
        ports = {line[1:].rsplit(':', 1)[1] for line in result.stdout.splitlines()
                 if re.fullmatch(r'n127\.0\.0\.1:\d+', line)}
        if result.returncode or len(ports) != 1:
            return 'unknown'
        executable = self.definition['ProgramArguments'][0]
        result = self.run([executable, 'health', '--port', ports.pop(), '--pid', str(pid),
                           '--require-control-plane-poll', '--json'])
        try:
            health = json.loads(result.stdout)
            ready = (result.returncode == 0 and health.get('result') == 'ok'
                     and all(health.get(key, {}).get('ok') is True
                             for key in ('healthz', 'readyz', 'control_plane_poll')))
            return 'ready' if ready else 'unready'
        except (ValueError, AttributeError):
            return 'unknown'

    def status(self):
        pid = self.job()
        if not pid:
            return {'status': 'stopped', 'readiness': 'unknown', 'processMode': 'external'}, 1
        try:
            readiness = self.readiness(pid)
        except (OSError, subprocess.TimeoutExpired):
            readiness = 'unknown'
        # Running is process state. Readiness must not claim remote MCP availability.
        return {'status': 'running', 'pid': pid, 'readiness': readiness, 'processMode': 'external'}, 0

    def mutate(self, args):
        if self.run(['/bin/launchctl', *args]).returncode:
            raise RuntimeError('launchd action failed; inspect this service with launchctl')

    def start(self):
        self.deadline = time.monotonic() + self.start_timeout
        initial_pid = self.job()
        created = False
        try:
            if initial_pid is None:
                # Only an acknowledged bootstrap establishes ownership for cleanup.
                # An ambiguous failure may be a racing operator's job; preserve it.
                try:
                    self.mutate(['bootstrap', self.domain, str(self.plist)])
                except (RuntimeError, OSError, subprocess.TimeoutExpired):
                    raise RuntimeError('Bootstrap failed or timed out; ownership uncertain; inspect launchd state') from None
                created = True
            elif not initial_pid:
                self.mutate(['kickstart', self.target])
            while time.monotonic() < self.deadline:
                pid = self.job()
                if pid:
                    try:
                        ready = not self.config.get('probe') or self.readiness(pid) == 'ready'
                    except (OSError, subprocess.TimeoutExpired):
                        ready = False
                    if ready:
                        return
                time.sleep(.2)
            raise RuntimeError('Startup readiness deadline exceeded')
        except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
            # Roll back only a job newly loaded by this attempt. Existing jobs remain owned
            # by their original supervisor policy, even when their readiness cannot be proven.
            if created:
                try:
                    self.stop()
                except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired):
                    raise RuntimeError('Startup failed; cleanup failed or ownership changed; inspect launchd state') from None
                raise RuntimeError('Startup failed; newly loaded launchd job was unloaded') from None
            if initial_pid is None:
                raise RuntimeError('Bootstrap failed or timed out; ownership uncertain; inspect launchd state') from None
            raise RuntimeError('Startup failed; pre-existing launchd job was preserved') from None

    def stop(self):
        self.deadline = time.monotonic() + 6
        if self.job() is None:
            return
        # bootout removes the job, so KeepAlive and kickstart-only recovery cannot revive it.
        self.mutate(['bootout', self.target])
        for _ in range(20):
            if self.job() is None:
                return
            time.sleep(.2)
        raise RuntimeError('launchd service did not unload within the stop deadline')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'status', 'restart'))
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        config = json.loads((Path(__file__).resolve().parent.parent / 'launchd.json').read_text())
        service = Service(config)
        if args.action == 'restart':
            service.stop()
            service.start()
        elif args.action != 'status':
            getattr(service, args.action)()
        if args.action in ('start', 'restart'):
            print('running · 本地就绪已确认' if config.get('probe') else 'running · 进程已确认')
            return 0
        if args.action == 'stop':
            print('stopped (launchd job unloaded)')
            return 0
        result, code = service.status()
        if args.json:
            print(json.dumps(result))
        else:
            state = {'ready': '就绪', 'unready': '未就绪', 'unknown': '未知'}[result['readiness']]
            print('{} · PID {} · 本地就绪检查：{}'.format(result['status'], result.get('pid', '—'), state))
        return code
    except (KeyError, ValueError, OSError, plistlib.InvalidFileException) as error:
        print('Invalid service configuration ({})'.format(type(error).__name__))
        return 2
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error) if isinstance(error, RuntimeError) else 'Service query/action timed out')
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
