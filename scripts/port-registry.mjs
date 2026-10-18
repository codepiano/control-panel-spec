#!/usr/bin/env node
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const usage = `Usage:
  node scripts/port-registry.mjs spec
  node scripts/port-registry.mjs list [--panel-url http://127.0.0.1:4310]
  node scripts/port-registry.mjs register --project /absolute/project [--count 1 | --ports 4323,4324]
Options: --panel-url (or CONTROL_PANEL_URL); --count allocates, --ports requests exact values.
Create control-panel.json with name and workingDirectory before registration.`;

async function main() {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: {
    project: { type: 'string' }, count: { type: 'string' }, ports: { type: 'string' },
    'panel-url': { type: 'string' }, help: { type: 'boolean', short: 'h' },
  } });
  if (values.help) { console.log(usage); return; }
  const [action] = positionals;
  if (positionals.length !== 1 || !['spec', 'list', 'register'].includes(action)) throw new Error(usage);
  if (action === 'spec') {
    process.stdout.write(fs.readFileSync(fileURLToPath(new URL('../spec/PROJECT_TOOLING_SPEC.md', import.meta.url)), 'utf8'));
    return;
  }
  const url = new URL(values['panel-url'] || process.env.CONTROL_PANEL_URL || 'http://127.0.0.1:4310');
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new Error('Panel URL must be a loopback HTTP origin');
  const request = async (route, options) => {
    const response = await fetch(new URL(route, url), { ...options, signal: AbortSignal.timeout(60000), redirect: 'error' });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    return result;
  };
  let args = [];
  if (action === 'register') {
    if (!values.project) throw new Error('--project is required');
    if (values.count !== undefined && values.ports !== undefined) throw new Error('Use either --count or --ports');
    const input = { projectDir: values.project };
    if (values.ports !== undefined) {
      if (!/^\d+(,\d+)*$/.test(values.ports)) throw new Error('--ports must be comma-separated integers');
      input.ports = values.ports.split(',').map(Number);
    } else if (values.count !== undefined) {
      if (!/^\d+$/.test(values.count)) throw new Error('--count must be an integer');
      input.count = Number(values.count);
    }
    args = [input];
  }
  const { token } = await request('/api/session');
  if (typeof token !== 'string' || !token) throw new Error('Invalid panel session');
  const { data } = await request(`/api/${action === 'list' ? 'get-port-allocations' : 'register-project-ports'}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Control-Panel-Token': token }, body: JSON.stringify({ args }),
  });
  console.log(JSON.stringify(data, null, 2));
}
main().catch((error) => { console.error(error.message); process.exitCode = 1; });
