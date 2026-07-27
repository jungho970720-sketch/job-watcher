import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from sources.jobda import _parse_page, fetch

FIXTURE = Path(__file__).parent / "fixtures" / "jobda_response.json"


def test_parse_page_extracts_job_fields():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    postings = _parse_page(data)

    assert len(postings) == 2
    posting = postings[0]
    assert posting.source == "jobda"
    assert posting.external_id == "223241"
    assert posting.title == "전산보안 신입사원 채용"
    assert posting.company == "테스트 시큐리티"
    assert posting.url == "https://www.jobda.im/position/223241"
    assert posting.location is None
    assert posting.experience_years_required is None
    assert posting.posted_date == "2026-07-27"
    assert posting.closing_date is None


def test_fetch_stops_when_a_page_has_no_positions():
    empty_page = {"pages": {"page": 1, "size": 60, "totalPages": 1, "totalElements": 0}, "positions": []}
    full_page = json.loads(FIXTURE.read_text(encoding="utf-8"))

    responses = [MagicMock(json=lambda: full_page), MagicMock(json=lambda: empty_page)]
    for r in responses:
        r.raise_for_status = lambda: None

    with patch("sources.jobda.requests.get", side_effect=responses) as mock_get:
        postings = fetch(["전산"], max_pages=5)

    assert mock_get.call_count == 2
    assert len(postings) == 1  # only the "전산보안" posting matches keyword "전산"
