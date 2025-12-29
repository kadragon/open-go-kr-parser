# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0001
"""API client for open.go.kr original document disclosure portal."""

import json
import re
from dataclasses import dataclass
from typing import Any

import requests


class OpenGoKrError(Exception):
    """Base exception for OpenGoKr client errors."""

    pass


@dataclass
class Document:
    """Represents a disclosed document."""

    title: str
    date: str
    url: str
    agency_name: str


class OpenGoKrClient:
    """Client for fetching documents from open.go.kr API."""

    PAGE_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do"
    PAGE_SIZE = 10

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize client with optional session.

        Args:
            session: Optional requests session for connection pooling.
        """
        self.session = session or requests.Session()
        self._setup_headers()

    def _setup_headers(self) -> None:
        """Configure default headers for requests."""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko,en;q=0.9",
            }
        )

    def _build_request_params(
        self, agency_code: str, agency_name: str, date: str, page: int = 1
    ) -> dict[str, str]:
        """Build request parameters for page request.

        Args:
            agency_code: Institution code (e.g., "1342000" for 교육부).
            agency_name: Institution name (e.g., "교육부").
            date: Target date in YYYY-MM-DD format.
            page: Page number (1-indexed).

        Returns:
            Dictionary of form parameters.
        """
        date_formatted = date.replace("-", "")
        return {
            "insttCd": agency_code,
            "insttCdNm": agency_name,
            "startDate": date_formatted,
            "endDate": date_formatted,
            "eduYn": "N",
            "viewPage": str(page),
            "rowPage": str(self.PAGE_SIZE),
            "sort": "s",
        }

    def _extract_result_from_html(self, html: str) -> dict[str, Any]:
        """Extract the embedded result JSON from page HTML.

        Args:
            html: HTML content from page response.

        Returns:
            Parsed JSON result object.

        Raises:
            OpenGoKrError: If result cannot be extracted.
        """
        # Look for: var result = {...};
        match = re.search(r"var\s+result\s*=\s*(\{.*?\});", html, re.DOTALL)
        if not match:
            raise OpenGoKrError("Could not find result data in page HTML")

        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise OpenGoKrError(f"Failed to parse result JSON: {e}") from e

    def _parse_response(self, data: dict[str, Any]) -> tuple[list[Document], int]:
        """Parse result data into Document objects.

        Args:
            data: Parsed result JSON from page.

        Returns:
            Tuple of (list of Document objects, total count).
        """
        doc_list = data.get("rtnList", [])
        total_count = data.get("rtnTotal", 0)

        if not doc_list:
            return [], 0

        documents = []
        for item in doc_list:
            # Format date from YYYYMMDDHHMMSS to YYYY-MM-DD
            raw_date = item.get("PRDCTN_DT", "")
            formatted_date = ""
            if raw_date and len(raw_date) >= 8:
                formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

            doc = Document(
                title=item.get("INFO_SJ", ""),
                date=formatted_date,
                url="",  # URL not available in this response format
                agency_name=item.get("PROC_INSTT_NM", ""),
            )
            documents.append(doc)

        return documents, int(total_count) if total_count else 0

    def fetch_documents(
        self, agency_code: str, agency_name: str, date: str
    ) -> list[Document]:
        """Fetch all documents for an agency on a specific date.

        Args:
            agency_code: Institution code (e.g., "1342000" for 교육부).
            agency_name: Institution name (e.g., "교육부").
            date: Target date in YYYY-MM-DD format.

        Returns:
            List of Document objects.

        Raises:
            OpenGoKrError: On network or parsing errors.
        """
        all_documents: list[Document] = []
        page = 1

        while True:
            try:
                response = self.session.post(
                    self.PAGE_URL,
                    data=self._build_request_params(agency_code, agency_name, date, page),
                    timeout=30,
                )
                response.raise_for_status()
                data = self._extract_result_from_html(response.text)
            except requests.exceptions.ConnectionError as e:
                raise OpenGoKrError(f"Network connection error: {e}") from e
            except requests.exceptions.Timeout as e:
                raise OpenGoKrError(f"Request timeout: {e}") from e
            except requests.exceptions.RequestException as e:
                raise OpenGoKrError(f"Request failed: {e}") from e

            documents, total_count = self._parse_response(data)
            all_documents.extend(documents)

            # Check if we need to fetch more pages
            if len(all_documents) >= total_count or not documents:
                break

            page += 1

        return all_documents
