---
name: project-tooling
description: Integrate projects with the repository's generic project tooling contract by inspecting the project, generating or repairing control-panel.json, lifecycle scripts, primary-entry behavior, and project-owned metrics. Use when a project needs standardized start/stop/status/restart integration, Node.js or Electron development-mode support, SQLite/full-stack project alignment, local TCP port registration through Control Panel, or validation against the Project Tooling Spec.
---

# Project Tooling

Use this skill to adapt an existing project to the shared project contract. Keep the project
generic: do not describe the integration as Control Panel-specific, and do not invent UI behavior.

## Authority

The canonical contract included in this Skill is:

`spec/PROJECT_TOOLING_SPEC.md`

Read the spec before changing a project integration. The repository is itself the Skill package, so
the spec and validation helpers are available relative to this file.
Run `scripts/check-spec-sync.sh` after changing the contract or its validation workflow.

For Node.js, TypeScript, Electron, or Node-based frontend/backend projects, follow the Node.js
guidance in the spec and generate only the files the target project actually needs.

## Workflow

1. Inspect the project before editing.

   - Identify the project root, package manager, runtime, frontend/backend layout, Electron entry,
     SQLite location, and existing process manager.
   - Inspect existing `control-panel.json`, `scripts/`, package scripts, launch configuration,
     and metrics endpoints.
   - Preserve user changes and existing lifecycle behavior unless it violates the contract.

2. Classify the project.

   - `surfaceType`: `web`, `desktop`, `hybrid`, or `service`.
   - `runtimeMode`: `development` or `packaged`.
   - `processMode`: `managed`, `external`, or `observed`.
   - Choose `external` for `launchd`, PM2, Docker, or another declared supervisor.
   - Choose `observed` only when the project is intentionally started outside tooling and cannot
     reliably control its process.

3. Register local ports and define the manifest.

   - For local network services, read [references/port-registration.md](references/port-registration.md).
     Use `scripts/port-registry.mjs spec` to retrieve the packaged spec and `list` to inspect the
     host inventory. Create a minimal manifest if absent, then use `register` to persist an
     allocation before generating final launch configuration. Candidate ports from `list` are
     not reservations. Preserve existing assignments when migrating clients is outside scope.
   - Use returned ports in the application's real startup settings, explicit manifest `ports`,
     local frontend/metrics URLs, and any in-scope consumers. Configure strict port binding;
     silently falling back to another port violates the declared allocation.
   - Registration supports the local Control Panel host. If it is unavailable, report the
     unregistered state and continue independent script work; do not claim a reservation.


   - Always provide `name`; provide `workingDirectory` for controllable projects.
   - Inspect whether nested repositories/services form a workspace or product. Declare their
     relative directories in the outer manifest's `children` with `role` and `notes` describing
     the relationship; retain each child's own manifest and lifecycle commands.
   - Use `kind: collection` for an outer directory with no runtime. Do not generate lifecycle
     commands, process ownership fields, or status/metrics for the collection itself.
   - A runtime-owning parent may declare children, but its scripts must not also control those
     independently exposed child services. Do not invent undeclared child services.
   - Preserve an existing project-relative `icon`; add one only when the project already has a suitable repository-owned image.
   - Prefer project-authored `scripts/*.sh` paths over inline commands.
   - Include `surfaceType`, `runtimeMode`, `processMode`, `processManager`, and `pidFile` when
     applicable.
   - Use `frontendUrl` for a web frontend, `appUrl` for an application/deep link, and
     `appLaunchCommand` for a desktop launch or focus command.
   - Keep `openHomepageCommand` only as a compatibility alias; use `openEntryCommand` and
     `scripts.openEntry` for new integrations.
   - Set `databasePath` to the project-owned SQLite file when SQLite is used.
   - Set `metricsUrl` only when the endpoint is real and project-owned.

