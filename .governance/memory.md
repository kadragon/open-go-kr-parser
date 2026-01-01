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

1. **API Approach:** POST to page URL and parse embedded JSON from HTML (not AJAX endpoint)
2. **Page URL:** `https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do`
3. **Notification Channel:** Telegram Bot API
4. **Scheduling:** GitHub Actions cron (daily at 09:00 KST)
5. **Configuration:** YAML file for agency list, environment variables for secrets

## Critical API Knowledge

**IMPORTANT:** The open.go.kr AJAX endpoint requires an XSRF token that is generated client-side by JavaScript. This makes direct API calls impossible without browser automation.

**Solution:** POST form data to the page URL (`.do`), and extract embedded JSON from the HTML response:
```python
# Response contains: var result = {"rtnList": [...], "rtnTotal": 15};
match = re.search(r"var\s+result\s*=\s*(\{.*?\});", html, re.DOTALL)
```

**Response field mapping:**
- `rtnList` → list of documents (not `list`)
- `rtnTotal` → total count (not `totalCnt`)
- `INFO_SJ` → document title
- `PRDCTN_DT` → production date (YYYYMMDDHHMMSS format)
- `PROC_INSTT_NM` → agency name

## Session Log

### 2025-12-28 - Project Initialization
- Created project structure following SDD/TDD principles
- Defined three core specifications: api-client, telegram-notifier, scheduler
- User requirements confirmed: Telegram notification, configurable agencies, no keyword filtering

### 2025-12-29 - Critical Bug Fix (TASK-0006)
- Fixed "Invalid response format: missing 'list' field" production error
- Root cause: AJAX endpoint requires client-side JavaScript-generated XSRF token
- Solution: Changed from AJAX to HTML parsing approach
- Used Chrome DevTools MCP to investigate actual browser behavior
- Integration test verified: fetched 8 documents across 3 agencies

### 2025-12-29 - Date Range Query Optimization
- Changed from per-day API calls to single date-range query
- Previously: Monday fetched Fri/Sat/Sun with 3 separate API calls per agency
- Now: Single API call with startDate~endDate range (e.g., "20251227" ~ "20251229")
- CLI args changed: `--dates` → `--start-date` and `--end-date`
- `get_target_dates()` → `get_target_date_range()` returning (start, end) tuple
- Reduces API load and improves efficiency

### 2025-12-29 - AJAX Endpoint with XSRF Token (TASK-0007)
- **Problem:** Document URLs were missing (`url=""` hardcoded)
- **Solution:** Switched from HTML parsing to AJAX endpoint with XSRF token authentication
- **Key Changes:**
  - Added XSRF token acquisition: POST to `.do` page → Extract from cookies
  - Switched to AJAX endpoint: `orginlInfoList.ajax` instead of HTML parsing
  - Headers updated: `X-Requested-With: XMLHttpRequest`, `Accept: application/json`
  - URL construction from response fields: `PRDCTN_INSTT_REGIST_NO`, `PRDCTN_DT`, `INSTT_SE_CD`
  - URL pattern: `https://www.open.go.kr/othicInfo/infoList/infoListDetl.do?prdnNstRgstNo={reg_no}&prdnDt={prod_dt}&nstSeCd={inst_se_cd}`
- **Multi-Agency Message Consolidation:**
  - Changed from per-agency messages to single consolidated message
  - All agencies in one Telegram message with sections
  - Format: "📋 원문정보 (date)\n\n총 N개 부서, M건\n\n▫️ 부서명 (X건)\n  1. [문서](url)\n..."
- **Token Management:**
  - Token acquired once per session and reused
  - Automatic refresh on 401/403 errors (one retry)
  - Cached in session headers for all AJAX requests
- **Response Format:** AJAX and HTML responses use SAME field names (rtnList, INFO_SJ, etc.)
- **Testing:** Added XSRF token mocking, URL validation, token caching tests

### 2025-12-29 - Code Quality Refactor (TASK-0008)
- Centralized client timeout and XSRF token payload into class constants
- Moved Document import in main.py to module top-level
- No behavior changes intended; tests not run

### 2025-12-29 - Lint Fix (TASK-0009)
- Wrapped long list comprehension lines in tests to satisfy ruff E501

### 2025-12-29 - Format Cleanup (TASK-0010)
- Applied ruff format to src/client.py and tests/test_client.py

### 2026-01-01 - Revert to HTML Parsing (TASK-0011)
- **Production issue**: GitHub Actions workflow failing with "XSRF-TOKEN not found in response cookies"
- **Root cause**: open.go.kr server stopped providing XSRF-TOKEN cookie (changed between 2025-12-29 and 2026-01-01)
- **Investigation**: Tested XSRF token acquisition locally - confirmed cookie is no longer set by server
- **Solution**: Reverted from AJAX + XSRF token approach (PR #6) back to HTML parsing approach
- **Key lesson**: HTML parsing approach is more stable than AJAX with token authentication for this API
- **Files changed**:
  - `src/client.py`: Reverted to HTML parsing implementation (removed all XSRF token logic)
  - `tests/test_client.py`: Updated all 6 tests to mock HTML responses instead of AJAX JSON
  - `.spec/api-client/spec.yaml`: Updated to reflect HTML parsing approach
- **Tradeoffs**: URLs are no longer available (set to empty string) - acceptable for notification use case
- All tests passing (6/6) with 94% coverage
- Integration verified: Successfully fetched 4 documents for 교육부 on 2025-12-31
