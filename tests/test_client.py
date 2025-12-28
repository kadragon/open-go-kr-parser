# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0001
"""Tests for OpenGoKrClient."""

import pytest
import responses
from requests.exceptions import ConnectionError

from client import Document, OpenGoKrClient, OpenGoKrError


class TestOpenGoKrClient:
    """Test suite for OpenGoKrClient."""

    API_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.ajax"

    @pytest.fixture
    def client(self) -> OpenGoKrClient:
        """Create a client instance for testing."""
        return OpenGoKrClient()

    # TEST-api-client-001: Successfully fetch documents for valid agency and date
    @responses.activate
    def test_fetch_documents_success(self, client: OpenGoKrClient) -> None:
        """Fetch documents successfully for valid agency and date."""
        mock_response = {
            "list": [
                {
                    "othbcSeNm": "원문공개",
                    "insttNm": "교육부",
                    "orginlNm": "2024년 교육정책 보고서",
                    "orginlUrl": "https://example.com/doc1",
                    "othbcDt": "2025-12-27",
                },
                {
                    "othbcSeNm": "원문공개",
                    "insttNm": "교육부",
                    "orginlNm": "학교 시설 관리 지침",
                    "orginlUrl": "https://example.com/doc2",
                    "othbcDt": "2025-12-27",
                },
            ],
            "totalCnt": 2,
        }

        responses.add(
            responses.POST,
            self.API_URL,
            json=mock_response,
            status=200,
        )

        documents = client.fetch_documents("1342000", "2025-12-27")

        assert len(documents) == 2
        assert documents[0].title == "2024년 교육정책 보고서"
        assert documents[0].agency_name == "교육부"
        assert documents[0].url == "https://example.com/doc1"
        assert documents[0].date == "2025-12-27"

    # TEST-api-client-002: Handle empty result gracefully
    @responses.activate
    def test_fetch_documents_empty_result(self, client: OpenGoKrClient) -> None:
        """Return empty list when no documents found."""
        mock_response = {
            "list": [],
            "totalCnt": 0,
        }

        responses.add(
            responses.POST,
            self.API_URL,
            json=mock_response,
            status=200,
        )

        documents = client.fetch_documents("9999999", "2025-12-27")

        assert documents == []

    # TEST-api-client-003: Raise appropriate error on network failure
    @responses.activate
    def test_fetch_documents_network_error(self, client: OpenGoKrClient) -> None:
        """Raise OpenGoKrError on network failure."""
        responses.add(
            responses.POST,
            self.API_URL,
            body=ConnectionError("Network error"),
        )

        with pytest.raises(OpenGoKrError) as exc_info:
            client.fetch_documents("1342000", "2025-12-27")

        error_msg = str(exc_info.value).lower()
        assert "network" in error_msg or "connection" in error_msg

    # TEST-api-client-004: Parse document fields correctly
    @responses.activate
    def test_parse_document_fields(self, client: OpenGoKrClient) -> None:
        """Parse all document fields correctly."""
        mock_response = {
            "list": [
                {
                    "othbcSeNm": "원문공개",
                    "insttNm": "과학기술정보통신부",
                    "orginlNm": "AI 정책 백서 2025",
                    "orginlUrl": "https://example.com/ai-policy",
                    "othbcDt": "2025-12-27",
                },
            ],
            "totalCnt": 1,
        }

        responses.add(
            responses.POST,
            self.API_URL,
            json=mock_response,
            status=200,
        )

        documents = client.fetch_documents("1660000", "2025-12-27")

        assert len(documents) == 1
        doc = documents[0]

        # Verify all fields are correctly parsed
        assert isinstance(doc, Document)
        assert doc.title == "AI 정책 백서 2025"
        assert doc.agency_name == "과학기술정보통신부"
        assert doc.url == "https://example.com/ai-policy"
        assert doc.date == "2025-12-27"

    @responses.activate
    def test_fetch_documents_malformed_response(self, client: OpenGoKrClient) -> None:
        """Raise error on malformed API response."""
        responses.add(
            responses.POST,
            self.API_URL,
            json={"unexpected": "format"},
            status=200,
        )

        with pytest.raises(OpenGoKrError):
            client.fetch_documents("1342000", "2025-12-27")

    @responses.activate
    def test_fetch_documents_pagination(self, client: OpenGoKrClient) -> None:
        """Fetch all pages when documents exceed page size."""
        # First page
        first_page_docs = [
            {
                "othbcSeNm": "원문공개",
                "insttNm": "교육부",
                "orginlNm": f"문서 {i}",
                "orginlUrl": f"https://example.com/{i}",
                "othbcDt": "2025-12-27",
            }
            for i in range(10)
        ]
        responses.add(
            responses.POST,
            self.API_URL,
            json={"list": first_page_docs, "totalCnt": 15},
            status=200,
        )
        # Second page
        second_page_docs = [
            {
                "othbcSeNm": "원문공개",
                "insttNm": "교육부",
                "orginlNm": f"문서 {i}",
                "orginlUrl": f"https://example.com/{i}",
                "othbcDt": "2025-12-27",
            }
            for i in range(10, 15)
        ]
        responses.add(
            responses.POST,
            self.API_URL,
            json={"list": second_page_docs, "totalCnt": 15},
            status=200,
        )

        documents = client.fetch_documents("1342000", "2025-12-27")

        assert len(documents) == 15
