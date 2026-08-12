---
name: project-tooling
description: Integrate projects with the repository's generic project tooling contract by inspecting the project, generating or repairing control-panel.json, lifecycle scripts, primary-entry behavior, and project-owned metrics. Use when a project needs standardized start/stop/status/restart integration, Node.js or Electron development-mode support, SQLite/full-stack project alignment, or validation against the Project Tooling Spec.
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

3. Define the manifest.

   - Always provide `name` and `workingDirectory`.
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

6. Implement metrics honestly.

   - Prefer `GET /control-panel/metrics` from the project backend or runtime adapter.
   - Return JSON with at least `status` and `updatedAt`.
   - Use `running`, `stopped`, `starting`, `stopping`, `failed`, or `unknown`.
   - Include `runtimeMode` and `processMode` when available.
   - Report `pid`, `uptimeSec`, `memory`, `cpu`, and `processes` only when measured reliably.
   - Do not fabricate HTTP metrics or guess runtime state from host process tables when a project
     endpoint is expected.
   - For `observed` mode, return `unknown` when the process cannot be verified.

7. Validate before handing off.

   - Parse `control-panel.json` as JSON.
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
- Validation commands and their results.

When asked to generate files without applying them, return a unified diff or a file manifest with
complete contents. Do not omit lifecycle scripts that the manifest advertises.
