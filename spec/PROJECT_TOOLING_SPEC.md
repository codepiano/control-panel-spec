# Project Tooling Spec

Version: `1.10`

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
- `workingDirectory`: directory used when running commands; optional for `kind: collection`

### 3.2 Recommended fields

- `id`: stable identifier
- `icon`: project-relative path to the icon used by compatible control surfaces
- `startCommand`: lifecycle start command
- `startTimeoutMs`: wrapper completion deadline in milliseconds (Control Panel default 60000; accepted 100–300000)
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
- `ports`: unique local TCP port integers reserved by this runtime (see section 3.7)
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

### 3.6 Declared child projects and collections

Nested directories may encode a product's components, a monorepo, several Git checkouts,
or a local workspace. The outer manifest must describe that relationship explicitly instead
of relying on a consumer to recursively guess which directories represent services.

Additional fields:

- `kind`: `project` (default, backwards compatible) or `collection`.
- `children`: an array of child references. Each reference requires `path`, a relative directory
  containing another `control-panel.json`; optional `role` describes the component's purpose
  (for example `api`, `frontend`, `worker`), and `notes` explains why it belongs here.
- A collection requires `name`; `id` is recommended. It has no independent runtime and must
  not declare lifecycle commands, lifecycle script mappings, or automatic script fallbacks.
  A collection may provide `notes` and `icon` as presentation metadata. `workingDirectory`
  is unnecessary because the collection does not execute commands.
- A project may both own a runtime and declare children. Its lifecycle commands control only
  its own runtime; they must not also start/stop children exposed as independent services.

Example outer manifest for several Git checkouts and component services:

```json
{
  "id": "research-workspace",
  "name": "Research Workspace",
  "kind": "collection",
  "notes": "Repositories and services used together for research",
  "children": [
    { "path": "repos/library", "role": "knowledge", "notes": "Knowledge backend" },
    { "path": "repos/reader/apps/web", "role": "frontend", "notes": "Reading interface" },
    { "path": "repos/reader/services/indexer", "role": "worker", "notes": "Background indexing" }
  ]
}
```

Discovery and identity rules:

1. Resolve each `path` against the directory containing the outer manifest, never against
   `workingDirectory`. References identify directories; arbitrary manifest filenames and
   glob patterns are not supported. Paths must be non-empty, relative, and strict descendants
   of the outer directory both lexically and after resolving symbolic links. Absolute paths,
   the parent directory itself, escapes, and symbolic-link escapes are invalid.
2. Follow declared children recursively even if the referenced directory is deeper than the
   consumer's initial scan depth. Do not stop at Git repository boundaries; do not search
   unrelated nested directories or synthesize lifecycle commands from package scripts.
3. Each child retains its own `name`, `id`, working directory, scripts, runtime ownership, and
   presentation fields. Do not inherit lifecycle commands or working directories. The
   relationship metadata belongs to the reference in the outer manifest.
4. Discover each manifest only once even when initial scan roots overlap or a child is
   reachable through several declarations. Manifest location is the identity boundary;
   repeated `id` values in different directories do not merge services. Keep the first
   declared ownership chain and surface parent names and roles to the operator.
5. Consumers must bound traversal (Control Panel: at most 1,000 manifests and 32 relationship
   levels), prevent cycles, and surface invalid references, unreadable/malformed manifests,
   and unsupported kinds. One invalid child must not hide valid siblings.
6. Collections organize descendants into launchable sets; they are not stopped services and
   must not inflate service/runtime counts. Collection launch expands to descendant project
   runtimes, deduplicates them, skips running or transitioning services, and reports results
   per service. Declaration order is discovery order, not a dependency scheduler. Starting
   prerequisites or waiting for readiness is outside this extension.
7. Group names derived from ownership relationships are portable manifest facts. Operator
   favorites, tags, personal groups, and selections are local consumer preferences; they
   must not overwrite the structural `children` declarations.

Projects without `kind` or `children` preserve the existing single-project contract. A
consumer that supports only earlier spec versions will not understand collection manifests;
update that consumer before using `kind: collection`.

### 3.7 Local TCP port allocation

`ports` is an optional array of unique integers from 1 through 65535. It declares all local TCP
ports owned by this independently controlled runtime, including non-HTTP and secondary backend
listeners. Local HTTP(S) `frontendUrl` and `metricsUrl` ports also imply allocations; consumers
merge and deduplicate these with `ports`. Recognized local URL hosts are `localhost`, `127.0.0.1`,
`0.0.0.0`, `[::1]` and `[::]`; omitted HTTP/HTTPS ports mean 80/443. Remote URLs do not reserve
local ports. Collections have no runtime and must not declare port allocations.

A host registry must consider stopped services' allocations, not only live listeners. Reserve
before finalizing launch configuration and keep the reservation until an explicit configuration
change/removal. Independent runtimes must not claim the same local TCP port number. This version
uses conservative host-wide port ownership across bind addresses; it does not define UDP
allocation, remote-host allocation, reverse-proxy sharing or automatic service migration.

Lifecycle scripts must apply the declared ports to the real runtime. Fail visibly when a port
cannot be bound; do not silently switch to another number. Updating URLs alone is insufficient.
Metrics and frontend may share a port when served by the same runtime. A parent must not reserve
ports owned by its independently controlled children.

