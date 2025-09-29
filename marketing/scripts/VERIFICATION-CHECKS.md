# Verification Checks Per Script

The current toolkit focuses on deterministic validations that we can reliably enforce in automation. Below is the actual behaviour implemented today.

## `validate_and_save.py`
- **Schema integrity**
  - Ensures root schema is an object with defined properties/required fields.
  - Validates required fields are present and non-empty.
  - Applies per-field rules (type, enum membership, min/max length, recommended vs required fields).
- **URL verification**
  - Performs a HEAD (and optional GET) request with retry/backoff.
  - Accepts status codes defined in the schema (`url_checks.allowed_status`).
  - Logs final status code, redirect target, and network errors.
- **Duplicate protection**
  - Compares `vendor_name` and `website_url` (case-insensitive) against existing models in the target subdirectory.
- **Warnings vs force**
  - Missing recommended fields or non-standard formats emit warnings; run exits unless `--force`.
  - Errors (missing required data, invalid enum value, unreachable URL, duplicates) abort immediately.

## `add_link.py`
- **HTTP checks**
  - HEAD/GET verification using schema defaults (allowed status codes, retry/backoff, headers).
  - Captures final URL, status code, and error details for rejected links.
- **Deduplication**
  - Skips URLs already in `verified_links.csv` unless `--force`.
- **Structured outputs**
  - Appends verified URLs with hash, source/metadata, and timestamp.
  - Records rejected attempts with the reason for follow-up.

## `download_file.py`
- **Request strategy**
  - Attempts Cloudscraper with Chrome-like headers, falls back to `requests` with retry/backoff.
  - Honours allowed status codes from `schemas/download.yaml` unless `--force`.
- **Result tracking**
  - Streams downloads to disk, reporting bytes written and destination path.
  - Provides dry-run mode for previewing actions.

## `propose_schema.py`
- **Modelling guardrails**
  - Enforces snake_case property names.
  - Validates primitive types, enum uniqueness, format/type compatibility.
  - Requires non-empty `required` array referencing defined properties.
- **Change control**
  - Blocks overwriting existing schemas unless `--force`.
  - Flags missing `additionalProperties` or long descriptions as warnings.

## `add_audit_note.py`
- **Audit hygiene**
  - Prevents empty submissions.
  - Wraps Markdown with timestamped headings for traceability.
  - Keeps the immutable `initial-requirements.md` untouched while expanding `audit-trail.md`.

## Logging & Manifests
- Each script emits JSONL events capturing `state`, `level`, `message`, and optional `details` (e.g., HTTP status, hint text for remediation).
- Default manifests (`*_result.json`) summarise status, warnings, affected paths, and whether `--dry-run`/`--force` was used.

These checks reflect the guardrails that are **currently** implemented. Extending the workflow (e.g., source cross-referencing or LinkedIn lookups) should be modelled as additional scripts or schema rules so the guarantees stay explicit and enforceable.
