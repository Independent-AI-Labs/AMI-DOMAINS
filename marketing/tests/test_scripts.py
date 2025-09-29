from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
SCHEMA_SOURCE_DIR = ROOT / "research" / "ai-enablers" / "requirements-and-schemas" / "schemas"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

os.environ.setdefault("AMI_MARKETING_SKIP_MAIN", "1")


def load_script(name: str) -> ModuleType:
    module_path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"marketing_{name}", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


validate_module = load_script("validate_and_save")
link_module = load_script("add_link")
download_module = load_script("download_file")
schema_module = load_script("propose_schema")
audit_module = load_script("add_audit_note")
create_module = load_script("create_research")


@pytest.fixture()
def tmp_paths(tmp_path: Path) -> validate_module.ModulePaths:
    research_root = tmp_path / "research" / "ai-enablers"
    schema_dir = research_root / "requirements-and-schemas" / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for schema_file in SCHEMA_SOURCE_DIR.glob("*.yaml"):
        shutil.copy(schema_file, schema_dir / schema_file.name)
    return validate_module.ModulePaths(SCRIPTS_DIR / "validate_and_save.py", research_root=research_root)


def test_validate_dry_run_success(tmp_paths: validate_module.ModulePaths, monkeypatch: pytest.MonkeyPatch) -> None:
    logger = validate_module.StructuredLogger(tmp_paths, "validate_and_save", subdir="tests")
    options = validate_module.ValidationOptions(
        data_type="company",
        subdir="tests",
        force=False,
        dry_run=True,
        manifest_path=None,
        max_retries=1,
        timeout=0.5,
        backoff_factor=0.1,
        requests_per_minute=None,
    )
    validator = validate_module.Validator(tmp_paths, options, logger)
    monkeypatch.setattr(validator, "_verify_url", lambda url: True)

    data = {"vendor_name": "TestCo", "website_url": "https://example.com"}
    outcome = validator.validate(data)

    assert not outcome.errors
    assert not outcome.warnings


def test_link_processor_parses_and_logs(tmp_paths: validate_module.ModulePaths, monkeypatch: pytest.MonkeyPatch) -> None:
    link_paths = link_module.ModulePaths(SCRIPTS_DIR / "add_link.py", research_root=tmp_paths.base)
    logger = link_module.StructuredLogger(link_paths, "add_link", subdir="tests")
    options = link_module.LinkOptions(
        subdir="tests",
        format="plain",
        dry_run=True,
        force=False,
        manifest_path=None,
        max_retries=1,
        timeout=0.5,
        backoff_factor=0.1,
        requests_per_minute=None,
    )
    processor = link_module.LinkProcessor(link_paths, options, logger)
    monkeypatch.setattr(processor, "_verify_url", lambda row: {
        "url": row["url"],
        "company_name": row.get("company_name", ""),
        "source": row.get("source", ""),
        "final_url": row["url"],
        "status_code": 200,
        "verified_at": "now",
        "url_hash": "abc123",
        "error": None,
        "success": True,
    })

    rows = link_module.parse_rows("https://example.com", "plain")
    outcome = processor.process(rows)

    assert outcome.verified and not outcome.rejected


class _FakeResponse:
    def __init__(self, url: str, status_code: int = 200, content: bytes = b"data") -> None:
        self.url = url
        self.status_code = status_code
        self._content = content
        self.headers = {"content-length": str(len(content))}

    def iter_content(self, chunk_size: int = 8192):
        yield self._content


def test_download_manager_dry_run(tmp_paths: validate_module.ModulePaths, monkeypatch: pytest.MonkeyPatch) -> None:
    download_paths = download_module.ModulePaths(SCRIPTS_DIR / "download_file.py", research_root=tmp_paths.base)
    logger = download_module.StructuredLogger(download_paths, "download_file", subdir="tests")
    options = download_module.DownloadOptions(
        urls=["https://example.com/data.csv"],
        output=None,
        subdir="tests",
        dry_run=True,
        force=False,
        manifest_path=None,
        max_retries=1,
        timeout=1.0,
        backoff_factor=0.1,
        requests_per_minute=None,
    )
    manager = download_module.DownloadManager(download_paths, options, logger)
    monkeypatch.setattr(manager, "_make_request", lambda url: _FakeResponse(url))

    outcome = manager.download_all()

    assert outcome.results[0]["success"] is True
    assert outcome.results[0]["output_path"]


def test_propose_schema_validation(tmp_paths: validate_module.ModulePaths) -> None:
    schema_paths = schema_module.ModulePaths(SCRIPTS_DIR / "propose_schema.py", research_root=tmp_paths.base)
    options = schema_module.SchemaOptions(name="test", dry_run=True, force=False, manifest_path=None)
    validator = schema_module.SchemaValidator(options, schema_paths, schema_module.StructuredLogger(schema_paths, "propose_schema", subdir=None))

    schema_payload = {
        "title": "Example",
        "type": "object",
        "properties": {
            "vendor_name": {"type": "string"},
            "website_url": {"type": "string", "format": "uri"},
        },
        "required": ["vendor_name", "website_url"],
        "additionalProperties": False,
    }

    result = validator.validate(schema_payload)
    assert not result.errors


def test_add_audit_note_wrap(tmp_paths: validate_module.ModulePaths) -> None:
    audit_paths = audit_module.ModulePaths(SCRIPTS_DIR / "add_audit_note.py", research_root=tmp_paths.base)
    audit_file = audit_module.resolve_audit_path(audit_paths)

    entry_text = "Update pipeline to include weekly market reviews."
    entry = audit_module.wrap_entry(entry_text, title="Weekly Update")
    assert "Weekly Update" in entry

    with audit_file.open("w", encoding="utf-8") as handle:
        handle.write("")
    with audit_file.open("a", encoding="utf-8") as handle:
        handle.write(entry)

    contents = audit_file.read_text(encoding="utf-8")
    assert "Weekly Update" in contents


def test_scaffold_dry_run_reports(tmp_path: Path) -> None:
    module_root = tmp_path / "marketing"
    options = create_module.ScaffoldOptions(
        slug="ai-scouting",
        title="AI Scouting",
        requirements_body="## Objective\nTrack scouting opportunities",
        dry_run=True,
    )
    scaffold = create_module.ResearchScaffold(
        options,
        module_root=module_root,
        script_path=SCRIPTS_DIR / "create_research.py",
    )

    outcome = scaffold.run()

    assert outcome.dry_run is True
    assert outcome.created_directories[0] == module_root / "research" / "ai-scouting"
    assert outcome.created_files == {}


def test_scaffold_creates_full_structure(tmp_path: Path) -> None:
    module_root = tmp_path / "marketing"
    options = create_module.ScaffoldOptions(
        slug="ai-security",
        title="AI Security",
        requirements_body="## Objective\nCatalogue AI security vendors",
        dry_run=False,
    )
    scaffold = create_module.ResearchScaffold(
        options,
        module_root=module_root,
        script_path=SCRIPTS_DIR / "create_research.py",
    )

    outcome = scaffold.run()

    research_root = module_root / "research" / "ai-security"
    req_path = research_root / "requirements-and-schemas" / "requirements" / "initial-requirements.md"
    audit_path = research_root / "requirements-and-schemas" / "requirements" / "audit-trail.md"

    assert outcome.dry_run is False
    assert req_path.exists()
    assert audit_path.exists()
    contents = req_path.read_text(encoding="utf-8")
    assert create_module.BROWSER_REMINDER in contents
