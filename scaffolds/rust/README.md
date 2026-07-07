# Rust Scaffold

This scaffold is for Rust services that can expose a tiny HTTP metrics endpoint.

Expected pieces:

- `control-panel.json.tmpl`
- `Cargo.toml.tmpl`
- `scripts/*.sh.tmpl`
- `metrics-server.rs.tmpl`

Prefer a lightweight in-process route and keep the JSON fields stable. Use `projectStartCommand`, `projectStopCommand`, and `projectStatusCommand` as the command inputs for the shell templates.
