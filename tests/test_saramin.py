import json
from pathlib import Path

import pytest

from sources.base import SourceAPIError
from sources.saramin import _parse_response

FIXTURE = Path(__file__).parent / "fixtures" / "saramin_response.json"


def test_parse_response_extracts_job_fields():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    postings = _parse_response(data)

    assert len(postings) == 1
    posting = postings[0]
    assert posting.source == "saramin"
    assert posting.external_id == "45678901"
    assert posting.title == "전산보안 담당자"
    assert posting.company == "테스트 IT"
    assert posting.location == "광주"
    # experience-level is {"min": 0, "max": 2}: "min" is used (not "max"),
    # since Saramin's "max" is the top of the accepted range, not a minimum
    # requirement, so the correct semantic value here is 0.
    assert posting.experience_years_required == 0
    assert posting.posted_date == "2026-07-27"
    assert posting.closing_date == "2026-08-27"


def test_parse_response_handles_single_job_dict_not_list():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["jobs"]["job"] = data["jobs"]["job"][0]
    postings = _parse_response(data)
    assert len(postings) == 1


def test_parse_response_raises_on_invalid_key_error_payload():
    # Real response captured from the live API with an invalid access-key:
    # HTTP 200 with an error body instead of a "jobs" key. Without an explicit
    # check this parses to zero postings, so a wrong/expired key would look
    # identical to "no matching jobs today" — silently, with no warning.
    error_payload = {"code": 2, "message": "사용 불가능한 access-key 입니다. "}

    with pytest.raises(SourceAPIError):
        _parse_response(error_payload)


def test_parse_response_raises_on_daily_quota_error_payload():
    # code 4 = daily call limit (500/day) exceeded — must surface, not silently
    # return an empty dashboard.
    with pytest.raises(SourceAPIError):
        _parse_response({"code": 4, "message": "일일 허용 호출 건수를 초과하였습니다."})


def test_parse_response_returns_empty_list_for_genuine_zero_results():
    # A real "no matching jobs" response still carries the "jobs" key, so it
    # must NOT be treated as an error.
    postings = _parse_response({"jobs": {"count": 0, "start": 0, "total": "0", "job": []}})
    assert postings == []
