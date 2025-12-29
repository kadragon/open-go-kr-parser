# Design Patterns

## API Client Pattern (XSRF Token Authentication)

When an API requires XSRF token authentication, use two-step request pattern:

```python
class OpenGoKrClient:
    """Client using XSRF token for AJAX endpoint access."""
    PAGE_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do"
    AJAX_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.ajax"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._xsrf_token: str | None = None
        self._setup_headers()

    def _acquire_xsrf_token(self) -> str:
        """Step 1: Acquire XSRF token from cookies."""
        response = self.session.post(self.PAGE_URL, data=minimal_params)
        token = self.session.cookies.get("XSRF-TOKEN")
        if not token:
            raise OpenGoKrError("Failed to obtain XSRF token")
        return token

    def _ensure_xsrf_token(self) -> None:
        """Ensure we have a valid XSRF token."""
        if not self._xsrf_token:
            self._xsrf_token = self._acquire_xsrf_token()
            self.session.headers["x-xsrf-token"] = self._xsrf_token

    def fetch_documents(self, agency_code: str, agency_name: str, date: str) -> list[Document]:
        """Step 2: POST to AJAX endpoint with token."""
        self._ensure_xsrf_token()  # Acquire if needed
        response = self.session.post(self.AJAX_URL, data={...})
        data = response.json()  # Direct JSON response
        return self._parse_response(data)

    def _build_detail_url(self, reg_no: str, prod_dt: str, inst_se_cd: str) -> str:
        """Build document detail URL from response fields."""
        return (
            f"https://www.open.go.kr/othicInfo/infoList/infoListDetl.do"
            f"?prdnNstRgstNo={reg_no}&prdnDt={prod_dt}&nstSeCd={inst_se_cd}"
        )
```

## Configuration Pattern

```python
@dataclass
class AgencyConfig:
    code: str
    name: str

def load_agencies(path: Path) -> list[AgencyConfig]:
    """Load agency configuration from YAML file."""
    pass
```

## Notification Pattern

```python
class TelegramNotifier:
    """Send notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, text: str) -> bool:
        """Send a message to the configured chat."""
        pass
```

## Error Handling Pattern

- Use custom exceptions for domain errors
- Log errors with context
- Graceful degradation (partial failure handling)
