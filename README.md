# Project Tooling

This repository holds the canonical spec and scaffold templates for projects that want a standard control surface, lifecycle scripts, and runtime metrics.

It is intentionally Node.js-first:

- `spec/` contains the contract other AIs should follow
- `scaffolds/` contains the Node.js starter templates
- `examples/` contains sample payloads and manifests

The goal is to keep the contract stable while letting the Node.js scaffold stay small, reusable, and easy to extend later.

Current scaffold family: `node/`.