4. Generate or repair lifecycle scripts.

   - For a supporting external runtime (tunnel, sidecar, worker), keep it inside its owning project
     and declare it in `children`. Read [references/launchd-components.md](references/launchd-components.md)
     for existing per-user LaunchAgents. Use `scripts/scaffold-launchd.py` to generate project-owned
     scripts; never start or restart the live job to validate the integration. Confirm recovery
     helpers respect an unloaded job and distinguish process state from local readiness.
     Confirm bounded readiness and cleanup of only jobs created by this attempt. Preserve existing
     jobs, report cleanup failures, and budget the consumer deadline for readiness plus cleanup.
     Stop failures must prevent restart; do not generate version backups or automatic downgrades.

   - `start.sh` must start only the project's declared service or application.
   - In `managed` mode, start must be non-blocking, idempotent, and record a PID, process group,
     or equivalent project-specific handle before returning.
   - `stop.sh` must use the same verified handle, attempt graceful termination, wait a bounded
     period, and force-stop only that verified process/group if needed.
   - `status.sh` must not infer ownership from a broad process name. Use the project handle,
     external supervisor, or an authoritative project endpoint.
   - `restart.sh` must perform the equivalent of stop followed by start.
   - `init.sh` and `install.sh` must not start the service unless explicitly required by the
     project.
   - `uninstall.sh` must not delete user data unless the project explicitly defines that behavior.

5. Handle Electron development mode correctly.

   - `runtimeMode: development` is valid and does not require a DMG or packaged app.
   - Never leave `electron .` attached to the lifecycle command's foreground terminal in
     `managed` mode.
   - Track the source-launched Electron runtime with a project-specific PID/process group or use
     an external supervisor.
   - Do not use `pkill electron`, `pkill node`, broad `pgrep`, or application-name matching to
     stop the app.
   - Keep development and packaged launchers behind the same wrapper paths; switch only the
     project-owned launch configuration or `runtimeMode`.
   - Keep `openEntry` separate from process supervision. It may focus/open the app and may call an
     idempotent start flow only when the project explicitly defines that behavior.

6. Integrate versioned lifecycle when requested.

   - Read section 10 of the spec. Opt in with `release.protocol: 1` only after inspecting the
     project's build inputs, immutable artifact storage, process ownership and real data paths.
   - Implement project-owned `scripts.version`, `scripts.prepare`, `scripts.activate`.
     The reference `templates/release/adapter.py` can be copied with a reviewed project-specific
     configuration; read `templates/release/README.md` and preserve legacy process authority.
     Never infer runtime provenance from current HEAD. Unknown existing processes remain unknown.
   - Preparation must be isolated from live watchers, dependencies, output and user data. It
     must succeed before stopping the old runtime. Source-only services still need a snapshot.
   - Verify actual runtime revision, failures and concurrency with temporary isolated services.
     Do not activate the live project merely to validate integration. Keep independent children
     unchanged. Never advertise placeholders as completed project support.

7. Implement metrics honestly.

   - Prefer `GET /control-panel/metrics` from the project backend or runtime adapter.
   - Return JSON with at least `status` and `updatedAt`.
   - Use `running`, `stopped`, `starting`, `stopping`, `failed`, or `unknown`.
   - Include `runtimeMode` and `processMode` when available.
   - Report `pid`, `uptimeSec`, `memory`, `cpu`, and `processes` only when measured reliably.
   - Do not fabricate HTTP metrics or guess runtime state from host process tables when a project
     endpoint is expected.
   - For `observed` mode, return `unknown` when the process cannot be verified.

8. Validate before handing off.

   - Parse every parent and child `control-panel.json` as JSON.
   - Validate every child path as a strict descendant of its declaring directory, including
     symbolic-link resolution. Validate missing references and cycles and explain the
     declared roles. Confirm that collections have no runtime commands.
   - Run `bash -n` against generated shell scripts.
   - Check every manifest script path exists and is executable when generated.
   - Verify that lifecycle commands use the declared working directory.
   - Verify that stop/status target the same project-specific handle as start.
   - Verify that the metrics URL and response shape match the actual project implementation.
   - Report unsupported operations explicitly instead of claiming success.

## Required Output

When modifying a project, return:

- The files changed.
- The selected `surfaceType`, `runtimeMode`, and `processMode`.
- The process ownership mechanism.
- The primary-entry behavior.
- The metrics source and endpoint, or the reason metrics are unavailable.
- Local TCP port reservations, application listen configuration, and any consumers updated.
- Validation commands and their results.

When asked to generate files without applying them, return a unified diff or a file manifest with
complete contents. Do not omit lifecycle scripts that the manifest advertises.
