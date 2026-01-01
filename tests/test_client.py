# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0011
"""Tests for OpenGoKrClient."""

import pytest
import responses

from client import Document, OpenGoKrClient, OpenGoKrError


class TestOpenGoKrClient:
    """Test suite for OpenGoKrClient."""

    PAGE_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do"

    @pytest.fixture
    def client(self) -> OpenGoKrClient:
        """Create a client instance for testing."""
        return OpenGoKrClient()

    def _make_html_response(
        self, rtn_list: list[dict[str, str]], rtn_total: int
    ) -> str:
        """Create mock HTML response with embedded JSON."""
        import json

        result_json = json.dumps({"rtnList": rtn_list, "rtnTotal": rtn_total})
        return f"""
        <html>
        <head><title>Test</title></head>
        <body>
        <script>
        var result = {result_json};
        </script>
        </body>
        </html>
        """

    # TEST-api-client-001: Successfully fetch documents for valid agency and date
    @responses.activate
    def test_fetch_documents_success(self, client: OpenGoKrClient) -> None:
        """Fetch documents successfully for valid agency and date."""
        mock_docs = [
            {
                "INFO_SJ": "2024년 교육정책 보고서",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
            },
            {
                "INFO_SJ": "학교 시설 관리 지침",
                "PRDCTN_DT": "20251227140000",
                "PROC_INSTT_NM": "교육부",
            },
        ]

        responses.add(
            responses.POST,
            self.PAGE_URL,
            body=self._make_html_response(mock_docs, 2),
            status=200,
        )

        documents = client.fetch_documents("1342000", "교육부", "2025-12-27")

        assert len(documents) == 2
        assert documents[0].title == "2024년 교육정책 보고서"
        assert documents[0].agency_name == "교육부"
        assert documents[0].date == "2025-12-27"
        # URL not available in HTML parsing approach
        assert documents[0].url == ""

    # TEST-api-client-002: Handle empty result gracefully
    @responses.activate
    def test_fetch_documents_empty_result(self, client: OpenGoKrClient) -> None:
        """Return empty list when no documents found."""
        responses.add(
            responses.POST,
            self.PAGE_URL,
            body=self._make_html_response([], 0),
            status=200,
        )

        documents = client.fetch_documents("9999999", "존재하지않는기관", "2025-12-27")

        assert documents == []

    # TEST-api-client-003: Raise appropriate error on network failure
    @responses.activate
    def test_fetch_documents_network_error(self, client: OpenGoKrClient) -> None:
        """Raise OpenGoKrError on network failure."""
        from requests.exceptions import ConnectionError

        responses.add(
            responses.POST,
            self.PAGE_URL,
            body=ConnectionError("Network error"),
        )

        with pytest.raises(OpenGoKrError) as exc_info:
            client.fetch_documents("1342000", "교육부", "2025-12-27")

        error_msg = str(exc_info.value).lower()
        assert "network" in error_msg or "connection" in error_msg

    # TEST-api-client-004: Parse document fields correctly
    @responses.activate
    def test_parse_document_fields(self, client: OpenGoKrClient) -> None:
        """Parse all document fields correctly."""
        mock_docs = [
            {
                "INFO_SJ": "AI 정책 백서 2025",
                "PRDCTN_DT": "20251227093015",
                "PROC_INSTT_NM": "과학기술정보통신부",
            },
        ]

        responses.add(
            responses.POST,
            self.PAGE_URL,
            body=self._make_html_response(mock_docs, 1),
            status=200,
        )

        documents = client.fetch_documents(
            "1660000", "과학기술정보통신부", "2025-12-27"
        )

        assert len(documents) == 1
        doc = documents[0]

        assert isinstance(doc, Document)
        assert doc.title == "AI 정책 백서 2025"
        assert doc.agency_name == "과학기술정보통신부"
        assert doc.date == "2025-12-27"
        # URL not available in HTML parsing approach
        assert doc.url == ""

    @responses.activate
    def test_fetch_documents_invalid_html_raises_error(
        self, client: OpenGoKrClient
    ) -> None:
        """Raise error when result data is not found in HTML."""
        responses.add(
            responses.POST,
            self.PAGE_URL,
            body="<html><body>No result data here</body></html>",
            status=200,
        )

        with pytest.raises(OpenGoKrError) as exc_info:
            client.fetch_documents("1342000", "교육부", "2025-12-27")

        assert "Could not find result data" in str(exc_info.value)

    @responses.activate
    def test_fetch_documents_pagination(self, client: OpenGoKrClient) -> None:
        """Fetch all pages when documents exceed page size."""
        # First page
        first_page_docs = [
            {
                "INFO_SJ": f"문서 {i}",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
            }
            for i in range(10)
        ]
        responses.add(
            responses.POST,
            self.PAGE_URL,
            body=self._make_html_response(first_page_docs, 15),
            status=200,
        )
        # Second page
        second_page_docs = [
            {
                "INFO_SJ": f"문서 {i}",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
            }
            for i in range(10, 15)
        ]
        responses.add(
            responses.POST,
            self.PAGE_URL,
            body=self._make_html_response(second_page_docs, 15),
            status=200,
        )

        documents = client.fetch_documents("1342000", "교육부", "2025-12-27")

        assert len(documents) == 15
