"""Tests for main entry point and orchestration."""

import logging
import runpy
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import main as main_module


def test_get_target_date_range_monday_returns_friday_to_sunday() -> None:
    """Return Friday-Sunday window when today is Monday."""
    monday = datetime(2026, 2, 2)  # Monday

    start_date, end_date = main_module.get_target_date_range(today_override=monday)

    assert start_date == "2026-01-30"
    assert end_date == "2026-02-01"


def test_get_target_date_range_tuesday_returns_yesterday_only() -> None:
    """Return yesterday-only window when today is Tuesday."""
    tuesday = datetime(2026, 2, 3)  # Tuesday

    start_date, end_date = main_module.get_target_date_range(today_override=tuesday)

    assert start_date == "2026-02-02"
    assert end_date == "2026-02-02"


def test_find_config_path_prefers_script_relative_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prefer script-relative config/agencies.yaml over cwd path."""
    script_dir = tmp_path / "package" / "src"
    script_dir.mkdir(parents=True)
    script_file = script_dir / "main.py"
    script_file.write_text("# test", encoding="utf-8")

    script_config = tmp_path / "package" / "config" / "agencies.yaml"
    script_config.parent.mkdir(parents=True)
    script_config.write_text("agencies: []\n", encoding="utf-8")

    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()
    cwd_config = cwd_dir / "config" / "agencies.yaml"
    cwd_config.parent.mkdir(parents=True)
    cwd_config.write_text("agencies: []\n", encoding="utf-8")

    monkeypatch.chdir(cwd_dir)
    monkeypatch.setattr(main_module, "__file__", str(script_file))

    config_path = main_module.find_config_path()

    assert config_path == script_config


def test_find_config_path_falls_back_to_cwd_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use cwd config/agencies.yaml when script-relative file is missing."""
    script_dir = tmp_path / "package" / "src"
    script_dir.mkdir(parents=True)
    script_file = script_dir / "main.py"
    script_file.write_text("# test", encoding="utf-8")

    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()
    cwd_config = cwd_dir / "config" / "agencies.yaml"
    cwd_config.parent.mkdir(parents=True)
    cwd_config.write_text("agencies: []\n", encoding="utf-8")

    monkeypatch.chdir(cwd_dir)
    monkeypatch.setattr(main_module, "__file__", str(script_file))

    config_path = main_module.find_config_path()

    assert config_path.resolve() == cwd_config.resolve()


def test_find_config_path_raises_when_no_config_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raise FileNotFoundError when no config candidate exists."""
    script_dir = tmp_path / "package" / "src"
    script_dir.mkdir(parents=True)
    script_file = script_dir / "main.py"
    script_file.write_text("# test", encoding="utf-8")

    cwd_dir = tmp_path / "cwd"
    cwd_dir.mkdir()

    monkeypatch.chdir(cwd_dir)
    monkeypatch.setattr(main_module, "__file__", str(script_file))

    with pytest.raises(FileNotFoundError):
        main_module.find_config_path()


def test_main_returns_one_when_start_date_is_after_end_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exit code 1 for invalid date range ordering."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "open-go-kr",
            "--start-date",
            "2026-02-03",
            "--end-date",
            "2026-02-02",
        ],
    )

    result = main_module.main()

    assert result == 1


def test_main_returns_one_when_config_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exit code 1 when no config file can be found."""
    monkeypatch.setattr(sys, "argv", ["open-go-kr"])

    def _missing_config() -> Path:
        raise FileNotFoundError("missing agencies.yaml")

    monkeypatch.setattr(
        main_module,
        "find_config_path",
        _missing_config,
    )

    result = main_module.main()

    assert result == 1


def test_main_returns_zero_when_agency_list_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exit code 0 when no agencies are configured."""
    monkeypatch.setattr(
        sys, "argv", ["open-go-kr", "--config", "/tmp/nonexistent-agencies.yaml"]
    )
    monkeypatch.setattr(main_module, "load_agencies", lambda _path: [])

    result = main_module.main()

    assert result == 0


def test_main_returns_one_when_telegram_env_vars_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exit code 1 when Telegram credentials are missing."""
    monkeypatch.setattr(
        sys, "argv", ["open-go-kr", "--config", "/tmp/nonexistent-agencies.yaml"]
    )
    monkeypatch.setattr(
        main_module,
        "load_agencies",
        lambda _path: [SimpleNamespace(code="1342000", name="교육부")],
    )
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    result = main_module.main()

    assert result == 1


def test_main_continues_after_one_agency_api_failure_and_returns_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continue remaining agencies after one API failure and return exit code 1."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "open-go-kr",
            "--config",
            "/tmp/nonexistent-agencies.yaml",
            "--start-date",
            "2026-02-02",
            "--end-date",
            "2026-02-02",
        ],
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setattr(
        main_module,
        "load_agencies",
        lambda _path: [
            SimpleNamespace(code="A1", name="기관1"),
            SimpleNamespace(code="A2", name="기관2"),
        ],
    )

    fetch_calls: list[tuple[str, str, str, str]] = []
    sent_payloads: list[tuple[str, list[tuple[str, list[main_module.Document]]]]] = []

    class FakeClient:
        def fetch_documents(
            self, code: str, name: str, start: str, end: str
        ) -> list[main_module.Document]:
            fetch_calls.append((code, name, start, end))
            if code == "A1":
                raise main_module.OpenGoKrError("API failure")
            return [
                main_module.Document(
                    title="문서",
                    date="2026-02-02",
                    url="",
                    agency_name=name,
                )
            ]

    class FakeNotifier:
        def __init__(self, _bot_token: str, _chat_id: str) -> None:
            pass

        def send_multi_agency_documents(
            self, date: str, results: list[tuple[str, list[main_module.Document]]]
        ) -> bool:
            sent_payloads.append((date, results))
            return True

    monkeypatch.setattr(main_module, "OpenGoKrClient", FakeClient)
    monkeypatch.setattr(main_module, "TelegramNotifier", FakeNotifier)

    result = main_module.main()

    assert result == 1
    assert [call[0] for call in fetch_calls] == ["A1", "A2"]
    assert len(sent_payloads) == 1
    assert sent_payloads[0][1][0][0] == "기관2"


