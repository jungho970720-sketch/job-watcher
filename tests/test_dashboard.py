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


def test_render_orders_new_postings_first_then_newest_date_first():
    old_not_new = JobPosting(
        source="saramin", external_id="1", title="옛날 공고",
        company="회사", url="https://example.com/1", is_new=False, posted_date="2026-01-01",
    )
    new_older = JobPosting(
        source="saramin", external_id="2", title="새 공고 (오래됨)",
        company="회사", url="https://example.com/2", is_new=True, posted_date="2026-07-01",
    )
    new_newest = JobPosting(
        source="saramin", external_id="3", title="새 공고 (최신)",
        company="회사", url="https://example.com/3", is_new=True, posted_date="2026-07-27",
    )
    html = render([old_not_new, new_older, new_newest], failed_sources=[])

    # Both NEW postings must appear before the non-NEW one, and within the
    # NEW group the newest posted_date must come first.
    pos_newest = html.index("새 공고 (최신)")
    pos_older = html.index("새 공고 (오래됨)")
    pos_old_not_new = html.index("옛날 공고")
    assert pos_newest < pos_older < pos_old_not_new


def test_render_shows_closing_date_when_set():
    posting = JobPosting(
        source="saramin", external_id="1", title="전산 담당자",
        company="회사", url="https://example.com/1", closing_date="2026-08-27",
    )
    html = render([posting], failed_sources=[])
    assert "마감: 2026-08-27" in html


def test_render_omits_closing_date_when_none():
    posting = JobPosting(
        source="saramin", external_id="1", title="전산 담당자",
        company="회사", url="https://example.com/1", closing_date=None,
    )
    html = render([posting], failed_sources=[])
    assert "마감" not in html
