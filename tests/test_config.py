# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0004
"""Tests for configuration loader."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from config import Agency, load_agencies


class TestLoadAgencies:
    """Test suite for agency configuration loading."""

    def test_load_agencies_success(self) -> None:
        """Load agencies from valid YAML file."""
        yaml_content = """
agencies:
  - code: "1342000"
    name: "교육부"
  - code: "1741000"
    name: "행정안전부"
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            agencies = load_agencies(Path(f.name))

            assert len(agencies) == 2
            assert agencies[0].code == "1342000"
            assert agencies[0].name == "교육부"
            assert agencies[1].code == "1741000"
            assert agencies[1].name == "행정안전부"

    def test_load_agencies_empty_list(self) -> None:
        """Return empty list when no agencies configured."""
        yaml_content = """
agencies: []
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            agencies = load_agencies(Path(f.name))

            assert agencies == []

    def test_load_agencies_file_not_found(self) -> None:
        """Raise error when config file not found."""
        with pytest.raises(FileNotFoundError):
            load_agencies(Path("/nonexistent/path/config.yaml"))

    def test_agency_dataclass(self) -> None:
        """Agency dataclass has correct fields."""
        agency = Agency(code="1342000", name="교육부")
        assert agency.code == "1342000"
        assert agency.name == "교육부"
