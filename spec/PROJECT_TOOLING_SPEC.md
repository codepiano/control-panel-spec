# Project Tooling Spec

Version: `1.6`

This document is the canonical contract for projects that want a standard control surface and for AIs that generate project lifecycle scripts.

The design goals are:

- One manifest format for discovery and control
- One metrics contract for runtime status and resource usage
- One reusable AI Skill for project integration

## 1. Scope

This spec covers:

- Discovering project roots from `control-panel.json`
- Generating init, install, start, stop, status, restart, entry-point, and metrics integrations
- Exposing runtime status through a standard HTTP endpoint
- Supporting Node.js, TypeScript, and Electron project integration

This spec does not cover:

- Deployment orchestration
- Remote cluster management
- UI implementation details
- Build or release pipelines

## 2. Skill Package Layout

Recommended top-level layout:

```text
project-tooling/
  SKILL.md
  agents/
    openai.yaml
  spec/
    PROJECT_TOOLING_SPEC.md
  scripts/
    check-spec-sync.sh
```

The Skill package contains the contract and validation workflow. Generated project files belong in
the target project, not in this repository. If additional runtimes are supported later, they should
preserve the same conceptual shape:

- `control-panel.json`
- `scripts/`
- `metrics` endpoint or adapter
- runtime-specific project files when needed

## 3. Project Manifest

Every controllable project should expose a `control-panel.json` file at the project root.

### 3.1 Required fields

- `name`: display name
- `workingDirectory`: directory used when running commands

### 3.2 Recommended fields

- `id`: stable identifier
- `icon`: project-relative path to the icon used by compatible control surfaces
- `startCommand`: lifecycle start command
- `installCommand`: lifecycle install command
- `initCommand`: lifecycle initialization command
- `stopCommand`: lifecycle stop command
- `uninstallCommand`: lifecycle uninstall command
- `statusCommand`: lifecycle status command
- `restartCommand`: lifecycle restart command
- `openHomepageCommand`: legacy command for opening the project entry point
- `openEntryCommand`: command that opens, launches, or focuses the project's primary user entry
- `surfaceType`: primary surface type: `web`, `desktop`, `hybrid`, or `service`
- `runtimeMode`: active runtime packaging mode: `development` or `packaged`
- `processMode`: process ownership mode: `managed`, `external`, or `observed`
- `processManager`: process owner such as `project-script`, `launchd`, `pm2`, or `docker`
- `pidFile`: project-relative PID file when the project manages a process directly
- `frontendUrl`: canonical local or deployed frontend URL
- `appUrl`: URL or deep link for an application entry when the project is not primarily a browser frontend
- `appLaunchCommand`: command that launches or focuses a desktop application
- `homepageUrl`: project homepage or repo URL fallback
- `metricsUrl`: HTTP endpoint that returns runtime metrics JSON
- `databasePath`: path to the project-owned SQLite database file when the project uses SQLite
- `notes`: short operator note
- `specUrl`: link to the project's own spec if it has one
- `scripts`: optional object mapping lifecycle names to relative script paths
- `scripts.init`, `scripts.install`, `scripts.start`, `scripts.stop`, `scripts.status`, `scripts.restart`, `scripts.uninstall`, `scripts.openEntry`: recommended script keys
- `scripts.openHomepage`: backwards-compatible alias for `scripts.openEntry`

The project owns the processes started by its lifecycle commands. A project script must only
start, stop, inspect, or restart processes belonging to that project. Prefer a project-owned
PID file, process group, or equivalent supervisor handle; do not use broad host-wide commands
such as `pkill node`.

`runtimeMode` describes how the application is launched, not whether it is controllable. A
development Electron application is still eligible for full lifecycle control if its dev command
is run in the background and tracked by the project. `runtimeMode: packaged` is not required for
integration.

### 3.3 Project icon

`icon` identifies the project visually across compatible control surfaces. It must be a relative
path resolved from the directory containing `control-panel.json`; absolute paths, URLs, data URLs,
and paths that escape the project root are invalid. Recommended formats are PNG, JPEG, and WebP.
Use a square source image with a transparent or simple background, ideally at least `128 x 128`
pixels. The consumer decides the rendered size and may convert the image to a safe local format.

