from sources.base import JobPosting


def test_job_posting_defaults_to_unknown_optional_fields():
    posting = JobPosting(
        source="saramin",
        external_id="123",
        title="백엔드 개발자",
        company="테스트 회사",
        url="https://example.com/123",
    )
    assert posting.location is None
    assert posting.experience_years_required is None
    assert posting.posted_date is None
    assert posting.closing_date is None
    assert posting.is_new is False
