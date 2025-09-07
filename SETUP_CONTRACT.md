# Domains Module — Setup Contract

Status
- This module currently has no `module_setup.py` and no application package imports that require a local venv.

Contract
- If/when local runners or MCP servers are added, provide `module_setup.py` delegating to Base `AMIModuleSetup` and a `python.ver` (3.12).
- Until then, document as a non-setup module and keep docs/tests runnable via orchestrator toolchain.

Policy references
- Orchestrator contract: `/docs/Setup-Contract.md`
- Base setup utilities: `base/backend/utils/{path_finder.py, environment_setup.py, path_utils.py}`
