# Cloudscraper Usage in the Marketing Toolkit

Cloudscraper ships with the marketing module to make HTTP requests look like a real browser when necessary. The primary consumer is `download_file.py`, which first tries Cloudscraper before falling back to plain `requests` so we can reach Cloudflare-protected assets without manual intervention.

## Why Cloudscraper?
- Cloudflare and similar providers often gate content behind lightweight JavaScript challenges.
- Standard `requests` fails (403/503) because it lacks browser fingerprints and JS execution.
- Cloudscraper emulates Chrome TLS and UA fingerprints, solving those challenges in pure Python.

## Download Flow
```python
# inside download_file.py
try:
    response = cloudscraper.create_scraper(...).get(url, stream=True, timeout=timeout)
except Exception:
    session = requests.Session()
    session.headers.update(stealth_headers)
    response = session.get(url, stream=True, timeout=timeout)
```
- The script logs whether the fallback was engaged and captures the final status code.
- Allowed status codes and headers live in `requirements-and-schemas/schemas/download.yaml` so we can tune behaviour without editing code.

## Limitations
- CAPTCHA challenges still require a human/browser.
- Respect website Terms of Service and robots.txt; Cloudscraper is a power tool, not a carte blanche.
- Heavy rate limiting may still block repeated requests—use the `--requests-per-minute` flag to throttle politely.

## Alternatives & Escalation Paths
- If Cloudscraper fails, consider orchestrated Playwright/Selenium runs for one-off captures.
- For truly locked-down resources, coordinate with the research lead before proceeding.

## Installation Notes
- Bundled via `pyproject.toml`; no extra setup required when running scripts.
- Pure Python dependency (~2–5 MB). The marketing scripts automatically activate the venv where it is installed.

Use Cloudscraper via the provided scripts—avoid ad-hoc integration so logging and manifests remain consistent.
