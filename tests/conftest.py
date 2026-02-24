"""Shared fixtures for tests."""

import pytest

from capacidad.parser import load_csv


@pytest.fixture(scope="session")
def df():
    """Load the full dataset once for all tests."""
    return load_csv()