The icon is presentation metadata only. Its absence must never affect project discovery or
lifecycle control. A control surface may generate a fallback icon or keep a user-local icon choice
in its own preferences. Such a local choice is a consumer display preference, not another copy of
the project manifest and not a portable project setting.

### 3.4 Resolution order

When both direct commands and script paths are present, prefer the project-authored script path.

Recommended precedence:

- `scripts.init` before `initCommand`
- `scripts.install` before `installCommand`
- `scripts.start` before `startCommand`
- `scripts.stop` before `stopCommand`
- `scripts.status` before `statusCommand`
- `scripts.restart` before `restartCommand`
- `scripts.uninstall` before `uninstallCommand`
- `scripts.openEntry` before `openEntryCommand`
- `scripts.openHomepage` before `openHomepageCommand`

For opening the primary entry point:

1. Project-authored entry script
2. `frontendUrl` for `web` or `hybrid` projects
3. `appUrl` for `desktop` or `hybrid` projects
4. `appLaunchCommand` for application-only projects
5. `homepageUrl`
6. Package metadata or git remote inference

`openHomepageCommand` remains supported as a compatibility alias. For new projects,
`openEntryCommand` and `scripts.openEntry` are preferred. An entry script may launch or focus
an application, open a deep link, or open a browser URL depending on `surfaceType`.

### 3.5 Graphical manifest editing

`control-panel.json` is the single source of truth for a discovered project. A control surface may
provide a graphical editor that reads and atomically writes that same manifest; it must not create
a separate per-project override layer.

The editor may expose only presentation fields: `name`, `icon`, `frontendUrl` (including its port),
and `notes`. It must preserve every other manifest field unchanged. Lifecycle commands, script paths,
working directory, process ownership, and runtime fields are specification-owned and must not be
editable through the control surface. At minimum, validate a non-empty display name, an `http` or
`https` `frontendUrl` when supplied, a port between `1` and `65535` when the URL contains one,
and bounded single-line text inputs.

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
For `managed` and `external` modes it must be non-blocking after the process or supervisor has
accepted the start request. It should be idempotent: starting an already-running project should
not create a second instance.

### 4.4 Stop

The stop script should stop only the service managed by the project.
It should succeed when the project is already stopped. A managed process should receive a graceful
termination signal first, followed by a bounded wait and forceful termination only for the same
verified process or process group.

### 4.5 Status

The status script should return the following exit codes:

- `0`: running or healthy
- `1`: stopped, failed, or degraded
- `2`: unsupported or invalid process-control configuration
- `3`: state unknown because the process is externally started and cannot be verified

When the control surface needs machine-readable output, the script should print the same status
vocabulary used by the metrics contract rather than human-only prose.

### 4.6 Restart

The restart script should call stop then start.

### 4.7 Uninstall

The uninstall script should remove project-local runtime artifacts or unregister project-specific setup when the project supports that flow.

Typical uninstall work includes:

- Removing generated config files
- Cleaning up local caches or temp files created by the install/init flow
- Reversing project-owned registrations

The uninstall script should be safe to run when the project is already absent or partially removed. It should fail only when the project intentionally requires manual intervention.

### 4.8 Process ownership

Lifecycle commands are the project's process-management boundary:

- `start` starts only the project's declared service or application processes
- `stop` stops only those processes and should be safe when they are already stopped
- `status` reports the project-owned runtime state without claiming ownership of unrelated processes
- `restart` performs the equivalent of `stop` followed by `start`

The three process modes have distinct contracts:

- `managed`: project scripts own the process. `start` must return after recording a usable handle,
  and `stop`, `status`, and `restart` must operate on that handle.
- `external`: a declared supervisor owns the process. Project scripts delegate to that supervisor
  and must not independently scan or kill the process.
- `observed`: the project does not control the process. Unsupported lifecycle actions must return
  a clear unsupported result, and unavailable runtime state must be reported as `unknown`.

For development-mode Electron apps, do not leave `electron .` attached to the lifecycle command's
foreground terminal. Use a project-specific PID file/process group, or delegate to an external
supervisor. If the app is started manually from an IDE or shell, use `observed` until a reliable
status or metrics source is available.

