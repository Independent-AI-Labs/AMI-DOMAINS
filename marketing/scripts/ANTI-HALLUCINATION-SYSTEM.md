# Anti-Hallucination Safeguards

The marketing research stack prevents fabricated data by forcing everything through scripted checkpoints. Instead of a loose pipeline, we now operate a set of focused tools that each guarantee a slice of the validation story. **All upstream content must originate from the Browser MCP tool—it is the only trusted source.**

## Guardrail Overview
| Risk | Mitigation |
| --- | --- |
| Invented URLs | `add_link.py` and `validate_and_save.py` both verify URLs via live HTTP checks with retry/backoff before any data is accepted. |
| Duplicate / recycled companies | `validate_and_save.py` compares `vendor_name` and `website_url` against existing models per subdirectory; duplicates require an explicit `--force` override. |
| Schema drift or missing fields | Schemas live in `requirements-and-schemas/schemas/*.yaml`; proposals pass through `propose_schema.py` which enforces modelling rules before publishing `*.schema.json`. |
| Silent edits or memory-based assertions | All dataset mutations emit structured JSON logs plus manifests; manual edits are detectable and disallowed by process. |
| Missing audit rationale | `add_audit_note.py` appends timestamped Markdown to `audit-trail.md`, ensuring every override or decision leaves context. |

## Scripted Flow
```
Research → add_link.py (URL reality) → validate_and_save.py (schema + duplicate checks)
                                 ↘ download_file.py (artefact capture)
                                   ↘ add_audit_note.py (context)
```

### 1. add_link.py – Reality check for URLs
- HEAD/GET requests with programmable retries.
- Logs reason for rejection (timeouts, HTTP status, duplicates).
- Requires conscious rerun without `--dry-run` before any CSV is modified.

### 2. validate_and_save.py – Structured data gatekeeper
- Schema-driven validation; missing fields or invalid enums block the run.
- URL verification with optional rate limiting and telemetry in logs.
- `--force` required to accept warnings (e.g., missing recommended data), creating an explicit paper trail.

### 3. download_file.py – Evidence capture
- Cloudscraper fallback mirrors browser fingerprints to avoid blockers.
- Dry-run support stops accidental large downloads.
- Manifests summarise which files were fetched (or failed) for orchestration compliance.

### 4. propose_schema.py – Controlled schema evolution
- Prevents ad-hoc JSON edits; snake_case keys, enum hygiene, and consistent types are enforced.
- Warns about lax settings (e.g., missing `additionalProperties` clauses) to prompt intentional design decisions.

### 5. add_audit_note.py – Narrative continuity
- Keeps immutable requirements untouched while logging why warnings were overridden, scope was refined, etc.
- Stored notes help future agents understand the research state without reverse engineering git history.

## Operational Signals
- Success: `[RESULT] … (manifest: …)`; exit code `0`.
- Warning requires attention: `[WARN] …` followed by exit code `1` until `--force` is used.
- Error: `[ERROR] …`; run aborts.
- Logs: `logs/<subdir>/latest.log.json` always reflects the latest state for agents to poll.

## Expected Outcomes
- Zero tolerance for hallucinated URLs or schema violations.
- Repeatable, auditable decisions recorded in manifests and the audit trail.
- Easy integration for orchestration platforms that need machine-readable progress updates.

Stick to the scripts, capture context, and the hallucination risk stays near zero.
