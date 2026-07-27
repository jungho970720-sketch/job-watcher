import re
import xml.etree.ElementTree as ET

import requests

from sources.base import JobPosting, SourceAPIError

SEARCH_URL = "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do"


def fetch(job_keywords: list[str], auth_key: str) -> list[JobPosting]:
    postings: dict[str, JobPosting] = {}
    for keyword in job_keywords:
        response = requests.get(
            SEARCH_URL,
            params={
                "authKey": auth_key,
                "callTp": "L",
                "returnType": "XML",
                "keyword": keyword,
                "display": 100,
            },
            timeout=15,
        )
        response.raise_for_status()
        for posting in _parse_response(response.text):
            postings[posting.external_id] = posting
    return list(postings.values())


def _parse_response(xml_text: str) -> list[JobPosting]:
    root = ET.fromstring(xml_text)

    # An invalid/expired authKey comes back as HTTP 200 with well-formed XML
    # carrying <messageCd> and no <wanted> elements, so raise_for_status()
    # never fires. Detect it here — otherwise the source silently contributes
    # zero postings and the dashboard looks the same as a genuinely quiet day.
    # A successful response carries <total> and no <messageCd>.
    message_code = root.find("messageCd")
    if message_code is not None:
        message = root.find("message")
        raise SourceAPIError(
            f"Worknet API error (messageCd={message_code.text}): "
            f"{message.text if message is not None else ''}"
        )

    result = []
    for wanted in root.findall("wanted"):
        result.append(
            JobPosting(
                source="worknet",
                external_id=_text(wanted, "wantedAuthNo") or "",
                title=_text(wanted, "title") or "",
                company=_text(wanted, "company") or "",
                url=_text(wanted, "wantedInfoUrl") or "",
                location=_text(wanted, "region"),
                experience_years_required=_parse_career(_text(wanted, "career")),
                posted_date=_normalize_date(_text(wanted, "regDt")),
                closing_date=_text(wanted, "closeDt"),
            )
        )
    return result


def _text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    return child.text if child is not None else None


def _normalize_date(date_text: str | None) -> str | None:
    # Worknet dates come as "2026.07.27"; normalize to "YYYY-MM-DD" so dates
    # sort/compare consistently across sources.
    if date_text is None:
        return None
    return date_text.replace(".", "-")


def _parse_career(career_text: str | None) -> int | None:
    if career_text is None:
        return None
    if "신입" in career_text:
        return 0
    match = re.search(r"\d+", career_text)
    return int(match.group()) if match else None
