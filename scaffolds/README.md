# Scaffolds

This folder currently holds the Node.js starter pack.

The Node scaffold keeps the same conceptual pieces:

- `control-panel.json` template
- lifecycle script templates
- optional metrics server or adapter
- a short README that explains the runtime-specific inputs and common project layout

Lifecycle templates should cover init, install, start, stop, status, restart, uninstall, and homepage.

The repository can add more runtimes later, but the current working surface is Node-only.

The templates are intentionally small. They should show the contract, not hide it behind framework-specific magic.
