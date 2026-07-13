# Project Tooling Spec

Version: `1.1`

This document is the canonical contract for projects that want a standard control surface and for AIs that generate project lifecycle scripts.

The design goals are:

- One manifest format for discovery and control
- One metrics contract for runtime status and resource usage
- One Node.js scaffold repository that stays small and reusable

## 1. Scope

This spec covers:

- Discovering project roots from `control-panel.json`
- Generating init, install, start, stop, status, restart, homepage, and metrics integrations
- Exposing runtime status through a standard HTTP endpoint
- Supporting the Node.js scaffold under one repository

This spec does not cover:

- Deployment orchestration
- Remote cluster management
- UI implementation details
- Build or release pipelines

## 2. Repository Layout

Recommended top-level layout:

```text
project-tooling/
  spec/
    PROJECT_TOOLING_SPEC.md
  scaffolds/
    node/
  examples/
```

The `examples/` directory may include both metrics payload examples and a reference `control-panel.json` manifest.

The repository currently ships only the Node.js scaffold. If additional runtimes are added later, they should preserve the same conceptual shape:

- `control-panel.json`
- `scripts/`
- `metrics` endpoint or adapter
- Node.js support files such as `package.json`, `tsconfig.json`, or framework-specific config when needed

## 3. Project Manifest

Every controllable project should expose a `control-panel.json` file at the project root.

### 3.1 Required fields

- `name`: display name
- `workingDirectory`: directory used when running commands

### 3.2 Recommended fields

- `id`: stable identifier
- `startCommand`: lifecycle start command
- `installCommand`: lifecycle install command
- `initCommand`: lifecycle initialization command
- `stopCommand`: lifecycle stop command
- `uninstallCommand`: lifecycle uninstall command
- `statusCommand`: lifecycle status command
- `restartCommand`: lifecycle restart command
- `openHomepageCommand`: command that opens the project homepage
- `frontendUrl`: canonical local or deployed frontend URL
- `homepageUrl`: project homepage or repo URL fallback
- `metricsUrl`: HTTP endpoint that returns runtime metrics JSON
- `databasePath`: path to the project-owned SQLite database file when the project uses SQLite
- `notes`: short operator note
- `specUrl`: link to the project's own spec if it has one
- `scripts`: optional object mapping lifecycle names to relative script paths
- `scripts.init`, `scripts.install`, `scripts.start`, `scripts.stop`, `scripts.status`, `scripts.restart`, `scripts.uninstall`, `scripts.openHomepage`: recommended script keys

### 3.3 Resolution order

When both direct commands and script paths are present, prefer the project-authored script path.

Recommended precedence:

- `scripts.init` before `initCommand`
- `scripts.install` before `installCommand`
- `scripts.start` before `startCommand`
- `scripts.stop` before `stopCommand`
- `scripts.status` before `statusCommand`
- `scripts.restart` before `restartCommand`
- `scripts.uninstall` before `uninstallCommand`
- `scripts.openHomepage` before `openHomepageCommand`

For opening the homepage:

1. `frontendUrl`
2. Project-authored homepage script
3. `homepageUrl`
4. Package metadata or git remote inference

The homepage resolution must always prefer `frontendUrl` when it exists. Do not promote a fallback URL above it.

For metrics:

1. `metricsUrl`
2. Project-authored status script if it returns structured JSON
3. No metric display if neither is available

The control surface should use project-authored metrics first. It should not guess runtime status from process tables, open ports, or other inferred host-state heuristics when a project-provided endpoint is available.

## 4. Lifecycle Scripts

Generated scripts should be:

- Minimal
- Idempotent where practical
- Explicit about working directory
- Safe on macOS

### 4.1 Init

The init script should prepare a fresh checkout for first use.

Typical init work includes:

- Creating local config files
- Bootstrapping environment variables
- Generating folders or databases the project expects
- Delegating to the project's own one-time setup command

The init script should be safe to rerun and should not start the service unless the project explicitly treats setup and start as the same action.

### 4.2 Install

The install script should install project dependencies or plugins.

Typical install work includes:

- Running the package manager install step
- Fetching language-specific dependencies
- Preparing vendored assets needed before startup

The install script should not start the service. It should be idempotent where practical and should avoid destructive cleanup.

### 4.3 Start

The start script should start exactly the project service or launcher the operator expects.

### 4.4 Stop

The stop script should stop only the service managed by the project.

### 4.5 Status

The status script should return `0` for running, nonzero for stopped or degraded.

### 4.6 Restart

The restart script should call stop then start.

### 4.7 Uninstall

The uninstall script should remove project-local runtime artifacts or unregister project-specific setup when the project supports that flow.

Typical uninstall work includes:

- Removing generated config files
- Cleaning up local caches or temp files created by the install/init flow
- Reversing project-owned registrations

