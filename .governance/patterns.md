# Design Patterns

## API Client Pattern (HTML Parsing)

When an API requires client-side JavaScript tokens (XSRF/CSRF), use HTML parsing:

```python
class OpenGoKrClient:
    """Client using HTML parsing to bypass XSRF requirements."""
    PAGE_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._setup_headers()

    def _extract_result_from_html(self, html: str) -> dict:
        """Extract embedded JSON from HTML response."""
        # Pattern: var result = {...};
        match = re.search(r"var\s+result\s*=\s*(\{.*?\});", html, re.DOTALL)
        if not match:
            raise OpenGoKrError("Could not find result data")
        return json.loads(match.group(1))

    def fetch_documents(self, agency_code: str, agency_name: str, date: str) -> list[Document]:
        """POST to page URL and parse embedded JSON."""
        response = self.session.post(self.PAGE_URL, data={...})
        data = self._extract_result_from_html(response.text)
        return self._parse_response(data)
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
