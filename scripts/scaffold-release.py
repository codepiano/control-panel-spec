#!/usr/bin/env python3
"""Install the reviewed release adapter and a project-authored recipe, without launching anything."""
import argparse
import json
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('project', type=Path)
parser.add_argument('--config', required=True, type=Path, help='reviewed project-specific recipe JSON')
args = parser.parse_args()
root = args.project.resolve()
manifest_path = root / 'control-panel.json'
manifest = json.loads(manifest_path.read_text())
recipe = json.loads(args.config.read_text())
if manifest.get('kind') == 'collection':
    parser.error('collections do not own a runtime')
for action in ['start', 'stop', 'status']:
    command = recipe.get('legacy', {}).get(action)
    if not isinstance(command, list) or not command or any(not isinstance(v, str) for v in command):
        parser.error('legacy.' + action + ' must be a nonempty argv array')
for key in ['persistent', 'runtimeFiles', 'exclude', 'outputs']:
    for value in recipe.get(key, []):
        path = Path(value)
        if not value or path.is_absolute() or '..' in path.parts or str(path) == '.':
            parser.error(key + ' must contain project-relative descendant paths')
destination = root / 'tooling/release'
destination.mkdir(parents=True, exist_ok=True)
shutil.copy2(Path(__file__).resolve().parents[1] / 'templates/release/adapter.py', destination / 'adapter.py')
(destination / 'config.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
(root / 'scripts').mkdir(exist_ok=True)
scripts = manifest.setdefault('scripts', {})
for action in ['version', 'prepare', 'activate', 'start', 'stop', 'status', 'restart']:
    script = root / 'scripts' / ('release-' + action + '.sh')
    script.write_text('#!/bin/sh\nset -eu\nSCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec python3 "$SCRIPT_DIR/../tooling/release/adapter.py" ' + action + ' "$@"\n')
    script.chmod(0o755)
    scripts[action] = './scripts/' + script.name
    if action in ['start', 'stop', 'status', 'restart']:
        manifest[action + 'Command'] = scripts[action]
manifest['release'] = {'protocol': 1, 'prepareTimeoutMs': 1800000, 'activateTimeoutMs': 240000}
temporary = manifest_path.with_suffix('.json.release-tmp')
temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
os.replace(temporary, manifest_path)
print('Release integration written; no build, start, stop or activation performed.')
