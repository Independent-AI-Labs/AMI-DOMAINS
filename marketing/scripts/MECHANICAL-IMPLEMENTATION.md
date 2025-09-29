# Mechanical Implementation – How the Toolkit Enforces Behaviour

All source material MUST be gathered via the Browser MCP tool; it is the only trusted conduit for content.

## Authorised Entry Points
| Action | Required Script |
| --- | --- |
| Capture URLs | `python scripts/add_link.py --subdir <focus>` |
| Validate structured data | `python scripts/validate_and_save.py --subdir <focus>` |
| Download artefacts | `python scripts/download_file.py --subdir <focus>` |
| Propose schema changes | `python scripts/propose_schema.py --name <schema>` |
| Append audit commentary | `python scripts/add_audit_note.py --title "..."` |

Each script ensures the marketing module venv is active (`ensure_module_venv`), prints clear `[STATE]` messages, writes JSON logs, and exits non-zero on failure so orchestrators can react immediately.

## What Actually Happens Under the Hood

### Example: Adding a Company Record
1. Claude prepares JSON representing the company.
2. Runs `validate_and_save.py --dry-run` to surface schema and duplicate issues.
3. The script:
   - Loads the relevant schema from `schemas/`.
   - Validates required fields, enums, string lengths, etc.
   - Performs URL verification with retry/backoff and optional rate limiting.
   - Checks `vendor_name` and `website_url` clashes inside the chosen subdirectory.
4. If any errors exist, the run aborts with exit code `1`; warnings require a conscious `--force` re-run.
5. On success, the script writes the JSON model, emits a manifest, and records the workflow in `logs/<subdir>/`.

### Example: Capturing Links
- `add_link.py` ingests URLs (plain or CSV), verifies them (HEAD/GET), deduplicates against existing registry entries, and appends to `verified_links.csv` in append-only mode.
- Rejected URLs—including the reason—land in `rejected_links.csv` for later manual review.

### Example: Audit Notes
- `add_audit_note.py` wraps Markdown in a timestamped section and appends it to `requirements-and-schemas/requirements/audit-trail.md`, ensuring the immutable initial requirements stay untouched while decisions remain traceable.

## Enforcement Mechanics
1. **Script-only mutations** – Data directories (`links-and-sources`, `data-models`, `downloads`) are modified exclusively by the scripts. Direct edits show up in review and violate policy.
2. **Structured telemetry** – `logs/<subdir>/latest.log.json` reflects the most recent run; JSONL histories make investigations reproducible.
3. **Manifests for orchestration** – Each run produces a concise `*_result.json` summarising status, warnings, outputs, and whether `--force` or `--dry-run` was used.
4. **No silent failures** – Any failed verification exits non-zero; orchestrators can halt pipelines immediately.
5. **Audit integrity** – Only Markdown append operations are allowed; the canonical `initial-requirements.md` remains immutable by convention and review.

## Prohibited Shortcuts (and Approved Alternatives)
| Forbidden | Why | Approved Path |
| --- | --- | --- |
| `echo ... >> verified_links.csv` | Skips URL verification & logging | Use `add_link.py --dry-run`, then rerun without `--dry-run`. |
| Editing JSON models manually | Bypasses schema enforcement | Pipe JSON through `validate_and_save.py`. |
| Curl + `mv` for downloads | No headers, no logging | Run `download_file.py` with appropriate flags. |
| Editing requirements directly | Breaks immutable audit baseline | Append context with `add_audit_note.py`. |
| Dropping new schema file manually | No modelling validation | Pipe proposal into `propose_schema.py`. |

## Feedback Signals
- ✔ Success: `[OK] Saved model to ...`, `[RESULT] Schema ready (...)` etc.
- ⚠ Warnings: `[WARN] Recommended field missing: ...` – rerun with `--force` only when intentional.
- ✖ Errors: `[ERROR] website_url: URL does not exist or is not accessible` – fix inputs before proceeding.
- 🛈 Logs: Inspect `logs/<subdir>/latest.log.json` for machine-readable states; manifests summarise final status.

Stay within the scripted lanes to guarantee high-quality, auditable research outputs.
