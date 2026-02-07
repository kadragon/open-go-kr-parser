"""Tests for package metadata exposure."""


def test_star_import_exposes_version() -> None:
    """Expose __version__ when importing from src package."""
    namespace: dict[str, object] = {}
    exec("from src import *", namespace)

    assert namespace["__version__"] == "0.1.0"
