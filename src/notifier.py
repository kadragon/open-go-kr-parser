# Trace: spec_id=SPEC-telegram-notifier-001 task_id=TASK-0002
"""Telegram notification service for document alerts."""

import requests

from client import Document


class TelegramError(Exception):
    """Exception for Telegram API errors."""

    pass


class TelegramNotifier:
    """Send notifications via Telegram Bot API."""

    API_BASE = "https://api.telegram.org"
    MAX_MESSAGE_LENGTH = 4096

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """Initialize notifier with Telegram credentials.

        Args:
            bot_token: Telegram bot token from BotFather.
            chat_id: Target chat ID for notifications.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.session = requests.Session()

    @property
    def _api_url(self) -> str:
        """Get the sendMessage API endpoint URL."""
        return f"{self.API_BASE}/bot{self.bot_token}/sendMessage"

    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for MarkdownV2.

        Args:
            text: Text to escape.

        Returns:
            Escaped text safe for MarkdownV2.
        """
        special_chars = "_*[]()~`>#+-=|{}.!"
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        return text

    def _format_title(self, document: Document) -> str:
        """Format document title with optional link suffix.

        Args:
            document: Document to format.

        Returns:
            Escaped title string for MarkdownV2.
        """
        title = document.title
        if document.url:
            title = f"{title} [바로가기]"
        return self._escape_markdown(title)

    def _format_documents_message(
        self, agency_name: str, date: str, documents: list[Document]
    ) -> str:
        """Format documents into a Telegram message.

        Args:
            agency_name: Name of the agency.
            date: Date of the documents.
            documents: List of documents to format.

        Returns:
            Formatted message string.
        """
        if not documents:
            escaped_agency = self._escape_markdown(agency_name)
            escaped_date = self._escape_markdown(date)
            return (
                f"📋 *{escaped_agency} 원문정보 \\({escaped_date}\\)*\n\n"
                "공개된 문서가 없습니다\\."
            )

        escaped_agency = self._escape_markdown(agency_name)
        escaped_date = self._escape_markdown(date)
        header = f"📋 *{escaped_agency} 원문정보 \\({escaped_date}\\)*\n\n"

        lines = []
        for i, doc in enumerate(documents, 1):
            escaped_title = self._format_title(doc)
            if doc.url:
                lines.append(f"{i}\\. [{escaped_title}]({doc.url})")
            else:
                lines.append(f"{i}\\. {escaped_title}")

        footer = f"\n\n총 {len(documents)}건"
        return header + "\n".join(lines) + footer

    def _split_message(self, message: str) -> list[str]:
        """Split message into chunks that fit Telegram's limit.

        Args:
            message: Full message to split.

        Returns:
            List of message chunks.
        """
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return [message]

        chunks = []
        lines = message.split("\n")
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > self.MAX_MESSAGE_LENGTH:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _send_message(self, text: str) -> bool:
        """Send a single message via Telegram API.

        Args:
            text: Message text to send.

        Returns:
            True if successful.

        Raises:
            TelegramError: On API errors.
        """
        try:
            response = self.session.post(
                self._api_url,
                data={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": "true",
                },
                timeout=30,
            )

            result = response.json()

            if not result.get("ok"):
                error_code = result.get("error_code", "unknown")
                description = result.get("description", "Unknown error")
                raise TelegramError(f"Telegram API error {error_code}: {description}")

            return True

        except requests.exceptions.RequestException as e:
            raise TelegramError(f"Network error: {e}") from e

    def send_documents(
        self, agency_name: str, date: str, documents: list[Document]
    ) -> bool:
        """Send document list notification.

        Args:
            agency_name: Name of the agency.
            date: Date of the documents.
            documents: List of documents to notify about.

        Returns:
            True if all messages sent successfully.

        Raises:
            TelegramError: On API or network errors.
        """
        message = self._format_documents_message(agency_name, date, documents)
        chunks = self._split_message(message)

        for chunk in chunks:
            self._send_message(chunk)

        return True

    def send_multi_agency_documents(
        self, date: str, agencies_documents: list[tuple[str, list[Document]]]
    ) -> bool:
        """Send consolidated notification for multiple agencies.

        Args:
            date: Date or date range string.
            agencies_documents: List of (agency_name, documents) tuples.

        Returns:
            True if all messages sent successfully.

        Raises:
            TelegramError: On API or network errors.
        """
        message = self._format_multi_agency_message(date, agencies_documents)
        chunks = self._split_message(message)

        for chunk in chunks:
            self._send_message(chunk)

        return True

    def _format_multi_agency_message(
        self, date: str, agencies_documents: list[tuple[str, list[Document]]]
    ) -> str:
        """Format documents from multiple agencies into a single message.

        Args:
            date: Date or date range string.
            agencies_documents: List of (agency_name, documents) tuples.

        Returns:
            Formatted message string with all agencies.
        """
        if not agencies_documents:
            escaped_date = self._escape_markdown(date)
            return f"📋 *원문정보 \\({escaped_date}\\)*\n\n공개된 문서가 없습니다\\."

        # Count total documents
        total_docs = sum(len(docs) for _, docs in agencies_documents)
        agency_count = len(agencies_documents)

        escaped_date = self._escape_markdown(date)
        header = (
            f"📋 *원문정보 \\({escaped_date}\\)*\n\n"
            f"총 {agency_count}개 부서, {total_docs}건\n\n"
        )

        sections = []
        for agency_name, documents in agencies_documents:
            if not documents:
                continue

            escaped_agency = self._escape_markdown(agency_name)
            section_header = f"▫️ *{escaped_agency}* \\({len(documents)}건\\)\n"

            lines = []
            for i, doc in enumerate(documents, 1):
                escaped_title = self._format_title(doc)
                if doc.url:
                    lines.append(f"  {i}\\. [{escaped_title}]({doc.url})")
                else:
                    lines.append(f"  {i}\\. {escaped_title}")

            section = section_header + "\n".join(lines)
            sections.append(section)

        return header + "\n\n".join(sections)
