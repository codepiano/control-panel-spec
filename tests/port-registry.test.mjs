import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
const exec = promisify(execFile);
const script = fileURLToPath(new URL('../scripts/port-registry.mjs', import.meta.url));

test('spec retrieval is offline and remote origins are rejected before session access', async () => {
  const { stdout } = await exec(process.execPath, [script, 'spec'], { env: { ...process.env, CONTROL_PANEL_URL: 'http://unavailable.invalid' } });
  assert.ok(stdout.startsWith('# Project Tooling Spec'));
  await assert.rejects(exec(process.execPath, [script, 'list', '--panel-url', 'http://example.com']), (error) => /loopback/.test(error.stderr));
});

test('helper retrieves a session, forwards registration arguments and surfaces API failures', async () => {
  const requests = [];
  const server = http.createServer(async (req, res) => {
    res.setHeader('Content-Type', 'application/json');
    if (req.url === '/api/session') { res.end(JSON.stringify({ token: 'test-session' })); return; }
    assert.equal(req.headers['x-control-panel-token'], 'test-session');
    let body = ''; for await (const chunk of req) body += chunk;
    const payload = JSON.parse(body); requests.push({ route: req.url, payload });
    if (req.url === '/api/get-port-allocations') { res.end(JSON.stringify({ data: { rows: [], suggestions: [4323] } })); return; }
    if (payload.args[0].ports?.includes(4318)) { res.statusCode = 400; res.end(JSON.stringify({ error: 'already reserved' })); return; }
    res.end(JSON.stringify({ data: { ...payload.args[0], ports: [4323, 4324], status: 'reserved' } }));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const url = `http://127.0.0.1:${server.address().port}`;
  const run = (...args) => exec(process.execPath, [script, ...args, '--panel-url', url]);
  try {
    const { stdout } = await run('register', '--project', '/tmp/project', '--count', '2');
    assert.equal(JSON.parse(stdout).status, 'reserved');
    assert.deepEqual(requests[0].payload.args, [{ projectDir: '/tmp/project', count: 2 }]);
    await run('list');
    assert.equal(requests[1].route, '/api/get-port-allocations');
    await assert.rejects(run('register', '--project', '/tmp/project', '--ports', '4318'), (error) => /already reserved/.test(error.stderr));
    await assert.rejects(run('register', '--project', '/tmp/project', '--ports', '4323', '--count', '1'), (error) => /either/.test(error.stderr));
  } finally { await new Promise((resolve) => server.close(resolve)); }
});
