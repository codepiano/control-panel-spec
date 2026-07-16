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

The generated project should prefer a local `metricsUrl` over process guessing. Its lifecycle
scripts own only the processes started for that project, using a PID file, process group, or
equivalent project-specific handle where needed.
Use `projectInitCommand`, `projectInstallCommand`, `projectStartCommand`, `projectStopCommand`, `projectStatusCommand`, and `projectUninstallCommand` as the command inputs for the shell templates.
If the project uses SQLite, set `databasePath` to the project-owned database file under `db/`.
Set `surfaceType` to `web`, `desktop`, `hybrid`, or `service`. Keep the existing
`open-homepage.sh` filename if compatibility is useful; for desktop projects it launches or
focuses the app through `appLaunchCommand` or `appUrl` instead of opening a browser homepage.
Set `runtimeMode` to `development` when the project intentionally runs Electron from source;
this does not prevent management. Use `processMode: managed` with a project PID/process-group
handle, or `processMode: external` with a supervisor such as `launchd` or PM2. Use `observed` only
when the app is started outside the project tooling and lifecycle control is intentionally unavailable.
