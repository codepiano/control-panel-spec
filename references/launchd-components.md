# Project-owned launchd components

Read spec section 4.9. Inspect the existing plist, parent scripts and recovery hooks first.
Do not print profile files, environment secrets or raw health responses.

Generate without starting or changing the LaunchAgent:

```bash
python3 /path/to/project-tooling/scripts/scaffold-launchd.py \
  --project /absolute/product \
  --child tooling/tunnel \
  --name "Product Tunnel" \
  --label com.example.product-tunnel \
  --tunnel-profile product
```

The parent must already have a manifest. Existing children and metadata are preserved; existing
destination directories, absolute child paths and symlink escapes are rejected. Omit
`--tunnel-profile` for a generic LaunchAgent without a tunnel-client readiness check.

The generated directory has `control-panel.json`, `launchd.json`, a README, project-owned Python
adapter, and executable start/stop/status/restart wrappers. It needs Python 3.9+ on macOS.
The installed Skill is needed only to generate/update files. Provision the referenced LaunchAgent
and its credentials separately; the generator never installs or starts them. Missing or mismatched
configuration fails visibly. No HTTP metrics endpoint is provided. There is no interactive entry.

Validate the generator and adapter in an outside-repo copy with fake launchctl/health responses:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Parse both manifests, check wrapper executability and `bash -n`, verify child ownership through
actual discovery, and run only read-only status against a live job. Do not test lifecycle mutations
on active tunnels. Process running, local readiness, and remote MCP tool success are separate claims.
