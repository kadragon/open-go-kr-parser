# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0001
"""Tests for OpenGoKrClient."""

import pytest
import responses

from client import Document, OpenGoKrClient, OpenGoKrError


class TestOpenGoKrClient:
    """Test suite for OpenGoKrClient."""

    PAGE_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do"
    AJAX_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.ajax"

    @pytest.fixture
    def client(self) -> OpenGoKrClient:
        """Create a client instance for testing."""
        return OpenGoKrClient()

    def _make_ajax_response(
        self, rtn_list: list[dict[str, str]], rtn_total: int
    ) -> dict:
        """Create mock AJAX JSON response."""
        return {"result": {"rtnList": rtn_list, "rtnTotal": rtn_total}}

    def _mock_xsrf_token(self) -> None:
        """Add XSRF token mock response."""
        responses.add(
            responses.POST,
            self.PAGE_URL,
            headers={"Set-Cookie": "XSRF-TOKEN=mock-token-123; Path=/"},
            body="",
            status=200,
        )

    # TEST-api-client-001: Successfully fetch documents for valid agency and date
    @responses.activate
    def test_fetch_documents_success(self, client: OpenGoKrClient) -> None:
        """Fetch documents successfully for valid agency and date."""
        self._mock_xsrf_token()

        mock_docs = [
            {
                "INFO_SJ": "2024년 교육정책 보고서",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
                "PRDCTN_INSTT_REGIST_NO": "DCT88209A2A1A26554804C2D0F2F351816D",
                "INSTT_SE_CD": "C",
            },
            {
                "INFO_SJ": "학교 시설 관리 지침",
                "PRDCTN_DT": "20251227140000",
                "PROC_INSTT_NM": "교육부",
                "PRDCTN_INSTT_REGIST_NO": "DCT768E063D7947E73B2F16E1C2EC093A5B",
                "INSTT_SE_CD": "C",
            },
        ]

        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response(mock_docs, 2),
            status=200,
        )

        documents = client.fetch_documents("1342000", "교육부", "2025-12-27")

        assert len(documents) == 2
        assert documents[0].title == "2024년 교육정책 보고서"
        assert documents[0].agency_name == "교육부"
        assert documents[0].date == "2025-12-27"
        # Verify URL is constructed correctly
        assert "prdnNstRgstNo=DCT88209A2A1A26554804C2D0F2F351816D" in documents[0].url
        assert "prdnDt=20251227120000" in documents[0].url
        assert "nstSeCd=C" in documents[0].url

    # TEST-api-client-002: Handle empty result gracefully
    @responses.activate
    def test_fetch_documents_empty_result(self, client: OpenGoKrClient) -> None:
        """Return empty list when no documents found."""
        self._mock_xsrf_token()

        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response([], 0),
            status=200,
        )

        documents = client.fetch_documents("9999999", "존재하지않는기관", "2025-12-27")

        assert documents == []

    # TEST-api-client-003: Raise appropriate error on network failure
    @responses.activate
    def test_fetch_documents_network_error(self, client: OpenGoKrClient) -> None:
        """Raise OpenGoKrError on network failure."""
        from requests.exceptions import ConnectionError

        self._mock_xsrf_token()

        responses.add(
            responses.POST,
            self.AJAX_URL,
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
        self._mock_xsrf_token()

        mock_docs = [
            {
                "INFO_SJ": "AI 정책 백서 2025",
                "PRDCTN_DT": "20251227093015",
                "PROC_INSTT_NM": "과학기술정보통신부",
                "PRDCTN_INSTT_REGIST_NO": "DCTA8E6643D6E5FB1A6C4E51D3F09BF2B04",
                "INSTT_SE_CD": "C",
            },
        ]

        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response(mock_docs, 1),
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
        # Verify URL is constructed
        assert doc.url != ""
        assert "prdnNstRgstNo=DCTA8E6643D6E5FB1A6C4E51D3F09BF2B04" in doc.url

    @responses.activate
    def test_fetch_documents_invalid_json_raises_error(
        self, client: OpenGoKrClient
    ) -> None:
        """Raise error when JSON parsing fails."""
        self._mock_xsrf_token()

        responses.add(
            responses.POST,
            self.AJAX_URL,
            body="Invalid JSON response",
            status=200,
        )

        with pytest.raises(OpenGoKrError) as exc_info:
            client.fetch_documents("1342000", "교육부", "2025-12-27")

        assert "Failed to parse JSON" in str(exc_info.value)

    @responses.activate
    def test_fetch_documents_pagination(self, client: OpenGoKrClient) -> None:
        """Fetch all pages when documents exceed page size."""
        self._mock_xsrf_token()

        # First page
        first_page_docs = [
            {
                "INFO_SJ": f"문서 {i}",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
                "PRDCTN_INSTT_REGIST_NO": f"DCT{i:032d}",
                "INSTT_SE_CD": "C",
            }
            for i in range(10)
        ]
        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response(first_page_docs, 15),
            status=200,
        )
        # Second page
        second_page_docs = [
            {
                "INFO_SJ": f"문서 {i}",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
                "PRDCTN_INSTT_REGIST_NO": f"DCT{i:032d}",
                "INSTT_SE_CD": "C",
            }
            for i in range(10, 15)
        ]
        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response(second_page_docs, 15),
            status=200,
        )

        documents = client.fetch_documents("1342000", "교육부", "2025-12-27")

        assert len(documents) == 15
        # Verify all documents have URLs
        assert all(doc.url != "" for doc in documents)

    @responses.activate
    def test_xsrf_token_cached_across_requests(self, client: OpenGoKrClient) -> None:
        """XSRF token is acquired once and reused across requests."""
        # Only one token acquisition should happen
        self._mock_xsrf_token()

        # Two AJAX requests
        mock_docs = [
            {
                "INFO_SJ": "문서",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
                "PRDCTN_INSTT_REGIST_NO": "DCT88209A2A1A26554804C2D0F2F351816D",
                "INSTT_SE_CD": "C",
            }
        ]
        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response(mock_docs, 1),
            status=200,
        )
        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response(mock_docs, 1),
            status=200,
        )

        # First request
        client.fetch_documents("1342000", "교육부", "2025-12-27")
        # Second request (should reuse token)
        client.fetch_documents("1342000", "교육부", "2025-12-27")

        # Verify only one token acquisition call
        token_calls = [call for call in responses.calls if self.PAGE_URL in call.request.url]
        assert len(token_calls) == 1

    @responses.activate
    def test_xsrf_token_refresh_on_401(self, client: OpenGoKrClient) -> None:
        """XSRF token is refreshed on 401 error."""
        # First token acquisition
        self._mock_xsrf_token()

        # First request fails with 401
        responses.add(
            responses.POST,
            self.AJAX_URL,
            json={"error": "Unauthorized"},
            status=401,
        )

        # Second token acquisition after retry
        self._mock_xsrf_token()

        # Second request succeeds
        mock_docs = [
            {
                "INFO_SJ": "문서",
                "PRDCTN_DT": "20251227120000",
                "PROC_INSTT_NM": "교육부",
                "PRDCTN_INSTT_REGIST_NO": "DCT88209A2A1A26554804C2D0F2F351816D",
                "INSTT_SE_CD": "C",
            }
        ]
        responses.add(
            responses.POST,
            self.AJAX_URL,
            json=self._make_ajax_response(mock_docs, 1),
            status=200,
        )

        documents = client.fetch_documents("1342000", "교육부", "2025-12-27")

        assert len(documents) == 1
        # Verify token was refreshed (2 token acquisition calls)
        token_calls = [call for call in responses.calls if self.PAGE_URL in call.request.url]
        assert len(token_calls) == 2
