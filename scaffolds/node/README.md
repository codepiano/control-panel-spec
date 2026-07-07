# Node Scaffold

This scaffold is for Node.js or TypeScript projects that already use a shell launcher or an HTTP server.

Expected pieces:

- `control-panel.json.tmpl`
- `scripts/*.sh.tmpl`
- `metrics-server.mjs.tmpl`

The generated project should prefer a local `metricsUrl` over process guessing.
Use `projectStartCommand`, `projectStopCommand`, and `projectStatusCommand` as the command inputs for the shell templates.
