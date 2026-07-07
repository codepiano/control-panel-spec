# Node Scaffold

This scaffold is for Node.js or TypeScript projects that already use a shell launcher or an HTTP server.

Expected pieces:

- `control-panel.json.tmpl`
- `scripts/*.sh.tmpl`
- `metrics-server.mjs.tmpl`

Recommended project shape:

- `frontend/` for the UI
- `backend/` for the Node API and SQLite access
- `db/` for the SQLite database file, migrations, and seeds
- `scripts/` for lifecycle wrappers

The generated project should prefer a local `metricsUrl` over process guessing.
Use `projectStartCommand`, `projectStopCommand`, and `projectStatusCommand` as the command inputs for the shell templates.
If the project uses SQLite, set `databasePath` to the project-owned database file under `db/`.
