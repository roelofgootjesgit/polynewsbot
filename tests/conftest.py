"""Shared test fixtures."""
import pytest

from src.config.loader import load_config


@pytest.fixture
def default_config() -> dict:
    """Load the default config for tests."""
    return load_config()
