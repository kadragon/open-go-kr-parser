# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0001
"""API client for open.go.kr original document disclosure portal."""

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

    API_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.ajax"
    PAGE_SIZE = 10

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize client with optional session.

        Args:
            session: Optional requests session for connection pooling.
        """
        self.session = session or requests.Session()
        self._setup_headers()

    def _setup_headers(self) -> None:
        """Configure default headers for API requests."""
        self.session.headers.update(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "ko,en;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    def _build_request_body(
        self, agency_code: str, date: str, page: int = 1
    ) -> dict[str, str]:
        """Build request body for API call.

        Args:
            agency_code: Institution code (e.g., "1342000" for 교육부).
            date: Target date in YYYYMMDD format.
            page: Page number (1-indexed).

        Returns:
            Dictionary of form parameters.
        """
        date_formatted = date.replace("-", "")
        return {
            "kwd": "",
            "searchInsttCdNmPop": "",
            "preKwds": "",
            "reSrchFlag": "off",
            "othbcSeCd": "",
            "insttSeCd": "",
            "eduYn": "N",
            "startDate": date_formatted,
            "endDate": date_formatted,
            "insttCdNm": "",
            "insttCd": agency_code,
            "searchMainYn": "",
            "viewPage": str(page),
            "rowPage": str(self.PAGE_SIZE),
            "sort": "s",
            "url": "/othicInfo/infoList/orginlInfoList.ajax",
            "callBackFn": "searchFn_callBack",
        }

    def _parse_response(self, data: dict[str, Any]) -> list[Document]:
        """Parse API response into Document objects.

        Args:
            data: JSON response from API.

        Returns:
            List of Document objects.

        Raises:
            OpenGoKrError: If response format is invalid.
        """
        if "list" not in data:
            raise OpenGoKrError("Invalid response format: missing 'list' field")

        documents = []
        for item in data["list"]:
            try:
                doc = Document(
                    title=item["orginlNm"],
                    date=item["othbcDt"],
                    url=item["orginlUrl"],
                    agency_name=item["insttNm"],
                )
                documents.append(doc)
            except KeyError as e:
                raise OpenGoKrError(f"Missing required field in response: {e}") from e

        return documents

    def fetch_documents(self, agency_code: str, date: str) -> list[Document]:
        """Fetch all documents for an agency on a specific date.

        Args:
            agency_code: Institution code (e.g., "1342000" for 교육부).
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
                    self.API_URL,
                    data=self._build_request_body(agency_code, date, page),
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.ConnectionError as e:
                raise OpenGoKrError(f"Network connection error: {e}") from e
            except requests.exceptions.Timeout as e:
                raise OpenGoKrError(f"Request timeout: {e}") from e
            except requests.exceptions.RequestException as e:
                raise OpenGoKrError(f"Request failed: {e}") from e
            except ValueError as e:
                raise OpenGoKrError(f"Failed to parse JSON response: {e}") from e

            documents = self._parse_response(data)
            all_documents.extend(documents)

            # Check if we need to fetch more pages
            total_count = data.get("totalCnt", 0)
            if len(all_documents) >= total_count or not documents:
                break

            page += 1

        return all_documents
