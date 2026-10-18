# Local port registration

Read the bundled spec section 3.7 for the portable manifest contract. This file describes the
Control Panel host integration. Commands below are relative to the installed skill package;
execute with its absolute path when your cwd is the target project.

## Get the spec and inventory

```bash
node /path/to/project-tooling/scripts/port-registry.mjs spec
node /path/to/project-tooling/scripts/port-registry.mjs list
```

`spec` reads the packaged canonical Markdown and works offline. The source is
https://github.com/codepiano/control-panel-spec/blob/main/spec/PROJECT_TOOLING_SPEC.md.
If a newer version is needed, update the skill checkout from that source and read it. Do not
mix a downloaded contract with an older helper without checking compatibility.

The helper uses `CONTROL_PANEL_URL` or `--panel-url`, default `http://127.0.0.1:4310`.
Only loopback HTTP origins are accepted. It obtains the session token itself; never print or
persist the token. The panel must be running and support the registration API. An unavailable
panel or unknown API is a registration failure; do not substitute a random port and claim it is
registered. Continue project inspection or prepare scripts while registration is unavailable.

## Reserve before generating final launch configuration

1. Inspect all listeners the target project needs: frontend, backend, metrics and extra TCP
   services. Identify existing consumers (browser extensions, proxy/tunnel rules, callback URLs,
   other service configs). One process sharing its frontend and metrics endpoint needs one port.
2. For a new project, create only a minimal valid `control-panel.json` with `name` and
   `workingDirectory`. Preserve an existing manifest. A collection never reserves ports.
3. Request the number of unique TCP ports, or exact ports when preserving an existing integration:

```bash
node /path/to/project-tooling/scripts/port-registry.mjs register --project /absolute/project --count 2
node /path/to/project-tooling/scripts/port-registry.mjs register --project /absolute/project --ports 4323,4324
```

These are alternative requests, not two sequential steps. The API serializes registrations,
checks persisted manifests plus live listeners, writes `ports` into the target manifest, and adds
an undiscovered project root to local discovery. Requests preserve all unrelated manifest fields.
An exact-port conflict fails without writing the manifest or changing discovery roots. Repeated
allocation with the same count reuses existing assignments. Reservations remain when stopped;
there is no lease expiry. `status: reserved` confirms allocation, not service readiness or
ownership of any listener. Existing configured ports may already be occupied; validate runtime
identity separately. `reservedPorts` includes any additional ports inferred from existing local
URLs. Inspect this union when migrating to avoid silently retaining an old URL assignment.

4. Use the returned numbers for the service's actual listen options/environment and for
   `frontendUrl` / real `metricsUrl`. Preserve `ports` as the complete explicit reservation.
   Do not just edit the displayed URL. Do not permit frameworks to silently choose the next port
   (`strictPort: true` for Vite, or the runtime's equivalent).
5. Generate only the lifecycle scripts needed by the project, following spec section 4 and the
   main skill. Prefer existing supervisors/wrappers. Startup must bind the declared ports and
   fail clearly on a collision even when started outside the panel. The panel is a registration
   service, not a required dependency for starting an already configured project.
6. Validate JSON, shell syntax, executable permissions and working directories. When runtime
   validation is in scope, run start → status/health → repeated start → stop and confirm unrelated
   processes survived. Verify the actual listening port and endpoint identity against the
   registered manifest; then refresh the inventory using `list`.

## Migrations and limitations

Changing an existing service's port is a coordinated configuration change. Account for all
consumers identified in step 1. Keep the current assignment when migration is outside the task.
Never stop a process solely because it occupies the desired port.

The registry currently reserves TCP port numbers across all local bind addresses. It does not
allocate UDP or remote-host ports, share a number across independent services, manage a
reverse-proxy routing table, or automatically rewrite application config. Register each independently
controlled child service against its own manifest. A new deep child should also be declared by
its parent's `children`; adding a local discovery root does not replace that structural declaration.

Registration is serialized by one running panel backend. Offline manifest edits and direct
server starts can still race; the final bind is authoritative. Do not remove reservations from
an active service without updating its configuration and consumers.

## HTTP integration

The helper obtains a token from `GET /api/session`. POST requests send
`Content-Type: application/json` and `X-Control-Panel-Token` using that token:

- `/api/get-port-allocations`: `{ "args": [] }`; response `data` contains `rows`,
  `suggestions`, `conflictCount`, and any listener-read `error`.
- `/api/register-project-ports`: `{ "args": [{ "projectDir": "/absolute/project", "count": 2 }] }`,
  or replace `count` with `ports: [4323, 4324]`. Response `data` contains `projectDir`,
  `manifestPath`, requested/allocated `ports`, the merged `reservedPorts`, and `status: reserved`.

Use `error` and the non-success status as failure. Session tokens authorize local panel actions;
registering a new project also trusts its manifest's existing status scripts for normal discovery.