def test_main_returns_one_when_notifier_send_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exit code 1 when consolidated notifier send raises TelegramError."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "open-go-kr",
            "--config",
            "/tmp/nonexistent-agencies.yaml",
            "--start-date",
            "2026-02-02",
            "--end-date",
            "2026-02-02",
        ],
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setattr(
        main_module,
        "load_agencies",
        lambda _path: [SimpleNamespace(code="A1", name="기관1")],
    )

    class FakeClient:
        def fetch_documents(
            self, _code: str, name: str, _start: str, _end: str
        ) -> list[main_module.Document]:
            return [
                main_module.Document(
                    title="문서",
                    date="2026-02-02",
                    url="",
                    agency_name=name,
                )
            ]

    class FakeNotifier:
        def __init__(self, _bot_token: str, _chat_id: str) -> None:
            pass

        def send_multi_agency_documents(
            self, _date: str, _results: list[tuple[str, list[main_module.Document]]]
        ) -> bool:
            raise main_module.TelegramError("notifier failed")

    monkeypatch.setattr(main_module, "OpenGoKrClient", FakeClient)
    monkeypatch.setattr(main_module, "TelegramNotifier", FakeNotifier)

    result = main_module.main()

    assert result == 1


def test_main_returns_zero_when_all_agencies_and_send_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exit code 0 when all agencies succeed and notifier send succeeds."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "open-go-kr",
            "--config",
            "/tmp/nonexistent-agencies.yaml",
            "--start-date",
            "2026-02-02",
            "--end-date",
            "2026-02-02",
        ],
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setattr(
        main_module,
        "load_agencies",
        lambda _path: [
            SimpleNamespace(code="A1", name="기관1"),
            SimpleNamespace(code="A2", name="기관2"),
        ],
    )

    class FakeClient:
        def fetch_documents(
            self, code: str, name: str, _start: str, _end: str
        ) -> list[main_module.Document]:
            if code == "A1":
                return []
            return [
                main_module.Document(
                    title="문서",
                    date="2026-02-02",
                    url="",
                    agency_name=name,
                )
            ]

    sent_payloads: list[tuple[str, list[tuple[str, list[main_module.Document]]]]] = []

    class FakeNotifier:
        def __init__(self, _bot_token: str, _chat_id: str) -> None:
            pass

        def send_multi_agency_documents(
            self, date: str, results: list[tuple[str, list[main_module.Document]]]
        ) -> bool:
            sent_payloads.append((date, results))
            return True

    monkeypatch.setattr(main_module, "OpenGoKrClient", FakeClient)
    monkeypatch.setattr(main_module, "TelegramNotifier", FakeNotifier)

    result = main_module.main()

    assert result == 0
    assert len(sent_payloads) == 1
    assert [agency_name for agency_name, _ in sent_payloads[0][1]] == ["기관1", "기관2"]


def test_main_formats_date_display_as_range_when_start_and_end_differ(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Build date range display when start_date and end_date differ."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "open-go-kr",
            "--config",
            "/tmp/nonexistent-agencies.yaml",
            "--start-date",
            "2026-02-01",
            "--end-date",
            "2026-02-02",
        ],
    )
    monkeypatch.setattr(main_module, "load_agencies", lambda _path: [])

    result = main_module.main()

    assert result == 0
    assert "Fetching documents for date range: 2026-02-01 ~ 2026-02-02" in caplog.text


def test_main_skips_notification_when_all_agencies_return_zero_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip Telegram notification when all agencies return empty document lists."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "open-go-kr",
            "--config",
            "/tmp/nonexistent-agencies.yaml",
            "--start-date",
            "2026-02-02",
            "--end-date",
            "2026-02-02",
        ],
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setattr(
        main_module,
        "load_agencies",
        lambda _path: [
            SimpleNamespace(code="A1", name="기관1"),
            SimpleNamespace(code="A2", name="기관2"),
        ],
    )

    class FakeClient:
        def fetch_documents(
            self, _code: str, _name: str, _start: str, _end: str
        ) -> list[main_module.Document]:
            return []

    sent_payloads: list[tuple[str, list[tuple[str, list[main_module.Document]]]]] = []

    class FakeNotifier:
        def __init__(self, _bot_token: str, _chat_id: str) -> None:
            pass

        def send_multi_agency_documents(
            self, date: str, results: list[tuple[str, list[main_module.Document]]]
        ) -> bool:
            sent_payloads.append((date, results))
            return True

    monkeypatch.setattr(main_module, "OpenGoKrClient", FakeClient)
    monkeypatch.setattr(main_module, "TelegramNotifier", FakeNotifier)

    result = main_module.main()

    assert result == 0
    assert len(sent_payloads) == 0


def test_main_module_entrypoint_exits_with_main_return_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoke module as script and assert SystemExit code from main()."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "open-go-kr",
            "--start-date",
            "2026-02-03",
            "--end-date",
            "2026-02-02",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("main", run_name="__main__")

    assert exc_info.value.code == 1
