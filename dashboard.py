import html
from datetime import datetime

from sources.base import JobPosting


def render(postings: list[JobPosting], failed_sources: list[str]) -> str:
    # Two-pass stable sort: newest-first by date, then group NEW postings
    # first (Python's sort is stable, so within each is_new group the
    # newest-first date order from the first pass is preserved).
    ordered = sorted(postings, key=lambda p: p.posted_date or "", reverse=True)
    ordered = sorted(ordered, key=lambda p: not p.is_new)
    rows = "\n".join(_render_row(p) for p in ordered)
    warnings = "".join(
        f'<div class="warning">{html.escape(source)} 수집 실패</div>' for source in failed_sources
    )
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>채용공고 대시보드</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 2rem auto; }}
.job {{ border-bottom: 1px solid #ddd; padding: 0.75rem 0; }}
.new {{ color: #c00; font-weight: bold; }}
.warning {{ background: #fee; padding: 0.5rem; margin-bottom: 0.5rem; }}
</style>
</head>
<body>
<h1>채용공고 대시보드 <small>({generated_at} 갱신)</small></h1>
{warnings}
<p>총 {len(postings)}건</p>
{rows}
</body>
</html>"""


def _render_row(posting: JobPosting) -> str:
    badge = '<span class="new">[NEW] </span>' if posting.is_new else ""
    location = posting.location or "지역 미상"
    closing = f" · 마감: {html.escape(posting.closing_date)}" if posting.closing_date else ""
    return f"""<div class="job">
{badge}<a href="{html.escape(posting.url)}" target="_blank">{html.escape(posting.title)}</a><br>
{html.escape(posting.company)} · {html.escape(location)} · {html.escape(posting.source)}{closing}
</div>"""
