from filter import matches
from sources.base import JobPosting

FILTERS = {
    "job_keywords": ["전산", "IT"],
    "regions": ["광주"],
    "experience_max_years": 2,
    "exclude_keywords": ["인턴"],
}


def _posting(**overrides) -> JobPosting:
    defaults = dict(
        source="test",
        external_id="1",
        title="전산 담당자 채용",
        company="회사",
        url="https://example.com",
        location="광주 북구",
        experience_years_required=1,
    )
    defaults.update(overrides)
    return JobPosting(**defaults)


def test_matches_when_all_conditions_satisfied():
    assert matches(_posting(), FILTERS) is True


def test_rejects_when_title_missing_job_keyword():
    assert matches(_posting(title="마케팅 담당자 채용"), FILTERS) is False


def test_rejects_when_exclude_keyword_present():
    assert matches(_posting(title="전산 인턴 채용"), FILTERS) is False


def test_rejects_when_region_does_not_match():
    assert matches(_posting(location="서울 강남구"), FILTERS) is False


def test_passes_when_location_unknown():
    assert matches(_posting(location=None), FILTERS) is True


def test_rejects_when_experience_exceeds_max():
    assert matches(_posting(experience_years_required=5), FILTERS) is False


def test_passes_when_experience_unknown():
    assert matches(_posting(experience_years_required=None), FILTERS) is True


def test_empty_job_keywords_matches_everything():
    filters = {**FILTERS, "job_keywords": []}
    assert matches(_posting(title="아무 공고"), filters) is True
