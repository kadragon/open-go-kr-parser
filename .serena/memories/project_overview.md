## Project Overview

### Purpose
Monitors the Korean government disclosure portal (open.go.kr) for document disclosures by agency and sends daily notifications via a Telegram bot.

### Tech Stack
Python 3.14+, requests, PyYAML, pytest, ruff, mypy (strict).

### Structure
- src/: application code (client, notifier, config loader, main entrypoint)
- config/: agencies.yaml with monitored agencies
- tests/: pytest test suite
- .github/workflows/: CI and scheduled notifications