The development and packaged launchers should share the same lifecycle wrapper interface. The
active launcher may be selected by `runtimeMode`, an environment variable, or a project-owned
configuration file, but `start`, `stop`, `status`, and `restart` must retain the same semantics.

For desktop or hybrid applications, the launcher process and any backend service may be managed
as one project runtime. The manifest and metrics response should identify the primary process and
may include child processes in `processes`.

### 4.9 Primary entry

The primary-entry script should do the action appropriate to the project surface:

- `web`: open `frontendUrl`
- `desktop`: launch or focus the application using `appLaunchCommand` or `appUrl`
- `hybrid`: open the frontend when available, otherwise launch or focus the application
- `service`: report that no interactive entry is available, unless `appUrl` or `homepageUrl` is explicitly configured

`openEntry` is not a second process supervisor. It should focus or open an already-running app and
may delegate to the idempotent `start` flow when the project explicitly supports that behavior.

The existing `open-homepage.sh` filename may remain as a compatibility wrapper, but its behavior
must follow this primary-entry contract.

### 4.10 Scaffold inputs

Scaffold templates should keep wrapper paths and project commands separate.

Recommended template inputs:

- `workingDirectory`: project root used by the wrapper scripts
- `projectInitCommand`: actual init command for the project setup flow
- `projectInstallCommand`: actual install command for dependency setup
- `projectStartCommand`: actual start command for the project service or launcher
- `projectStopCommand`: actual stop command for the project service or launcher
- `projectStatusCommand`: actual status command or probe
- `projectUninstallCommand`: actual uninstall command for cleanup or deregistration
- `surfaceType`: primary project surface
- `runtimeMode`: active `development` or `packaged` launch mode
- `processMode`: `managed`, `external`, or `observed`
- `processManager`: owner of the runtime process
- `pidFile`: project-relative process handle file when applicable
- `frontendUrl`: preferred web frontend target
- `appUrl`: application URL or deep link
- `appLaunchCommand`: application launch or focus command
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
  "runtimeMode": "development",
  "processMode": "managed",
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

- `status`: use `running`, `stopped`, `starting`, `stopping`, `failed`, or `unknown`; use
  `unknown` when an observed application cannot be verified
- `runtimeMode`: active packaging mode, normally `development` or `packaged`
- `processMode`: process ownership mode from the manifest
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

### 6.1 Electron development example

An Electron project that is normally run from source can use the same contract as a packaged app:

```json
{
  "surfaceType": "desktop",
  "runtimeMode": "development",
  "processMode": "managed",
  "processManager": "project-script",
  "pidFile": ".runtime/electron.pid",
  "startCommand": "./scripts/start.sh",
  "stopCommand": "./scripts/stop.sh",
  "statusCommand": "./scripts/status.sh",
  "restartCommand": "./scripts/restart.sh",
  "openEntryCommand": "./scripts/open-homepage.sh"
}
```

In this mode, `start.sh` may invoke the source-based Electron command, but it must detach it from
the caller, record the process handle, and capture logs in a project-owned location. `stop.sh`
must validate that handle before sending signals. The scripts must not match processes by a broad
name such as `electron` or `node`.

If the same project sometimes runs a packaged application, keep the wrapper paths unchanged and
switch only the project-owned launcher configuration or `runtimeMode` value.

## 7. Skill Execution Policy

The Skill should inspect the target project before generating files. It may generate a manifest,
lifecycle scripts, a metrics adapter, or runtime-specific support files, but it must not assume a
fixed output template. Generated output should remain aligned with:

- `control-panel.json`
- project-owned lifecycle scripts
- a primary-entry action appropriate to `surfaceType`
- a metrics endpoint or explicit unsupported/unknown state

The Skill should prefer existing project commands and preserve project-specific conventions. It
should return only the files that changed and include validation results.

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
- The primary entry opens, launches, or focuses the right place for the declared `surfaceType`
- Metrics are available through the standard endpoint when needed
- Metrics come from the project itself instead of being inferred from host process state
- The manifest is stable enough for another AI to reproduce the setup
