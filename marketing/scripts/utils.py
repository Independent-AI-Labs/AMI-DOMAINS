"""Shared utilities for marketing research scripts.

This module centralises bootstrap, logging, configuration loading, and
resilience helpers so individual CLI entry points can stay focused on
business logic.  Everything here is intentionally lightweight and pure
Python so scripts can import it without additional bootstrapping.
"""

from __future__ import annotations

import contextlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

try:
    import yaml  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - fallback when PyYAML missing
    yaml = None


_REPO_ROOT_CACHE: Path | None = None


def ensure_runtime(script_path: Path) -> Path:
    """Ensure the repo root is importable and the module venv is active."""
    global _REPO_ROOT_CACHE

    script_path = script_path.resolve()
    repo_root = script_path
    while repo_root != repo_root.parent:
        if (repo_root / ".git").exists() and (repo_root / "base").exists():
            break
        repo_root = repo_root.parent
    else:  # pragma: no cover - guard against unexpected layout
        raise RuntimeError("Could not locate repository root for marketing scripts")

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    if _REPO_ROOT_CACHE is None:
        _REPO_ROOT_CACHE = repo_root
        from base.backend.utils.runner_bootstrap import ensure_module_venv  # noqa: PLC0415

        ensure_module_venv(script_path)

    return repo_root


@dataclass(slots=True)
class ModulePaths:
    """Utility accessor for frequently-used directories."""

    script_path: Path
    research_root: Path | None = None

    def __post_init__(self) -> None:
        if self.research_root is None:
            # scripts/<name>.py -> module root -> research tree
            module_root = self.script_path.resolve().parent.parent
            self.research_root = module_root / "research" / "landscape" / "ai" / "leads"

    @property
    def base(self) -> Path:
        assert self.research_root is not None
        return self.research_root

    def logs(self, subdir: str | None = None) -> Path:
        location = self.base / "logs"
        if subdir:
            location = location / subdir
        location.mkdir(parents=True, exist_ok=True)
        return location

    def data_models(self, subdir: str) -> Path:
        path = self.base / "data-models" / "validated" / subdir / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def links(self, subdir: str) -> Path:
        path = self.base / "links-and-sources" / "validated" / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def downloads(self, subdir: str | None = None) -> Path:
        path = self.base / "downloads"
        if subdir:
            path = path / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def schemas(self) -> Path:
        path = self.base / "requirements-and-schemas" / "schemas"
        path.mkdir(parents=True, exist_ok=True)
        return path


DEFAULT_ALLOWED_STATUS = [200, 201, 301, 302]


def load_schema_config(paths: ModulePaths, schema_name: str) -> dict[str, Any]:
    """Load YAML/JSON schema configuration for a data type."""
    schema_dir = paths.schemas()
    yaml_path = schema_dir / f"{schema_name}.yaml"
    json_path = schema_dir / f"{schema_name}.schema.json"

    if yaml_path.exists():
        if yaml is None:
            raise RuntimeError("PyYAML is required to load marketing schemas; install pyyaml in the module venv")
        with yaml_path.open("r", encoding="utf-8") as handle:
            return json.loads(json.dumps(yaml.safe_load(handle)))

    if json_path.exists():
        with json_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    raise FileNotFoundError(f"No schema found for '{schema_name}' in {schema_dir}")


def append_json_line(path: Path, payload: Mapping[str, Any]) -> None:
    """Append a JSON payload as a single line (JSONL style)."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


@dataclass
class StructuredLogger:
    """Dual-output logger that prints human-readable status and JSON events."""

    paths: ModulePaths
    script_name: str
    subdir: str | None = None
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    def __post_init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._log_dir = self.paths.logs(self.subdir)
        self._session_file = self._log_dir / f"{self.script_name}_{self.session_id}.log.jsonl"
        self._latest_file = self._log_dir / "latest.log.json"
        self._printed_states: set[str] = set()

    def _build_event(self, state: str, message: str, level: str, details: Mapping[str, Any] | None) -> dict[str, Any]:
        event: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "script": self.script_name,
            "state": state,
            "level": level.lower(),
            "message": message,
        }
        if self.subdir:
            event["subdir"] = self.subdir
        if details:
            event["details"] = dict(details)
        return event

    def log(self, state: str, message: str, *, level: str = "INFO", details: Mapping[str, Any] | None = None) -> None:
        event = self._build_event(state, message, level, details)
        self._events.append(event)

        badge = state if state in {"OK", "ERROR", "WARN"} else level.upper()
        prefix = f"[{badge}]"
        if state not in self._printed_states:
            print(f"{prefix} {state}: {message}")
            self._printed_states.add(state)
        else:
            print(f"{prefix} {message}")

        append_json_line(self._session_file, event)
        append_json_line(self._latest_file, event)

    def flush_summary(self, summary: Mapping[str, Any]) -> Path:
        """Persist a manifest summarising the run."""
        manifest_path = self._log_dir / f"{self.script_name}_result.json"
        payload = {
            "generated_at": datetime.now().isoformat(),
            "script": self.script_name,
            **summary,
        }
        if self.subdir:
            payload["subdir"] = self.subdir
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return manifest_path


class RateLimiter:
    """Simple token bucket rate limiter for cooperative throttling."""

    def __init__(self, requests_per_minute: float | None = None) -> None:
        self.requests_per_minute = requests_per_minute
        self._last_call: float | None = None
        self._min_interval = 60.0 / requests_per_minute if requests_per_minute else 0.0

    def wait(self) -> None:
        if not self.requests_per_minute:
            return
        now = time.monotonic()
        if self._last_call is None:
            self._last_call = now
            return
        elapsed = now - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()


def build_retry_session(
    *,
    max_retries: int,
    backoff_factor: float,
    timeout: float,
    allowed_methods: Iterable[str],
    status_forcelist: Iterable[int] | None = None,
) -> Any:
    """Create a requests session with retry/backoff configuration."""
    import requests  # type: ignore[import-untyped]
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry  # type: ignore[import-not-found]

    status_forcelist = list(status_forcelist or DEFAULT_ALLOWED_STATUS)

    retry_config = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        respect_retry_after_header=True,
        allowed_methods=frozenset(method.upper() for method in allowed_methods),
    )

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_config)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.request = _wrap_request_with_timeout(session.request, timeout)
    return session


def _wrap_request_with_timeout(request_func: Callable[..., Any], timeout: float) -> Callable[..., Any]:
    def wrapped(method: str, url: str, **kwargs: Any) -> Any:
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return request_func(method, url, **kwargs)

    return wrapped


def iter_non_empty_lines(text: str) -> Iterator[str]:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped


def hint_for_error(message: str) -> str | None:
    """Return a remediation hint for a known validation error."""
    lowered = message.lower()
    mapping = {
        "missing required field": "Re-run your research prompt and capture that field before retrying.",
        "url does not exist": "Double-check the URL in a browser; if it is correct pass --force to accept redirects.",
        "duplicate entry": "Use --force with a new subdir or update the existing JSON if this is an intentional refresh.",
        "not in allowed values": "Pick one of the enumerated values from the schema file or request a schema update.",
    }
    for key, hint in mapping.items():
        if key in lowered:
            return hint
    return None


@contextlib.contextmanager
def change_cwd(path: Path) -> Iterator[None]:  # pragma: no cover - helper for future scripting
    import os

    original = Path.cwd()
    try:
        if original != path:
            os.chdir(path)
        yield
    finally:
        if Path.cwd() != original:
            os.chdir(original)
