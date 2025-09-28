# Lead Capture Workflow

This directory stores source-verified prospect lists for each AI platform segment. Every entry must come from a documented web search and include the URL consulted to confirm the company belongs in the segment.

## Directory Layout

- `data/` – segment-specific CSV exports (`{segment_code}.csv`).
- `logs/` – dated search logs capturing queries, engines, timestamps, and evaluated result URLs.
- `README.md` – this guide.

## CSV Schema

All CSVs share the following header (UTF-8, RFC 4180 compliant):

```
VendorName,SegmentCode,CompanyType,HQRegion,EmployeeBand,PrimaryOffering,WebsiteURL,SourceURL,SourceType,DateVerified,QueryUsed,Notes
```

| Column | Type | Enum Reference | Description |
| --- | --- | --- | --- |
| `VendorName` | string | — | Legal/common company name. |
| `SegmentCode` | SegmentCode | `overview/data-model.md` | Segment taxonomy code (`hyperscalers`, `foundation_model_providers`, etc.). |
| `CompanyType` | CompanyType | `overview/data-model.md` | Organizational archetype (`hyperscaler`, `independent_isv`, `startup`, `oss_foundation`, `system_integrator`, `device_manufacturer`, `consultancy`, `marketplace_operator`). |
| `HQRegion` | RegionCode | `overview/data-model.md` | Headquarters region (`na`, `latam`, `emea`, `apac`, `global`). |
| `EmployeeBand` | EmployeeBand | `overview/data-model.md` | Normalized size band (`lt_50`, `50_199`, `200_499`, `500_999`, `1k_4k`, `5k_9k`, `10k_plus`). |
| `PrimaryOffering` | string | — | Short descriptor of the AI platform/product positioned in the segment. |
| `WebsiteURL` | string | — | Direct URL to the vendor’s primary site or product page. |
| `SourceURL` | string | — | URL used to verify segment fit (press release, analyst report, etc.). |
| `SourceType` | SourceFormat | `overview/data-model.md` | Format of the verifying artifact (`pdf`, `html`, `video`, `audio`, `image`, `dataset`, `text`). |
| `DateVerified` | date | — | `YYYY-MM-DD` date the link was validated. |
| `QueryUsed` | string | — | Exact search query string executed before capturing the lead. |
| `Notes` | string | — | Optional context (unique positioning, pricing callouts, etc.). |

### Enum Notes

- Use enumerations exactly as defined in `overview/data-model.md`. If a value is unknown, record `unknown` where permitted, otherwise leave blank.
- `HQRegion` here captures the top-level geography until finer-grained codes are introduced.

## Search Logging

For every search session, append a Markdown table to `logs/YYYY-MM-DD.md` with:

```
| Timestamp (UTC) | SearchEngine | Query | OpenedURLs | Notes |
```

- `OpenedURLs` may contain multiple comma-separated links considered.
- Include failed or low-quality results with a note; this prevents duplicated effort later.
- When a lead is captured, reference the corresponding log row in the CSV `Notes` field if helpful.

## Workflow Checklist

1. Decide on the target segment and draft 3–5 distinct queries covering synonyms and adjacent language.
2. Record each query in the daily log *before* reviewing results.
3. Validate the company’s positioning using authoritative sources (official site, investor relations, analyst coverage).
4. Add the company to the appropriate CSV with the schema above.
5. Commit supporting downloads to `../downloads/` if long-form collateral is used as a source.
