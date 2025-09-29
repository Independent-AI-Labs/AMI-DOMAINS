#!/usr/bin/env python
"""Marketing module setup using uv for dependency management.

Sets up the marketing research environment with all required dependencies
including cloudscraper for anti-bot protection bypass.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def check_uv() -> bool:
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("uv is not installed or not on PATH.")
        logger.info("Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False


def ensure_python(version: str = "3.12") -> None:
    """Ensure Python version is available via uv."""
    find = subprocess.run(["uv", "python", "find", version], capture_output=True, text=True, check=False)
    if find.returncode != 0 or not find.stdout.strip():
        logger.info(f"Installing Python {version} via uv...")
        subprocess.run(["uv", "python", "install", version], check=False)


def setup_venv(module_root: Path) -> bool:
    """Create and sync virtual environment with dependencies."""
    venv_dir = module_root / ".venv"

    # Create venv if it doesn't exist
    if not venv_dir.exists():
        logger.info("Creating virtual environment with Python 3.12...")
        result = subprocess.run(
            ["uv", "venv", "--python", "3.12"], cwd=module_root, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            logger.error("Failed to create virtual environment")
            logger.error(result.stderr)
            return False

    # Sync dependencies (including dev)
    logger.info("Installing dependencies (including cloudscraper for anti-bot)...")
    result = subprocess.run(["uv", "sync", "--dev"], cwd=module_root, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        logger.error("Failed to sync dependencies")
        logger.error(result.stderr)
        return False

    logger.info("✓ All dependencies installed successfully")
    return True


def create_directories(module_root: Path) -> None:
    """Create required directory structure for research."""
    dirs = [
        "research/ai-enablers/links-and-sources/validated",
        "research/ai-enablers/data-models/validated",
        "research/ai-enablers/logs",
        "research/ai-enablers/downloads",
        "research/ai-enablers/requirements-and-schemas/requirements",
        "research/ai-enablers/requirements-and-schemas/schemas",
    ]

    for dir_path in dirs:
        full_path = module_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)

    logger.info("✓ Directory structure created")


def install_pre_commit(module_root: Path) -> None:
    """Install pre-commit hooks if config exists."""
    config = module_root / ".pre-commit-config.yaml"
    if not config.exists():
        # Create basic pre-commit config
        config_content = """repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
"""
        config.write_text(config_content)

    logger.info("Installing pre-commit hooks...")
    subprocess.run(["uv", "run", "pre-commit", "install"], cwd=module_root, check=False)


def test_imports(module_root: Path) -> bool:
    """Test that all required imports work."""
    test_script = """
import sys
try:
    import requests
    import bs4
    import cloudscraper
    print("✓ All required imports successful")
    sys.exit(0)
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
"""

    # Write test script
    test_file = module_root / "test_imports.py"
    test_file.write_text(test_script)

    # Run test
    result = subprocess.run(["uv", "run", "python", "test_imports.py"], cwd=module_root, capture_output=True, text=True)

    # Clean up
    test_file.unlink()

    if result.returncode == 0:
        logger.info(result.stdout.strip())
        return True
    else:
        logger.error(result.stdout.strip())
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up marketing module environment")
    parser.add_argument(
        "--module-dir", type=Path, default=Path(__file__).resolve().parent, help="Marketing module directory"
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip import tests")
    args = parser.parse_args()

    module_root = args.module_dir

    logger.info("=" * 60)
    logger.info("Marketing Module Setup")
    logger.info(f"Module root: {module_root}")
    logger.info("=" * 60)

    # Check prerequisites
    if not check_uv():
        return 1

    ensure_python("3.12")

    # Setup environment
    if not setup_venv(module_root):
        return 1

    # Create directory structure
    create_directories(module_root)

    # Install pre-commit
    install_pre_commit(module_root)

    # Test imports
    if not args.skip_tests:
        if not test_imports(module_root):
            logger.error("Import test failed - check dependencies")
            return 1

    logger.info("=" * 60)
    logger.info("Marketing Module Setup Complete!")
    logger.info("")
    logger.info("Activate the environment:")
    if sys.platform == "win32":
        logger.info(f"  {module_root}\\.venv\\Scripts\\activate")
    else:
        logger.info(f"  source {module_root}/.venv/bin/activate")
    logger.info("")
    logger.info("Run validation scripts:")
    logger.info("  uv run python scripts/add_link.py --help")
    logger.info("  uv run python scripts/validate_and_save.py --help")
    logger.info("")
    logger.info("Or use the research mode:")
    logger.info("  ./scripts/research.sh")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
