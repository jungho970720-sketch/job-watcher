from pathlib import Path

import pytest

from sources.base import SourceAPIError
from sources.worknet import _parse_response

FIXTURE = Path(__file__).parent / "fixtures" / "worknet_response.xml"


def test_parse_response_extracts_job_fields():
    postings = _parse_response(FIXTURE.read_text(encoding="utf-8"))

    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "worknet"
    assert posting.external_id == "W20260727001"
    assert posting.title == "전산 관제 담당자 채용"
    assert posting.company == "테스트 전산센터"
    assert posting.location == "광주광역시 북구"
    assert posting.experience_years_required == 0
    assert posting.posted_date == "2026-07-27"
    assert posting.closing_date == "2026.08.27"


def test_parse_response_raises_on_invalid_key_error_payload():
    # Real response captured from the live API with an invalid authKey: HTTP 200
    # with well-formed XML carrying <messageCd> and no <wanted> elements. Without
    # an explicit check this parses to zero postings, so a wrong/expired key
    # would look identical to "no matching jobs today" — silently, no warning.
    error_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<wantedRoot>"
        "<message>유효하지 않은 인증키 입니다.</message>"
        "<messageCd>002</messageCd>"
        "</wantedRoot>"
    )

    with pytest.raises(SourceAPIError):
        _parse_response(error_xml)


def test_parse_response_returns_empty_list_for_genuine_zero_results():
    # A real "no matching jobs" response carries <total> and no <messageCd>,
    # so it must NOT be treated as an error.
    empty_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<wantedRoot><total>0</total><startPage>1</startPage><display>100</display></wantedRoot>"
    )

    assert _parse_response(empty_xml) == []


def test_parse_career_with_years():
    from sources.worknet import _parse_career

    assert _parse_career("신입") == 0
    assert _parse_career("경력3년이상") == 3
    assert _parse_career("경력3년~5년") == 3
    assert _parse_career("경력1~3년") == 1
    assert _parse_career(None) is None
