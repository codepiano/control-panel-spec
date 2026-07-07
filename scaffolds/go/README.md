# Go Scaffold

This scaffold is for Go services that can expose a tiny HTTP metrics endpoint.

Expected pieces:

- `control-panel.json.tmpl`
- `scripts/*.sh.tmpl`
- `metrics-server.go.tmpl`

Prefer a small in-process HTTP handler and keep the runtime metrics explicit. Use `projectStartCommand`, `projectStopCommand`, and `projectStatusCommand` as the command inputs for the shell templates.
