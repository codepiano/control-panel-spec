# Project-owned release adapter

Use `scripts/scaffold-release.py <project> --config <reviewed-recipe.json>` or copy `adapter.py` into the project's `tooling/release/` with a reviewed `config.json` and
seven small `scripts/release-{version,prepare,activate,start,stop,status,restart}.sh` wrappers.
The adapter uses Python 3.9+, Git, `ps`, and `lsof`; runtime/build tools remain project-owned.
No global Skill installation is needed after copying. Configuration is project-specific; never
copy another project's data paths or build recipe without inspecting it.

`legacy` provides exact argv arrays for existing start/stop/status scripts. `prepare` is a list
of build/install argv arrays, `outputs` lists required artifact paths, `toolchain` reports actual
compiler/runtime versions, and `patches` removes already-completed builds from snapshot launchers.
`persistent` lists project-relative live data directories; `runtimeFiles` lists existing private
configuration/data files. They are excluded from source snapshots and linked only at activation.
Runtime overrides are explicit `runtimeEnvironment` values; `{origin}` expands without a shell.
`pathPrefix` selects an existing runtime toolchain directory. `packageManager` pins an otherwise
unpinned pnpm version in the snapshot package.json. Allowlisted `buildEnvironment` and
`buildEnvFiles` public values are fingerprinted and passed to the build; other env-file content is
never exposed to preparation. Independent declared children and
Git submodules are excluded. Runtime data, credentials, caches and installed dependencies are
never copied as source inputs. Do not use an entire project root as persistent data.

Artifacts and PID identity records live under the current user's
`~/Library/Application Support/project-tooling/releases/<hash-of-project-directory>/`.
`PROJECT_RELEASE_STORE` can select a fully private store for isolated validation. Each immutable
artifact captures nonignored source content, executable modes, internal symlinks and declared
toolchain/environment inputs. Preparation verifies the source again before recording success.
Output/core-source checks are used for lightweight status; complete dependency/content integrity
is checked before artifact reuse and activation. Per-project process locks serialize CLI operations.
Only real processes tied to an exact artifact directory and start-time/command identities are
recorded as running; pre-integration processes remain unknown. Process matching never grants
permission to kill a broad process name. Existing stop scripts remain the process authority.

Private data links are established only after stopping the previous runtime and verifying the
artifact. Builds have separate dependency trees and a release-store cache isolated from live workspaces.
Pnpm global virtual stores are disabled and package import uses copies, so dependency writes cannot
flow back through symlinks or hard links into an older running artifact. Existing project entry scripts
remain available for compatibility; the manifest uses the new `release-*` entrypoints. Use those
entrypoints for CLI version-aware starts/restarts. Original legacy CLI starts have unknown runtime
provenance, even when launched after a Git update.

For a launchd tunnel, the adapter snapshots the existing executable, keeps the existing Label and
profile, creates a private artifact-owned plist only during activation, and delegates to the existing
ownership-checking launchd adapter. It does not create credentials or modify the original plist.
Stop unloads the specific active job. Re-login may invoke the operator's original LaunchAgent;
this is then honestly reported as an unknown pre-integration runtime until explicitly switched.

The Control Panel keeps its existing pre-restart PID/launcher checks. Its detached helper invokes
the origin project's version-aware restart, allowing preparation while the old backend runs.
`PROJECT_RELEASE_ORIGIN` identifies the original project when the backend runs from a snapshot.

Validate against temporary data and independent origins. Never activate a snapshot merely to test
a live user's project. Full builds validate preparation, not delivery or user workflow compatibility.
