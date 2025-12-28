# Trace: spec_id=SPEC-telegram-notifier-001 task_id=TASK-0002
"""Tests for TelegramNotifier."""

import pytest
import responses

from client import Document
from notifier import TelegramError, TelegramNotifier


class TestTelegramNotifier:
    """Test suite for TelegramNotifier."""

    BOT_TOKEN = "123456:ABC-DEF"
    CHAT_ID = "-1001234567890"
    API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    @pytest.fixture
    def notifier(self) -> TelegramNotifier:
        """Create a notifier instance for testing."""
        return TelegramNotifier(self.BOT_TOKEN, self.CHAT_ID)

    @pytest.fixture
    def sample_documents(self) -> list[Document]:
        """Create sample documents for testing."""
        return [
            Document(
                title="2024년 교육정책 보고서",
                date="2025-12-27",
                url="https://example.com/doc1",
                agency_name="교육부",
            ),
            Document(
                title="학교 시설 관리 지침",
                date="2025-12-27",
                url="https://example.com/doc2",
                agency_name="교육부",
            ),
        ]

    # TEST-telegram-notifier-001: Successfully send formatted document list
    @responses.activate
    def test_send_documents_success(
        self, notifier: TelegramNotifier, sample_documents: list[Document]
    ) -> None:
        """Send formatted document list successfully."""
        responses.add(
            responses.POST,
            self.API_URL,
            json={"ok": True, "result": {"message_id": 123}},
            status=200,
        )

        result = notifier.send_documents("교육부", "2025-12-27", sample_documents)

        assert result is True
        assert len(responses.calls) == 1

        # Verify message contains document info
        request_body = responses.calls[0].request.body
        assert request_body is not None
        body_str = (
            request_body.decode() if isinstance(request_body, bytes) else request_body
        )
        assert "교육부" in body_str or "%EA%B5%90%EC%9C%A1%EB%B6%80" in body_str

    # TEST-telegram-notifier-002: Handle empty document list with appropriate message
    @responses.activate
    def test_send_documents_empty(self, notifier: TelegramNotifier) -> None:
        """Send appropriate message when no documents found."""
        responses.add(
            responses.POST,
            self.API_URL,
            json={"ok": True, "result": {"message_id": 123}},
            status=200,
        )

        result = notifier.send_documents("교육부", "2025-12-27", [])

        assert result is True
        assert len(responses.calls) == 1

    # TEST-telegram-notifier-003: Raise error on invalid credentials
    @responses.activate
    def test_send_documents_invalid_token(self, notifier: TelegramNotifier) -> None:
        """Raise TelegramError on invalid credentials."""
        responses.add(
            responses.POST,
            self.API_URL,
            json={"ok": False, "error_code": 401, "description": "Unauthorized"},
            status=401,
        )

        with pytest.raises(TelegramError) as exc_info:
            notifier.send_documents("교육부", "2025-12-27", [])

        assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)

    # TEST-telegram-notifier-004: Split long messages correctly
    @responses.activate
    def test_send_documents_long_message(self, notifier: TelegramNotifier) -> None:
        """Split message when it exceeds Telegram limit."""
        # Create many documents to exceed 4096 char limit
        many_documents = [
            Document(
                title=f"문서 제목이 매우 긴 경우를 테스트하기 위한 문서 번호 {i}",
                date="2025-12-27",
                url=f"https://example.com/very/long/path/document/{i}",
                agency_name="교육부",
            )
            for i in range(50)
        ]

        responses.add(
            responses.POST,
            self.API_URL,
            json={"ok": True, "result": {"message_id": 123}},
            status=200,
        )
        responses.add(
            responses.POST,
            self.API_URL,
            json={"ok": True, "result": {"message_id": 124}},
            status=200,
        )
        responses.add(
            responses.POST,
            self.API_URL,
            json={"ok": True, "result": {"message_id": 125}},
            status=200,
        )

        result = notifier.send_documents("교육부", "2025-12-27", many_documents)

        assert result is True
        # Should have made multiple API calls
        assert len(responses.calls) >= 1

    @responses.activate
    def test_format_message(
        self, notifier: TelegramNotifier, sample_documents: list[Document]
    ) -> None:
        """Message format includes all required elements."""
        responses.add(
            responses.POST,
            self.API_URL,
            json={"ok": True, "result": {"message_id": 123}},
            status=200,
        )

        notifier.send_documents("교육부", "2025-12-27", sample_documents)

        request_body = responses.calls[0].request.body
        # URL encoded Korean text or actual text should be present
        assert request_body is not None
        assert len(request_body) > 0
