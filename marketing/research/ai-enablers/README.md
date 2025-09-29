# AI Landscape Research Toolkit

## Directory Layout
```
research/ai-enablers/
├── requirements-and-schemas/
│   ├── requirements/                 # Immutable baseline requirements plus audit trail
│   └── schemas/                      # Active validation schemas (.yaml + .schema.json)
├── links-and-sources/
│   └── validated/<subdir>/           # Verified link CSVs produced by add_link.py
├── data-models/
│   └── validated/<subdir>/data/      # JSON company models saved by validate_and_save.py
├── downloads/                        # Files fetched via download_file.py
└── logs/<subdir>/                    # JSONL event streams + result manifests per script run
```

> **Trust boundary:** All factual research must come through the Browser MCP tool. It is the only trusted source of content—do not rely on memory, prior exports, or any other channel.

## Core Scripts
| Script | Purpose | Typical First Step |
| --- | --- | --- |
| `scripts/add_link.py` | Verify and append research URLs to the link registry. | `--dry-run` to review status codes and duplicates. |
| `scripts/validate_and_save.py` | Validate structured company data against the active schema and persist it. | `--dry-run` to inspect warnings/errors before writing. |
| `scripts/download_file.py` | Fetch supporting artefacts (PDF/CSV/etc.) with stealth headers and retry logic. | Provide `--subdir` to organise downloads. |
| `scripts/propose_schema.py` | Validate and (optionally) publish new JSON schema drafts. | Run without `--force` to capture warnings before overwriting. |
| `scripts/add_audit_note.py` | Append Markdown context to the audit trail. | Pipe narrative updates through stdin. |

Every script boots the marketing virtual environment automatically, prints human-friendly status updates, and emits structured JSONL logs plus an optional manifest to help downstream tooling.

## Recommended Workflow

1. **Understand requirements** – review `research/ai-enablers/requirements-and-schemas/requirements/initial-requirements.md`. Add contextual notes with `scripts/add_audit_note.py` so future runs know why decisions were made.
2. **Draft or extend schemas** – iterate locally with `scripts/propose_schema.py --name <schema> --dry-run`. Re-run with `--force` once warnings are resolved and you are ready to persist `*.schema.json`.
3. **Collect candidate links** – capture URLs or CSV rows and run `scripts/add_link.py --subdir <focus-area> --dry-run` to see verification outcomes. Drop the `--dry-run` flag to append to `links-and-sources/validated/<subdir>/`.
4. **Validate structured company data** – paste JSON (or colon-delimited pairs) into `scripts/validate_and_save.py`. Review the structured log at `logs/<subdir>/latest.log.json`, address warnings, and rerun with `--force` only when you intentionally override soft gates.
5. **Download supporting assets** – use `scripts/download_file.py` to capture pitch decks, price sheets, etc. Each run logs to `logs/<subdir>/` and can run in dry-run mode before writing files.
6. **Document decisions** – any time you adjust taxonomy, reject data, or coordinate research, append a Markdown note via `scripts/add_audit_note.py`.

## Examples

### Validate and save (dry-run first)
```bash
cat <<'EOF' | python scripts/validate_and_save.py \
  --subdir foundation_models \
  --type company \
  --dry-run
{
  "vendor_name": "OpenAI",
  "website_url": "https://openai.com",
  "segment_code": "foundation_model_providers",
  "primary_offering": "GPT product family"
}
EOF
```
Re-run without `--dry-run` (or add `--force`) once warnings are resolved. A manifest such as `logs/foundation_models/validate_and_save_result.json` summarises the outcome.

### Append verified links
```bash
echo "https://openai.com\nhttps://anthropic.com" | python scripts/add_link.py \
  --subdir foundation_models \
  --requests-per-minute 30 \
  --dry-run
```
Drop `--dry-run` to update `links-and-sources/validated/foundation_models/verified_links.csv`.

### Download supporting files
```bash
python scripts/download_file.py \
  --url https://example.com/ai-landscape.pdf \
  --subdir foundation_models \
  --timeout 45 \
  --max-retries 4
```

### Propose a schema update
```bash
cat schema-draft.json | python scripts/propose_schema.py \
  --name company \
  --dry-run
```
Warnings must be acknowledged with `--force` before the schema is overwritten.

### Add an audit note
```bash
cat <<'EOF' | python scripts/add_audit_note.py --title "April 2025 scope tweak"
Shifted focus to APAC enterprise copilots; double-check segment assignments.
EOF
```

## Logging & Manifests
- The most recent structured log for any script/subdir lives at `logs/<subdir>/latest.log.json`.
- Each run writes an append-only JSONL session log (`*_YYYYMMDD_HHMMSS.log.jsonl`).
- Result manifests (e.g., `validate_and_save_result.json`) record success/failure, warning details, and output paths for orchestration.

## Validation Highlights
    - Schemas are authored in YAML (`research/ai-enablers/requirements-and-schemas/schemas/*.yaml`) and compiled to JSON for compatibility (`*.schema.json`).
- URL checks use a configurable HEAD/GET strategy with retries and rate limiting.
- Duplicate detection looks at `vendor_name` and `website_url` within the chosen subdirectory.
- Warnings (missing recommended fields, non-standard formats) block the run unless `--force` is provided, ensuring conscious overrides.

Stick to these entry points—manual edits to `data-models` or the link registry bypass the verification guarantees and should be avoided.
