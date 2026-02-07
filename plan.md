# Test Coverage Upgrade Plan

## Baseline (2026-02-07)

- Total coverage: 58% (`163/281`)
- Test command: `uv run pytest -q --cov=src --cov-report=term-missing`
- Biggest gaps:
  - `src/main.py`: 0% (83 missed lines)
  - `src/notifier.py`: 73% (29 missed lines)
  - `src/client.py`: 93% (5 missed lines)
  - `src/__init__.py`: 0% (1 missed line)

## Target

- Phase 1 target: >= 75% total coverage (cover `main.py` core control flow + notifier multi-agency path)
- Phase 2 target: >= 85% total coverage (cover remaining error/edge branches)

## Backlog (One Item = One Behavioral Test)

### `src/__init__.py`

- [x] Add test: importing `src` exposes `__version__ == "0.1.0"`

### `src/client.py` (missing: 109-110, 188, 190, 205)

- [x] Add test: invalid embedded JSON in HTML raises `OpenGoKrError` parse failure
- [x] Add test: request timeout raises `OpenGoKrError` containing timeout context
- [x] Add test: non-timeout request exception raises `OpenGoKrError` request failed
- [x] Add test: pagination stops when returned page size is smaller than `PAGE_SIZE`

### `src/notifier.py` (missing: 179, 220-226, 240-274)

- [x] Add test: `_send_message` wraps `requests` network failure as `TelegramError`
- [x] Add test: `send_multi_agency_documents` returns `True` on successful API post
- [x] Add test: `send_multi_agency_documents` sends multiple chunks when message exceeds 4096 chars
- [x] Add test: `_format_multi_agency_message` returns no-document message when input is empty
- [x] Add test: `_format_multi_agency_message` header includes agency count and total document count
- [x] Add test: `_format_multi_agency_message` skips agencies with zero documents
- [x] Add test: `_format_multi_agency_message` formats link entries with escaped title and URL
- [x] Add test: `_format_multi_agency_message` formats entries without URLs as plain numbered lines

### `src/main.py` (missing: 5-183)

- [x] Add test: `get_target_date_range` returns Friday-Sunday window when today is Monday
- [x] Add test: `get_target_date_range` returns yesterday-only window when today is Tuesday
- [x] Add test: `find_config_path` prefers script-relative `config/agencies.yaml` when present
- [x] Add test: `find_config_path` falls back to cwd `config/agencies.yaml` when script-relative is absent
- [x] Add test: `find_config_path` raises `FileNotFoundError` when no candidate exists
- [x] Add test: `main` returns `1` when `--start-date` is after `--end-date`
- [x] Add test: `main` returns `1` when config file is missing
- [x] Add test: `main` returns `0` when agency list is empty
- [x] Add test: `main` returns `1` when Telegram env vars are missing
- [x] Add test: `main` continues after one agency API failure and returns `1` if any agency failed
- [x] Add test: `main` returns `1` when notifier send fails with `TelegramError`
- [x] Add test: `main` returns `0` when all agencies process successfully and consolidated send succeeds
- [x] Add test: `main` formats date display as range when start/end differ
- [x] Add test: module entrypoint (`__main__`) exits with `main()` return code

## Execution Rule

- Run each item with strict TDD cycle: Red -> Green -> Refactor -> mark done.
- Mark an item complete only after:
  - the new test exists,
  - the new test passes,
  - full suite passes.