The portable contract is the manifest. Control Panel's optional local registration API serializes
allocation, validates existing manifests and live TCP listeners, writes `ports` to the project's
manifest and adds undiscovered project roots to host discovery. The skill's
`scripts/port-registry.mjs` helper implements spec retrieval, inventory and registration. See
`references/port-registration.md` for commands and endpoint parameters. Registration success is
not a readiness check or proof of listener ownership. Direct starts and offline edits remain
subject to the final bind result; startup need not require the registry to be online.

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

Start wrappers must exit after bounded startup confirmation. Consumers wait for completion rather
than treating a surviving launcher as success, then verify the declared status command. Keep
`starting` until these steps complete. A nonzero exit, timeout, or failed status confirmation is a
failed operation with its reason retained even if a service process remains running. A timed-out
launcher is terminated, but generic consumers must not kill inferred service processes or run an
unconditional stop command to clean up: ownership-aware cleanup belongs to the project adapter.
The default consumer wrapper deadline is 60 seconds; projects may set `startTimeoutMs` (100–300000)
when their bounded startup flow needs a different budget. Foreground dev servers need a detaching
wrapper; they no longer count as successful starts just because the command stays alive.

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

The restart script should call stop then start, and must not start if stopping failed.
Consumers must return stop failures to the caller instead of silently continuing a restart.

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

### 4.9 Project-owned externally supervised components

A tunnel, worker, sidecar or other supporting runtime belongs to its product project. Declare it
in the product's `children` with a role (for example `tunnel`), and keep its manifest and lifecycle
adapter under that project, for example `tooling/tunnel/`. It need not be a separate repository.
Do not create a detached host-only project entry or fold its process control into the parent scripts.
Each child uses `surfaceType: service`, `processMode: external`, and its actual `processManager`.

For a per-user macOS LaunchAgent, `launchd.json` identifies the exact `label` and `plist` path
(`~` expands to the current user's home). The project-owned adapter validates the plist Label and
the loaded job's plist path before mutations. Use `launchctl print gui/<uid>/<label>` as the process
authority. Start reuses a running job, bootstraps the existing plist if unloaded, or kickstarts a
loaded stopped job. Stop uses `bootout` and confirms unloading; killing its PID is insufficient for
KeepAlive jobs. Restart unloads then starts. Missing configuration, supervisor query failures and
rejected actions must fail visibly. Do not automatically create profiles, install credentials,
change login policy, or use broad process-name matches. Recovery helpers must respect an unloaded
job; they must not bootstrap a target deliberately stopped by the operator. RunAtLoad can start the
job again on a future login; stopping is not uninstalling or disabling login startup.

The reusable `scripts/scaffold-launchd.py` generator copies `templates/launchd/service.py` and
creates four wrappers plus both manifests. It never starts a service. Generated adapters are
project-owned copies, so the project works without a global Skill installation at runtime.
`--tunnel-profile` enables the optional tunnel-client probe and validates the profile in the plist.
Readiness uses the exact launchd PID's loopback listener and the client's health/ready/control-plane
poll checks. Do not copy profile contents, credentials or full health error output into manifests,
logs or repository files. Keep actual tunnel transport and proxy configuration in the existing
host profile/LaunchAgent.

For the supplied launchd adapter, start waits for a PID plus local readiness when a probe is
configured (default 30 seconds; `launchd.json` `startTimeoutSec` from 1 through 120). Without a
probe it confirms only the process. The consumer deadline must leave room for readiness and
cleanup (at least startTimeoutSec plus 15 seconds). On failure, only a job with an acknowledged bootstrap by
this attempt is unloaded. A failed or timed-out bootstrap has uncertain ownership and must report
that uncertainty instead of unloading a potentially concurrent operator-owned job. A job loaded before the attempt is preserved. Verify exact plist
ownership again during cleanup; inability to verify or unload is an explicit cleanup failure,
never a successful rollback. Once unloaded, KeepAlive/recovery cannot retry that failed attempt;
the next retry is manual. Existing loaded jobs retain their supervisor retry policy.
Restart is stop then start; if the replacement fails, it stays failed/stopped instead of restoring
a previous binary, configuration, credentials or process. No version backups are created.

Process state and readiness are separate: a live process returns status exit 0 even when readiness
is `unready` or `unknown`; text output must state that distinction. Optional `status --json` adds
`readiness: ready|unready|unknown` and the authoritative PID to the existing status vocabulary.
Local readiness is not proof of remote MCP availability; verify a real remote tool call before
claiming that. No HTTP metrics server or fixed admin port is required for an external adapter.
Ephemeral loopback admin ports remain runtime-owned and are not invented fixed reservations.

### 4.10 Primary entry

The primary-entry script should do the action appropriate to the project surface:

- `web`: open `frontendUrl`
- `desktop`: launch or focus the application using `appLaunchCommand` or `appUrl`
- `hybrid`: open the frontend when available, otherwise launch or focus the application
- `service`: report that no interactive entry is available, unless `appUrl` or `homepageUrl` is explicitly configured

`openEntry` is not a second process supervisor. It should focus or open an already-running app and
may delegate to the idempotent `start` flow when the project explicitly supports that behavior.

The existing `open-homepage.sh` filename may remain as a compatibility wrapper, but its behavior
must follow this primary-entry contract.

### 4.11 Scaffold inputs

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
