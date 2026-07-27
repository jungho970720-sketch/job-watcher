import re
import time

from playwright.sync_api import sync_playwright

from sources.base import JobPosting

BASE_URL = "https://www.jobkorea.co.kr"

_EXTRACT_CARDS_JS = """
() => {
  const anchors = Array.from(document.querySelectorAll('a[href*="/Recruit/GI_Read/"]'));
  const seen = new Set();
  const results = [];
  for (const a of anchors) {
    const path = a.pathname;
    if (seen.has(path)) continue;
    seen.add(path);
    let card = a;
    let level = 0;
    while (card.parentElement) {
      const next = card.parentElement;
      const distinct = new Set(
        Array.from(next.querySelectorAll('a[href*="/Recruit/GI_Read/"]')).map(x => x.pathname)
      );
      if (distinct.size > 1) break;
      card = next;
      level++;
      if (level > 10) break;
    }
    results.push({ path, text: card.innerText });
  }
  return results;
}
"""


def fetch(job_keywords: list[str]) -> list[JobPosting]:
    postings: dict[str, JobPosting] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for keyword in job_keywords:
            page.goto(f"{BASE_URL}/Search/?stext={keyword}&tabType=recruit", timeout=30000)
            page.wait_for_selector('a[href*="/Recruit/GI_Read/"]', timeout=15000)
            for card in page.evaluate(_EXTRACT_CARDS_JS):
                posting = _parse_card(card["path"], card["text"])
                if posting is not None:
                    postings[posting.external_id] = posting
            time.sleep(2)
        browser.close()
    return list(postings.values())


def _parse_card(path: str, card_text: str) -> JobPosting | None:
    lines = [line.strip() for line in card_text.split("\n") if line.strip()]
    if "스크랩" not in lines:
        return None
    scrap_idx = lines.index("스크랩")
    if scrap_idx + 3 >= len(lines):
        return None

    external_id = path.rstrip("/").rsplit("/", 1)[-1]
    return JobPosting(
        source="jobkorea",
        external_id=external_id,
        title=lines[scrap_idx + 1],
        company=lines[scrap_idx + 2],
        url=BASE_URL + path,
        location=lines[scrap_idx + 3],
        experience_years_required=_parse_experience(lines),
        posted_date=_find_date(lines, "등록"),
        closing_date=_find_date(lines, "마감"),
    )


def _parse_experience(lines: list[str]) -> int | None:
    for line in lines:
        if "경력무관" in line or line == "신입" or "신입·경력" in line:
            return 0
        match = re.search(r"경력\s*(\d+)년", line)
        if match:
            return int(match.group(1))
    return None


def _find_date(lines: list[str], suffix: str) -> str | None:
    for line in lines:
        match = re.match(r"(\d{2}/\d{2})\([^)]+\)\s*" + suffix, line)
        if match:
            return match.group(1)
    return None
