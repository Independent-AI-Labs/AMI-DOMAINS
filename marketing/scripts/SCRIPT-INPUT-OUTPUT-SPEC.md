# Script Input / Output Reference

All scripts run from `domains/marketing/scripts/`, bootstrap the local venv automatically, print human-readable status lines, and emit JSONL logs plus optional manifests underneath `research/ai-enablers/logs/`.

## `validate_and_save.py`
- **Purpose**: Validate structured company data and persist it to `data-models/validated/<subdir>/`.
- **Input**: JSON or `key: value` pairs via stdin.
- **Key flags**:
  - `--subdir <name>` *(required)* – taxonomy folder.
  - `--type <schema>` – schema name (default `company`).
  - `--dry-run` – run validation without writing files.
  - `--force` – override warnings/duplicate detections.
  - `--manifest <path>` – custom manifest destination.
  - `--max-retries`, `--timeout`, `--requests-per-minute` – URL verification controls.
- **Output**:
  - On success: `[OK] Saved model to …` and manifest `validate_and_save_result.json`.
  - On failure: `[ERROR] …` lines per violation; exit code `1`.
  - Structured log events written to `logs/<subdir>/validate_and_save_*.log.jsonl` and `latest.log.json`.

## `add_link.py`
- **Purpose**: Verify URLs and update the link registry.
- **Input**: Plain URLs (one per line) or CSV via stdin.
- **Key flags**:
  - `--subdir <name>` *(required)*.
  - `--format plain|csv` (default `plain`).
  - `--dry-run`, `--force`, `--manifest`, retry/timeout/rate-limit flags.
- **Output**:
  - Appends to `links-and-sources/validated/<subdir>/verified_links.csv` and `rejected_links.csv` (unless `--dry-run`).
  - Summary plus manifest `add_link_result.json`.
  - Logs to `logs/<subdir>/add_link_*.log.jsonl` and `latest.log.json`.

## `download_file.py`
- **Purpose**: Fetch supporting artefacts with stealth headers / Cloudscraper fallback.
- **Input**: `--url` argument and/or URLs piped via stdin.
- **Key flags**:
  - `--subdir` to group downloads under `downloads/<subdir>/`.
  - `--output` for an explicit file path.
  - `--dry-run`, `--force`, `--manifest`, retry/timeout/rate-limit flags.
- **Output**:
  - Saves file(s) or reports errors per URL.
  - Manifest summarising counts and output paths.
  - Logs under `logs/<subdir or general>/`.

## `propose_schema.py`
- **Purpose**: Validate JSON schema drafts against modelling guardrails and optionally persist them as `schemas/<name>.schema.json`.
- **Input**: JSON schema via stdin.
- **Key flags**:
  - `--name <schema>` *(required)* – file stem.
  - `--dry-run`, `--force`, `--manifest`.
- **Output**:
  - Logs warnings/errors for missing fields, invalid formats, etc.
  - Writes schema file unless `--dry-run`.
  - Logs go to `logs/` (no subdir).

## `add_audit_note.py`
- **Purpose**: Append Markdown notes to `requirements-and-schemas/requirements/audit-trail.md`.
- **Input**: Markdown body via stdin.
- **Key flags**:
  - `--title` for the entry heading.
  - `--dry-run`, `--manifest`.
- **Output**:
  - Timestamped section appended to the audit trail (unless dry-run).
  - Manifest capturing success and target path.

## Common Behaviours
- **Structured logging**: Every script prints `[STATE] message` lines and mirrors them to JSON with timestamps, state, level, details, and optional hints.
- **Manifests**: Default manifests are written alongside session logs (e.g., `validate_and_save_result.json`). Use `--manifest` to point to a custom location.
- **Bootstrap**: No manual `source` or `uv` activation required; the scripts invoke `ensure_module_venv` internally.
- **Exit codes**: `0` on success; non-zero when validation fails or all operations were rejected.

Use these entry points for ALL modifications—direct edits to CSV/JSON datasets bypass guardrails and should be avoided.
