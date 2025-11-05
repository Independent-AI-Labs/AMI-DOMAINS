# Domains Module - Setup Contract

Status
- `module_setup.py` delegates to Base `AMIModuleSetup` and provisions the module `.venv` using Python 3.12 (see `python.ver`).
- No MCP servers or runners are defined yet; the module currently supplies domain models and research artefacts.

Contract
- Maintain parity with Base environment helpers: no top-level third-party imports in `module_setup.py`, and reuse `EnvironmentSetup` when adding future runners.
- When new services are introduced (predictive models, SDA pipelines), document their runners/tests and ensure they honour the orchestrator setup policy.

Policy references
- Orchestrator contract: `docs/Setup-Contract.md`
- Base setup utilities: `base/backend/utils/{path_finder.py,environment_setup.py,path_utils.py}`
