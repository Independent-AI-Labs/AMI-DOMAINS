# Research Methodology – Operational Playbook

The marketing toolkit enforces a scripted workflow so every data point is verified, logged, and reproducible. Follow the stages below—manual edits to datasets are not supported.

## Stage 0 · Requirements & Schema Stewardship
1. Review the baseline requirements in `research/ai-enablers/requirements-and-schemas/requirements/initial-requirements.md`.
2. Capture clarifications, scope changes, or coordination notes with:
   ```bash
   cat note.md | python scripts/add_audit_note.py --title "<summary>"
   ```
   The script appends a timestamped section to `audit-trail.md` and logs the action.
3. Propose schema updates through `scripts/propose_schema.py`. Always run with `--dry-run` first, address warnings, then rerun with `--force` to publish `*.schema.json` alongside the YAML source.

## Stage 1 · Link Discovery & Verification
1. Gather candidate URLs from browsing sessions.
2. Run `scripts/add_link.py --subdir <focus>` with `--dry-run` to see HTTP status, deduplication decisions, and error hints.
3. Remove `--dry-run` once satisfied. Verified URLs flow into `links-and-sources/validated/<subdir>/verified_links.csv`; rejects live beside them for follow-up.
4. Inspect structured logs (`logs/<subdir>/add_link_*.log.jsonl`) for machine-readable states when troubleshooting automations.

## Stage 2 · Company Data Validation
1. Consolidate research into JSON adhering to the active schema (see `schemas/company.yaml`).
2. Pipe it into `scripts/validate_and_save.py`:
   ```bash
   cat data.json | python scripts/validate_and_save.py \
     --subdir <focus> \
     --type company \
     --dry-run
   ```
3. Address errors/warnings noted in stdout or `logs/<subdir>/latest.log.json`. Use `--force` only when you intentionally accept a warning (e.g., missing recommended field with justification in the audit trail).
4. Successful runs produce `data-models/validated/<subdir>/data/<slug>.json` and a manifest referencing the saved path.

## Stage 3 · Artefact Collection
1. For datasheets, pitch decks, or price lists, execute `scripts/download_file.py` with the relevant `--subdir`.
2. Tune retry/timeout flags or enable `--force` if you must keep a non-200 response in the manifest.
3. Outputs land under `downloads/<subdir>/`, with structured logs capturing status codes, fallback usage (Cloudscraper vs requests), and final file names.

## Stage 4 · Ongoing Governance
1. Record why warnings were forced, note source caveats, or document collaboration steps using `scripts/add_audit_note.py`.
2. Re-run `scripts/propose_schema.py` when expanding the dataset (new required fields, enumerations, etc.). The validator enforces snake_case keys, type/format compatibility, and prevents accidental schema regressions.
3. Periodically review `logs/<subdir>/latest.log.json` and stored manifests to ensure orchestrated agents have the telemetry they need.

## Enforcement Guarantees
- **No direct writes**: Only `validate_and_save.py`, `add_link.py`, and `download_file.py` mutate datasets. They all require live verification and emit audit logs.
- **URL reality checks**: HEAD/GET requests with retry/backoff ensure hosts actually respond with approved status codes.
- **Duplicate protection**: Vendor name and URL comparisons stop redundant entries unless `--force` explicitly overrides.
- **Structured traceability**: Each run generates append-only JSONL logs and a manifest summarising status, counts, warnings, and critical paths.

## Typical Daily Loop
1. Start `add_link.py --dry-run` to triage new leads.
2. Validate high-signal companies via `validate_and_save.py` (dry-run → force if needed).
3. Capture supporting files with `download_file.py`.
4. Append audit context so other agents know what happened.

Stay within this loop to guarantee research quality and maintain a full audit trail.
