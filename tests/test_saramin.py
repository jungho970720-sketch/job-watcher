import json
from pathlib import Path

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
