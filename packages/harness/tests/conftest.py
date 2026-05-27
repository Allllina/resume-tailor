"""Shared test fixtures."""
from pathlib import Path
import pytest


@pytest.fixture
def repo_root() -> Path:
    """Repo root path. Tests run from packages/harness/."""
    return Path(__file__).resolve().parents[3]
