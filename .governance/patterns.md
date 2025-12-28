# Design Patterns

## API Client Pattern

```python
class OpenGoKrClient:
    """Stateless client for open.go.kr API."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self._setup_headers()

    def fetch_documents(self, agency_code: str, date: str) -> list[Document]:
        """Fetch documents for a specific agency and date."""
        pass
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
