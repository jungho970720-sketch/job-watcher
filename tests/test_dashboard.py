from dashboard import render
from sources.base import JobPosting


def test_render_includes_posting_title_and_link():
    posting = JobPosting(
        source="saramin", external_id="1", title="전산 담당자",
        company="회사", url="https://example.com/1", location="광주",
    )
    html = render([posting], failed_sources=[])
    assert "전산 담당자" in html
    assert 'href="https://example.com/1"' in html
    assert "광주" in html


def test_render_escapes_html_in_title():
    posting = JobPosting(
        source="saramin", external_id="1", title="<script>alert(1)</script>",
        company="회사", url="https://example.com/1",
    )
    html = render([posting], failed_sources=[])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_shows_new_badge_only_for_new_postings():
    new_posting = JobPosting(
        source="saramin", external_id="1", title="새 공고",
        company="회사", url="https://example.com/1", is_new=True,
    )
    old_posting = JobPosting(
        source="saramin", external_id="2", title="예전 공고",
        company="회사", url="https://example.com/2", is_new=False,
    )
    html = render([new_posting, old_posting], failed_sources=[])
    assert html.count("[NEW]") == 1


def test_render_shows_failure_warning():
    html = render([], failed_sources=["jobkorea"])
    assert "jobkorea" in html
    assert "수집 실패" in html
