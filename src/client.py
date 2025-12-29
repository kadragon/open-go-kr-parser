# Trace: spec_id=SPEC-api-client-001 task_id=TASK-0001
# Trace: spec_id=SPEC-code-quality-001 task_id=TASK-0008
"""API client for open.go.kr original document disclosure portal."""

import json
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
    AJAX_URL = "https://www.open.go.kr/othicInfo/infoList/orginlInfoList.ajax"
    DETAIL_URL_BASE = "https://www.open.go.kr/othicInfo/infoList/infoListDetl.do"
    PAGE_SIZE = 10
    REQUEST_TIMEOUT = 30
    _XSRF_TOKEN_PAYLOAD = {"rowPage": "1", "viewPage": "1"}

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize client with optional session.

        Args:
            session: Optional requests session for connection pooling.
        """
        self.session = session or requests.Session()
        self._xsrf_token: str | None = None
        self._setup_headers()

    def _setup_headers(self) -> None:
        """Configure default headers for AJAX requests."""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "ko,en;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    def _acquire_xsrf_token(self) -> str:
        """Acquire XSRF token by requesting the page URL.

        Returns:
            XSRF token string.

        Raises:
            OpenGoKrError: If token cannot be obtained.
        """
        try:
            # Make a minimal request to get session cookies
            response = self.session.post(
                self.PAGE_URL,
                data=self._XSRF_TOKEN_PAYLOAD,
                timeout=self.REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            # Extract XSRF token from cookies
            token = self.session.cookies.get("XSRF-TOKEN")
            if not token:
                raise OpenGoKrError("XSRF-TOKEN not found in response cookies")

            return token

        except requests.exceptions.RequestException as e:
            raise OpenGoKrError(f"Failed to acquire XSRF token: {e}") from e

    def _ensure_xsrf_token(self) -> None:
        """Ensure we have a valid XSRF token."""
        if not self._xsrf_token:
            self._xsrf_token = self._acquire_xsrf_token()
            self.session.headers["x-xsrf-token"] = self._xsrf_token

    def _build_request_params(
        self,
        agency_code: str,
        agency_name: str,
        start_date: str,
        end_date: str,
        page: int = 1,
    ) -> dict[str, str]:
        """Build request parameters for page request.

        Args:
            agency_code: Institution code (e.g., "1342000" for 교육부).
            agency_name: Institution name (e.g., "교육부").
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            page: Page number (1-indexed).

        Returns:
            Dictionary of form parameters.
        """
        start_formatted = start_date.replace("-", "")
        end_formatted = end_date.replace("-", "")
        return {
            "insttCd": agency_code,
            "insttCdNm": agency_name,
            "startDate": start_formatted,
            "endDate": end_formatted,
            "eduYn": "N",
            "viewPage": str(page),
            "rowPage": str(self.PAGE_SIZE),
            "sort": "s",
        }

    def _build_detail_url(
        self, reg_no: str, prod_dt: str, inst_se_cd: str
    ) -> str:
        """Build document detail page URL.

        Args:
            reg_no: Document registration number (PRDCTN_INSTT_REGIST_NO).
            prod_dt: Production datetime (PRDCTN_DT).
            inst_se_cd: Institution type code (INSTT_SE_CD).

        Returns:
            Document detail URL, or empty string if required fields missing.
        """
        if not (reg_no and prod_dt and inst_se_cd):
            return ""

        return (
            f"{self.DETAIL_URL_BASE}"
            f"?prdnNstRgstNo={reg_no}&prdnDt={prod_dt}&nstSeCd={inst_se_cd}"
        )

    def _parse_response(self, data: dict[str, Any]) -> tuple[list[Document], int]:
        """Parse result data into Document objects.

        Args:
            data: Parsed result JSON from AJAX response.

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

            # Build document detail URL
            url = self._build_detail_url(
                reg_no=item.get("PRDCTN_INSTT_REGIST_NO", ""),
                prod_dt=item.get("PRDCTN_DT", ""),
                inst_se_cd=item.get("INSTT_SE_CD", ""),
            )

            doc = Document(
                title=item.get("INFO_SJ", ""),
                date=formatted_date,
                url=url,
                agency_name=item.get("PROC_INSTT_NM", ""),
            )
            documents.append(doc)

        return documents, int(total_count or 0)

    def fetch_documents(
        self,
        agency_code: str,
        agency_name: str,
        start_date: str,
        end_date: str | None = None,
    ) -> list[Document]:
        """Fetch all documents for an agency within a date range.

        Args:
            agency_code: Institution code (e.g., "1342000" for 교육부).
            agency_name: Institution name (e.g., "교육부").
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format. If None, uses start_date.

        Returns:
            List of Document objects.

        Raises:
            OpenGoKrError: On network or parsing errors.
        """
        if end_date is None:
            end_date = start_date

        # Ensure we have XSRF token before making requests
        self._ensure_xsrf_token()

        all_documents: list[Document] = []
        page = 1
        max_retries = 1

        while True:
            for attempt in range(max_retries + 1):
                try:
                    params = self._build_request_params(
                        agency_code, agency_name, start_date, end_date, page
                    )
                    response = self.session.post(
                        self.AJAX_URL,
                        data=params,
                        timeout=self.REQUEST_TIMEOUT,
                    )
                    response.raise_for_status()

                    # Parse JSON response directly
                    result = response.json()
                    # Extract from nested structure: result.result or just result
                    data = result.get("result", result)

                    break  # Success, exit retry loop

                except (json.JSONDecodeError, ValueError) as e:
                    raise OpenGoKrError(f"Failed to parse JSON response: {e}") from e
                except requests.exceptions.HTTPError as e:
                    # On auth errors, try refreshing token once
                    if e.response.status_code in (401, 403) and attempt < max_retries:
                        self._xsrf_token = None
                        self._ensure_xsrf_token()
                        continue
                    raise OpenGoKrError(f"HTTP error: {e}") from e
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
