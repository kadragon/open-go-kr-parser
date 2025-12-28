# Project Memory

## Project Overview

**Name:** open-go-kr-parser
**Purpose:** Daily notification service for Korean government original document disclosures
**Created:** 2025-12-28

## Architecture Summary

```
src/open_go_kr_parser/
├── client.py          # API client for open.go.kr
├── notifier.py        # Telegram notification sender
├── config.py          # Configuration loader
└── main.py            # Entry point for GitHub Actions

config/
└── agencies.yaml      # List of agencies to monitor

.github/workflows/
└── daily-notify.yml   # Scheduled workflow (daily)
```

## Key Decisions

1. **API Endpoint:** `https://www.open.go.kr/othicInfo/infoList/orginlInfoList.ajax`
2. **Notification Channel:** Telegram Bot API
3. **Scheduling:** GitHub Actions cron (daily at 09:00 KST)
4. **Configuration:** YAML file for agency list, environment variables for secrets

## Session Log

### 2025-12-28 - Project Initialization
- Created project structure following SDD/TDD principles
- Defined three core specifications: api-client, telegram-notifier, scheduler
- User requirements confirmed: Telegram notification, configurable agencies, no keyword filtering
