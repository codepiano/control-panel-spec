# Scaffolds

This folder holds language-specific starter packs.

Each language folder should keep the same conceptual pieces:

- `control-panel.json` template
- lifecycle script templates
- optional metrics server or adapter
- a short README that explains the runtime-specific inputs

The intended shape is the same across Node, Python, Go, and Rust. Only the implementation details change.

The templates are intentionally small. They should show the contract, not hide it behind framework-specific magic.