The uninstall script should be safe to run when the project is already absent or partially removed. It should fail only when the project intentionally requires manual intervention.

### 4.8 Homepage

The homepage script should open the project frontend URL when one exists, otherwise fall back to the canonical project page.

### 4.9 Scaffold inputs

Scaffold templates should keep wrapper paths and project commands separate.

Recommended template inputs:

- `workingDirectory`: project root used by the wrapper scripts
- `projectInitCommand`: actual init command for the project setup flow
- `projectInstallCommand`: actual install command for dependency setup
- `projectStartCommand`: actual start command for the project service or launcher
- `projectStopCommand`: actual stop command for the project service or launcher
- `projectStatusCommand`: actual status command or probe
- `projectUninstallCommand`: actual uninstall command for cleanup or deregistration
- `frontendUrl`: preferred homepage target
- `homepageUrl`: fallback homepage target

This separation keeps `control-panel.json` stable while still allowing the generated shell scripts to invoke the real project-specific command.

## 5. Metrics Contract

Projects that expose runtime metrics should provide:

- An HTTP endpoint, usually `GET /control-panel/metrics`
- JSON only
- Stable field names
- Timestamps in ISO 8601

### 5.1 Required response shape

```json
{
  "status": "running",
  "updatedAt": "2026-07-08T09:00:00.000Z"
}
```

### 5.2 Recommended response shape

```json
{
  "status": "running",
  "pid": 12345,
  "updatedAt": "2026-07-08T09:00:00.000Z",
  "uptimeSec": 120,
  "memory": {
    "rssBytes": 123456789,
    "heapUsedBytes": 45678901,
    "heapTotalBytes": 67890123
  },
  "cpu": {
    "percent": 12.4
  },
  "processes": [
    {
      "pid": 12345,
      "rssBytes": 123456789,
      "cpu": {
        "percent": 12.4
      }
    }
  ]
}
```

### 5.3 Field guidance

- `pid`: numeric process id of the primary service process
- `uptimeSec`: process uptime in seconds, measured by the service itself
- `memory.rssBytes`: resident memory in bytes when the runtime can measure it reliably
- `memory.heapUsedBytes`: heap used in bytes when the runtime has a heap concept
- `memory.heapTotalBytes`: total heap in bytes when the runtime has a heap concept
- `cpu.percent`: current or recent CPU percentage as reported by the service
- `processes`: optional array for multi-process services or worker pools

Prefer bytes in the contract and let the consumer decide how to render units. If a runtime cannot measure a field accurately, omit it instead of guessing.

### 5.4 Memory rules

- Prefer bytes in the contract
- Let the UI decide whether to render MB or GB
- For multi-process apps, include a `processes` array
- If the project cannot measure memory precisely, omit the field rather than guessing

### 5.5 CPU rules

- `cpu.percent` should come from the project runtime or its own metrics collector
- If the runtime only knows process-local CPU and not system-wide CPU, that is acceptable as long as the field meaning is stable within the project
- Do not synthesize CPU usage from shell wrappers or host heuristics

## 6. Node.js Guidance

- Use `node`, `npm`, `pnpm`, or `corepack` only if the repository already uses them
- Keep the frontend and backend separated when the product has both a UI and an API
- Put the frontend under `frontend/` and the backend under `backend/`
- Keep SQLite data, migrations, and seeds under `db/`
- Add the metrics endpoint to the backend service when the app already exposes HTTP
- If the app is a desktop shell, keep the launcher and the runtime service separate when possible
- Use `databasePath` to point at the project-owned SQLite file when the project uses SQLite

## 7. Scaffold Policy

The Node scaffold should include:

- A manifest template
- Lifecycle script templates
- A metrics adapter or example service
- A README explaining the common project layout and runtime-specific inputs

The scaffold should keep its output shape aligned:

- `control-panel.json`
- `scripts/init.sh`
- `scripts/install.sh`
- `scripts/start.sh`
- `scripts/stop.sh`
- `scripts/status.sh`
- `scripts/restart.sh`
- `scripts/uninstall.sh`
- `scripts/open-homepage.sh`
- a metrics server or adapter that serves `GET /control-panel/metrics`

For Node projects that separate frontend and backend, `frontendUrl` should point at the frontend surface and the metrics endpoint should live with the backend.

## 8. Output Contract

An AI using this spec should return one of:

- A unified diff
- A file manifest JSON with full file contents

The patch should only include files that changed.

## 9. Minimum Acceptance

A project is ready when:

- `control-panel.json` exists
- Init/install/start/stop/status/uninstall work on macOS when the project supports them
- Homepage opens the right place, with `frontendUrl` preferred when present
- Metrics are available through the standard endpoint when needed
- Metrics come from the project itself instead of being inferred from host process state
- The manifest is stable enough for another AI to reproduce the setup
