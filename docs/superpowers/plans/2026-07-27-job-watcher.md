# Job Watcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python tool that collects job postings from 사람인, 워크넷, 잡다, 잡코리아, filters them by user-defined conditions (job keywords, region, experience, exclusions), and renders them into a single local `dashboard.html` file, run automatically every day via Windows Task Scheduler.

**Architecture:** Four independent `sources/*.py` modules each expose `fetch(job_keywords: list[str]) -> list[JobPosting]`, normalizing site-specific responses into a shared `JobPosting` dataclass. `main.py` calls each source (catching per-source failures), passes the combined list through `filter.py` (keyword/region/experience matching against the normalized fields — not each site's own API filter params, since fields available differ per site), diffs against `state.json` to flag new postings, and renders everything with `dashboard.py` into `dashboard.html`.

**Tech Stack:** Python 3.12, `requests` (Saramin/Worknet/JobDA — all three have real, verified HTTP JSON/XML endpoints), `playwright` (JobKorea only — its search results are rendered client-side by a Next.js SPA; confirmed by inspecting the live page, plain HTTP requests return no listing data), stdlib `xml.etree.ElementTree` (Worknet XML parsing), `pytest` for tests.

## Global Constraints

- Python 3.12+ must be installed and on PATH before any task runs code (verified during Task 1 — this machine had no Python installed as of plan-writing time).
- No API keys committed to git. Saramin `access-key` and Worknet `authKey` live in `config/secrets.json`, which is gitignored; `config/secrets.json.example` (committed) documents the expected shape.
- `config/filters.json` is committed with sensible defaults and is meant to be hand-edited by the user to add/remove conditions — no separate editing UI/CLI.
- `state.json` and `dashboard.html` are runtime-generated output and gitignored.
- Every source module separates **fetching** (network/browser I/O) from **parsing** (pure function turning raw response text into `JobPosting` objects), so parsing logic is unit-testable with fixture data and never makes real network calls in tests.
- Every *optional* field on `JobPosting` (`location`, `experience_years_required`, `posted_date`, `closing_date` — the ones typed `X | None = None`) that the fetch/parse layer cannot determine is `None`, never an empty string — `filter.py` treats `None` as "unknown, don't reject." This does not apply to the required `str` fields (`title`, `company`, `url`, `external_id`); those have no `None` variant in the dataclass, so a missing value falls back to `""` (in practice, none of the four sources omit these fields).

---

### Task 1: Project scaffolding, Python setup, and the `JobPosting` model

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `config/filters.json`
- Create: `config/secrets.json.example`
- Create: `sources/__init__.py`
- Create: `sources/base.py`
- Test: `tests/test_base.py`

**Interfaces:**
- Produces: `JobPosting` dataclass (used by every later task) with fields:
  `source: str`, `external_id: str`, `title: str`, `company: str`, `url: str`,
  `location: str | None = None`, `experience_years_required: int | None = None`,
  `posted_date: str | None = None`, `closing_date: str | None = None`, `is_new: bool = False`.

- [ ] **Step 1: Install Python 3.12+ if not already present**

Run in PowerShell to check:
```powershell
python --version
```
If this fails (as it did during planning — only the Windows Store stub existed), download and run the official installer from https://www.python.org/downloads/ (check "Add python.exe to PATH" during install). After installing, re-run `python --version` in a new terminal and confirm it prints a version.

- [ ] **Step 2: Create the project skeleton and `.gitignore`**

`C:\Users\jungho\job-watcher\.gitignore`:
```
config/secrets.json
state.json
dashboard.html
__pycache__/
*.pyc
.pytest_cache/
```

`C:\Users\jungho\job-watcher\requirements.txt`:
```
requests==2.32.3
playwright==1.47.0
pytest==8.3.3
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

- [ ] **Step 4: Write default filter config and secrets example**

`config/filters.json`:
```json
{
  "job_keywords": ["전산", "IT", "전산보안", "정보보안"],
  "regions": ["광주"],
  "experience_max_years": 2,
  "exclude_keywords": ["인턴", "파견"]
}
```

`config/secrets.json.example`:
```json
{
  "saramin_access_key": "YOUR_SARAMIN_ACCESS_KEY",
  "worknet_auth_key": "YOUR_WORKNET_AUTH_KEY"
}
```

- [ ] **Step 5: Write the failing test for `JobPosting`**

`tests/test_base.py`:
```python
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
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.base'` (or `ImportError`)

- [ ] **Step 7: Implement `sources/base.py`**

```python
from dataclasses import dataclass


@dataclass
class JobPosting:
    source: str
    external_id: str
    title: str
    company: str
    url: str
    location: str | None = None
    experience_years_required: int | None = None
    posted_date: str | None = None
    closing_date: str | None = None
    is_new: bool = False
```

`sources/__init__.py`: empty file.

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_base.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add requirements.txt .gitignore config/filters.json config/secrets.json.example sources/__init__.py sources/base.py tests/test_base.py
git commit -m "Add project scaffolding and JobPosting model"
```

---

### Task 2: Saramin source module

**Files:**
- Create: `sources/saramin.py`
- Test: `tests/test_saramin.py`
- Test fixture: `tests/fixtures/saramin_response.json`

**Interfaces:**
- Consumes: `JobPosting` from `sources/base.py` (Task 1)
- Produces: `fetch(job_keywords: list[str], access_key: str) -> list[JobPosting]`, used by `main.py` (Task 9)

Real, verified endpoint: `GET https://oapi.saramin.co.kr/job-search` with query params `access-key`, `keywords`, `count` (max 110). JSON response shape (confirmed from Saramin's own API docs):
```json
{"jobs": {"job": [{"id": "...", "url": "...", "company": {"detail": {"name": "..."}},
  "position": {"title": "...", "location": {"name": "..."}, "experience-level": {"min": 0, "max": 2}},
  "posting-date": "...", "expiration-date": "..."}]}}
```

- [ ] **Step 1: Write the fixture**

`tests/fixtures/saramin_response.json`:
```json
{
  "jobs": {
    "count": 1,
    "start": 0,
    "total": "1",
    "job": [
      {
        "id": "45678901",
        "url": "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=45678901",
        "company": {"detail": {"href": "https://example.com", "name": "테스트 IT"}},
        "position": {
          "title": "전산보안 담당자",
          "location": {"code": "112", "name": "광주"},
          "experience-level": {"code": 2, "min": 0, "max": 2, "name": "신입/경력2년↑"}
        },
        "posting-date": "2026-07-27 09:00:00",
        "expiration-date": "2026-08-27"
      }
    ]
  }
}
```

- [ ] **Step 2: Write the failing test**

`tests/test_saramin.py`:
```python
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
    assert posting.experience_years_required == 2
    assert posting.posted_date == "2026-07-27 09:00:00"
    assert posting.closing_date == "2026-08-27"


def test_parse_response_handles_single_job_dict_not_list():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["jobs"]["job"] = data["jobs"]["job"][0]
    postings = _parse_response(data)
    assert len(postings) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_saramin.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.saramin'`

- [ ] **Step 4: Implement `sources/saramin.py`**

```python
import requests

from sources.base import JobPosting

SEARCH_URL = "https://oapi.saramin.co.kr/job-search"


def fetch(job_keywords: list[str], access_key: str) -> list[JobPosting]:
    postings: dict[str, JobPosting] = {}
    for keyword in job_keywords:
        response = requests.get(
            SEARCH_URL,
            params={"access-key": access_key, "keywords": keyword, "count": 110},
            timeout=15,
        )
        response.raise_for_status()
        for posting in _parse_response(response.json()):
            postings[posting.external_id] = posting
    return list(postings.values())


def _parse_response(data: dict) -> list[JobPosting]:
    jobs = data.get("jobs", {}).get("job", [])
    if isinstance(jobs, dict):
        jobs = [jobs]

    result = []
    for job in jobs:
        position = job.get("position", {})
        location = position.get("location", {})
        experience = position.get("experience-level", {})
        result.append(
            JobPosting(
                source="saramin",
                external_id=str(job.get("id", "")),
                title=position.get("title", ""),
                company=job.get("company", {}).get("detail", {}).get("name", ""),
                url=job.get("url", ""),
                location=location.get("name"),
                experience_years_required=_to_int(experience.get("max")),
                posted_date=job.get("posting-date"),
                closing_date=job.get("expiration-date"),
            )
        )
    return result


def _to_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_saramin.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sources/saramin.py tests/test_saramin.py tests/fixtures/saramin_response.json
git commit -m "Add Saramin source module"
```

---

### Task 3: Worknet source module

**Files:**
- Create: `sources/worknet.py`
- Test: `tests/test_worknet.py`
- Test fixture: `tests/fixtures/worknet_response.xml`

**Interfaces:**
- Consumes: `JobPosting` from `sources/base.py` (Task 1)
- Produces: `fetch(job_keywords: list[str], auth_key: str) -> list[JobPosting]`, used by `main.py` (Task 9)

Real, verified endpoint: `GET http://openapi.work.go.kr/opi/opi/opia/wantedApi.do` with query params `authKey`, `callTp=L`, `returnType=XML`, `keyword`, `display` (max 100). XML response shape (confirmed from Worknet's own API docs):
```xml
<wantedRoot><total>1</total><wanted>
  <wantedAuthNo>...</wantedAuthNo><company>...</company><title>...</title>
  <region>...</region><career>...</career><regDt>...</regDt><closeDt>...</closeDt>
  <wantedInfoUrl>...</wantedInfoUrl>
</wanted></wantedRoot>
```

- [ ] **Step 1: Write the fixture**

`tests/fixtures/worknet_response.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<wantedRoot>
  <total>1</total>
  <startPage>1</startPage>
  <display>10</display>
  <wanted>
    <wantedAuthNo>W20260727001</wantedAuthNo>
    <company>테스트 전산센터</company>
    <title>전산 관제 담당자 채용</title>
    <sal>회사내규에 따름</sal>
    <region>광주광역시 북구</region>
    <career>신입</career>
    <regDt>2026.07.27</regDt>
    <closeDt>2026.08.27</closeDt>
    <wantedInfoUrl>https://www.work24.go.kr/wk/a/b/1200/wantedView.do?wantedAuthNo=W20260727001</wantedInfoUrl>
  </wanted>
</wantedRoot>
```

- [ ] **Step 2: Write the failing test**

`tests/test_worknet.py`:
```python
from pathlib import Path

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
    assert posting.posted_date == "2026.07.27"
    assert posting.closing_date == "2026.08.27"


def test_parse_career_with_years():
    from sources.worknet import _parse_career

    assert _parse_career("신입") == 0
    assert _parse_career("경력3년이상") == 3
    assert _parse_career(None) is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_worknet.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.worknet'`

- [ ] **Step 4: Implement `sources/worknet.py`**

```python
import xml.etree.ElementTree as ET

import requests

from sources.base import JobPosting

SEARCH_URL = "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do"


def fetch(job_keywords: list[str], auth_key: str) -> list[JobPosting]:
    postings: dict[str, JobPosting] = {}
    for keyword in job_keywords:
        response = requests.get(
            SEARCH_URL,
            params={
                "authKey": auth_key,
                "callTp": "L",
                "returnType": "XML",
                "keyword": keyword,
                "display": 100,
            },
            timeout=15,
        )
        response.raise_for_status()
        for posting in _parse_response(response.text):
            postings[posting.external_id] = posting
    return list(postings.values())


def _parse_response(xml_text: str) -> list[JobPosting]:
    root = ET.fromstring(xml_text)
    result = []
    for wanted in root.findall("wanted"):
        result.append(
            JobPosting(
                source="worknet",
                external_id=_text(wanted, "wantedAuthNo") or "",
                title=_text(wanted, "title") or "",
                company=_text(wanted, "company") or "",
                url=_text(wanted, "wantedInfoUrl") or "",
                location=_text(wanted, "region"),
                experience_years_required=_parse_career(_text(wanted, "career")),
                posted_date=_text(wanted, "regDt"),
                closing_date=_text(wanted, "closeDt"),
            )
        )
    return result


def _text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    return child.text if child is not None else None


def _parse_career(career_text: str | None) -> int | None:
    if career_text is None:
        return None
    if "신입" in career_text:
        return 0
    digits = "".join(ch for ch in career_text if ch.isdigit())
    return int(digits) if digits else None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_worknet.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sources/worknet.py tests/test_worknet.py tests/fixtures/worknet_response.xml
git commit -m "Add Worknet source module"
```

---

### Task 4: JobDA source module

**Files:**
- Create: `sources/jobda.py`
- Test: `tests/test_jobda.py`
- Test fixture: `tests/fixtures/jobda_response.json`

**Interfaces:**
- Consumes: `JobPosting` from `sources/base.py` (Task 1)
- Produces: `fetch(job_keywords: list[str], max_pages: int = 5) -> list[JobPosting]`, used by `main.py` (Task 9)

Real, verified endpoint (no auth required — confirmed by direct request during planning): `GET https://api.jobda.im/position?page=0&size=60&jobTitles=&recruitments=&locations=&matchingYn=false&orderType=LATEST`. `orderType=LATEST` sorts newest-first (confirmed; `RECENT`/`NEWEST` are rejected with `B001 Invalid Input Value`). Response JSON:
```json
{"pages": {"page": 0, "size": 60, "totalPages": 104, "totalElements": 6235},
 "positions": [{"positionSn": 223241, "positionName": "...", "companyName": "...",
   "createdDateTime": "...", "closingDateTime": null}]}
```
There is no keyword search parameter and no human-readable location field, so this module fetches the most recent `max_pages` pages and filters by `job_keywords` matching against `positionName` only; region/experience are left `None` (unknown) for JobDA postings, consistent with the spec's "unknown → pass" rule applied later in `filter.py`.

- [ ] **Step 1: Write the fixture**

`tests/fixtures/jobda_response.json`:
```json
{
  "pages": {"page": 0, "size": 2, "totalPages": 3000, "totalElements": 6000},
  "positions": [
    {
      "positionSn": 223241,
      "positionName": "전산보안 신입사원 채용",
      "companyName": "테스트 시큐리티",
      "createdDateTime": "2026-07-27T16:30:28",
      "closingDateTime": null
    },
    {
      "positionSn": 223100,
      "positionName": "마케팅 인턴 채용",
      "companyName": "테스트 마케팅",
      "createdDateTime": "2026-07-27T15:00:00",
      "closingDateTime": "2026-08-10T17:00:00"
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

`tests/test_jobda.py`:
```python
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
    assert posting.posted_date == "2026-07-27T16:30:28"
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_jobda.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.jobda'`

- [ ] **Step 4: Implement `sources/jobda.py`**

```python
import requests

from sources.base import JobPosting

POSITION_URL = "https://api.jobda.im/position"


def fetch(job_keywords: list[str], max_pages: int = 5) -> list[JobPosting]:
    all_postings: dict[str, JobPosting] = {}
    for page in range(max_pages):
        response = requests.get(
            POSITION_URL,
            params={
                "page": page,
                "size": 60,
                "jobTitles": "",
                "recruitments": "",
                "locations": "",
                "matchingYn": "false",
                "orderType": "LATEST",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        page_postings = _parse_page(data)
        if not page_postings:
            break
        for posting in page_postings:
            all_postings[posting.external_id] = posting

    if not job_keywords:
        return list(all_postings.values())
    return [
        posting
        for posting in all_postings.values()
        if any(keyword in posting.title for keyword in job_keywords)
    ]


def _parse_page(data: dict) -> list[JobPosting]:
    result = []
    for position in data.get("positions", []):
        position_sn = position.get("positionSn")
        result.append(
            JobPosting(
                source="jobda",
                external_id=str(position_sn),
                title=position.get("positionName", ""),
                company=position.get("companyName", ""),
                url=f"https://www.jobda.im/position/{position_sn}",
                location=None,
                experience_years_required=None,
                posted_date=position.get("createdDateTime"),
                closing_date=position.get("closingDateTime"),
            )
        )
    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_jobda.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sources/jobda.py tests/test_jobda.py tests/fixtures/jobda_response.json
git commit -m "Add JobDA source module"
```

---

### Task 5: JobKorea source module (Playwright)

**Files:**
- Create: `sources/jobkorea.py`
- Test: `tests/test_jobkorea.py`

**Interfaces:**
- Consumes: `JobPosting` from `sources/base.py` (Task 1)
- Produces: `fetch(job_keywords: list[str]) -> list[JobPosting]`, used by `main.py` (Task 9)

JobKorea's search page (`https://www.jobkorea.co.kr/Search/?stext=<keyword>&tabType=recruit`) is a client-rendered Next.js SPA — confirmed during planning that a plain HTTP GET returns no job data (0 matches for the listing link pattern in the raw HTML), while the rendered DOM does contain `a[href*="/Recruit/GI_Read/"]` anchors. Each job card's `innerText`, captured directly from the live site during planning, reliably follows this line structure after the literal line `"스크랩"`:
```
스크랩
<title>
<company>
<location>
<job tags, comma-separated>
[optional: 연봉 ... line]
<application method, e.g. "즉시 지원">
<experience, e.g. "경력2년↑" / "경력무관" / "신입" / "신입·경력">
•
[optional benefits line]
MM/DD(요일) 등록
•
MM/DD(요일) 마감
```
The parsing function below is written against this verified real structure. Because site markup can still drift over time, parsing is a pure function (`_parse_card`) fed by plain strings, independent of Playwright, so tests never depend on network/browser access.

- [ ] **Step 1: Write the failing test**

`tests/test_jobkorea.py`:
```python
from sources.jobkorea import _parse_card

REAL_CARD_TEXT = """신입 지원 가능
스크랩
전산관리 신입사원 채용
㈜엘에스티
전남광주 서구
물류·운송·배송, R&D·연구원
즉시 지원
신입
07/24(금) 등록
•
08/23(일) 마감"""


def test_parse_card_extracts_fields_from_real_card_text():
    posting = _parse_card("/Recruit/GI_Read/49646333", REAL_CARD_TEXT)

    assert posting is not None
    assert posting.source == "jobkorea"
    assert posting.external_id == "49646333"
    assert posting.title == "전산관리 신입사원 채용"
    assert posting.company == "㈜엘에스티"
    assert posting.location == "전남광주 서구"
    assert posting.url == "https://www.jobkorea.co.kr/Recruit/GI_Read/49646333"
    assert posting.experience_years_required == 0
    assert posting.posted_date == "07/24"
    assert posting.closing_date == "08/23"


def test_parse_card_reads_numeric_experience():
    text = "스크랩\n제목\n회사\n서울 강남구\n태그\n즉시 지원\n경력2년↑\n07/01(수) 등록\n•\n08/01(토) 마감"
    posting = _parse_card("/Recruit/GI_Read/1", text)
    assert posting.experience_years_required == 2


def test_parse_card_returns_none_when_no_scrap_marker():
    assert _parse_card("/Recruit/GI_Read/1", "이상한 텍스트만 있음") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_jobkorea.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.jobkorea'`

- [ ] **Step 3: Implement `sources/jobkorea.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_jobkorea.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sources/jobkorea.py tests/test_jobkorea.py
git commit -m "Add JobKorea source module (Playwright-rendered scraping)"
```

---

### Task 6: Filter module

**Files:**
- Create: `filter.py`
- Test: `tests/test_filter.py`

**Interfaces:**
- Consumes: `JobPosting` from `sources/base.py` (Task 1)
- Produces: `matches(posting: JobPosting, filters: dict) -> bool`, used by `main.py` (Task 9)

- [ ] **Step 1: Write the failing tests**

`tests/test_filter.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_filter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'filter'`

- [ ] **Step 3: Implement `filter.py`**

```python
from sources.base import JobPosting


def matches(posting: JobPosting, filters: dict) -> bool:
    job_keywords = filters.get("job_keywords", [])
    exclude_keywords = filters.get("exclude_keywords", [])
    regions = filters.get("regions", [])
    experience_max_years = filters.get("experience_max_years")

    if job_keywords and not _any_in(posting.title, job_keywords):
        return False
    if exclude_keywords and _any_in(posting.title, exclude_keywords):
        return False
    if not _matches_region(posting.location, regions):
        return False
    if not _matches_experience(posting.experience_years_required, experience_max_years):
        return False
    return True


def _any_in(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _matches_region(location: str | None, regions: list[str]) -> bool:
    if not regions or location is None:
        return True
    return any(region in location for region in regions)


def _matches_experience(years: int | None, max_years) -> bool:
    if years is None or max_years is None:
        return True
    return years <= max_years
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_filter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add filter.py tests/test_filter.py
git commit -m "Add filter module"
```

---

### Task 7: State module (new-posting detection)

**Files:**
- Create: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `JobPosting` from `sources/base.py` (Task 1)
- Produces: `load_seen_ids(path: Path) -> set[str]`, `mark_new(postings: list[JobPosting], seen_ids: set[str]) -> list[JobPosting]`, `save_seen_ids(path: Path, postings: list[JobPosting]) -> None` — all used by `main.py` (Task 9)

- [ ] **Step 1: Write the failing tests**

`tests/test_state.py`:
```python
import json
from pathlib import Path

from sources.base import JobPosting
from state import load_seen_ids, mark_new, save_seen_ids


def _posting(source: str, external_id: str) -> JobPosting:
    return JobPosting(source=source, external_id=external_id, title="t", company="c", url="u")


def test_load_seen_ids_returns_empty_set_when_file_missing(tmp_path: Path):
    assert load_seen_ids(tmp_path / "state.json") == set()


def test_save_and_load_round_trip(tmp_path: Path):
    path = tmp_path / "state.json"
    postings = [_posting("saramin", "1"), _posting("worknet", "2")]
    save_seen_ids(path, postings)

    loaded = load_seen_ids(path)
    assert loaded == {"saramin:1", "worknet:2"}


def test_mark_new_flags_only_unseen_postings():
    postings = [_posting("saramin", "1"), _posting("saramin", "2")]
    seen_ids = {"saramin:1"}

    result = mark_new(postings, seen_ids)

    by_id = {p.external_id: p for p in result}
    assert by_id["1"].is_new is False
    assert by_id["2"].is_new is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Implement `state.py`**

```python
import json
from pathlib import Path

from sources.base import JobPosting


def load_seen_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("seen_ids", []))


def save_seen_ids(path: Path, postings: list[JobPosting]) -> None:
    seen_ids = sorted({_key(p) for p in postings})
    path.write_text(
        json.dumps({"seen_ids": seen_ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def mark_new(postings: list[JobPosting], seen_ids: set[str]) -> list[JobPosting]:
    for posting in postings:
        posting.is_new = _key(posting) not in seen_ids
    return postings


def _key(posting: JobPosting) -> str:
    return f"{posting.source}:{posting.external_id}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "Add state module for new-posting detection"
```

---

### Task 8: Dashboard renderer

**Files:**
- Create: `dashboard.py`
- Test: `tests/test_dashboard.py`

**Interfaces:**
- Consumes: `JobPosting` from `sources/base.py` (Task 1)
- Produces: `render(postings: list[JobPosting], failed_sources: list[str]) -> str`, used by `main.py` (Task 9)

- [ ] **Step 1: Write the failing tests**

`tests/test_dashboard.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dashboard'`

- [ ] **Step 3: Implement `dashboard.py`**

```python
import html
from datetime import datetime

from sources.base import JobPosting


def render(postings: list[JobPosting], failed_sources: list[str]) -> str:
    ordered = sorted(postings, key=lambda p: (not p.is_new, p.posted_date or ""), reverse=False)
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
    return f"""<div class="job">
{badge}<a href="{html.escape(posting.url)}" target="_blank">{html.escape(posting.title)}</a><br>
{html.escape(posting.company)} · {html.escape(location)} · {html.escape(posting.source)}
</div>"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard.py tests/test_dashboard.py
git commit -m "Add dashboard renderer"
```

---

### Task 9: Main pipeline with per-source error isolation

**Files:**
- Create: `main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `fetch()` from `sources/saramin.py`, `sources/worknet.py`, `sources/jobda.py`, `sources/jobkorea.py` (Tasks 2–5); `matches()` from `filter.py` (Task 6); `load_seen_ids`/`mark_new`/`save_seen_ids` from `state.py` (Task 7); `render()` from `dashboard.py` (Task 8)
- Produces: `run(filters: dict, secrets: dict, state_path: Path) -> str` (returns the rendered HTML; used directly by tests and by the `if __name__ == "__main__"` block, which additionally writes `dashboard.html` and reads `config/filters.json` / `config/secrets.json`)

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
from pathlib import Path
from unittest.mock import patch

from main import run
from sources.base import JobPosting

FILTERS = {"job_keywords": ["전산"], "regions": [], "experience_max_years": None, "exclude_keywords": []}
SECRETS = {"saramin_access_key": "key", "worknet_auth_key": "key"}


def _posting(source: str, external_id: str, title: str = "전산 담당자") -> JobPosting:
    return JobPosting(source=source, external_id=external_id, title=title, company="c", url="u")


def test_run_combines_all_sources_and_writes_dashboard(tmp_path: Path):
    state_path = tmp_path / "state.json"

    with (
        patch("main.saramin.fetch", return_value=[_posting("saramin", "1")]),
        patch("main.worknet.fetch", return_value=[_posting("worknet", "2")]),
        patch("main.jobda.fetch", return_value=[_posting("jobda", "3")]),
        patch("main.jobkorea.fetch", return_value=[_posting("jobkorea", "4")]),
    ):
        html_output = run(FILTERS, SECRETS, state_path)

    assert "총 4건" in html_output
    assert state_path.exists()


def test_run_continues_when_one_source_raises(tmp_path: Path):
    state_path = tmp_path / "state.json"

    with (
        patch("main.saramin.fetch", side_effect=RuntimeError("network down")),
        patch("main.worknet.fetch", return_value=[_posting("worknet", "2")]),
        patch("main.jobda.fetch", return_value=[]),
        patch("main.jobkorea.fetch", return_value=[]),
    ):
        html_output = run(FILTERS, SECRETS, state_path)

    assert "saramin 수집 실패" in html_output
    assert "총 1건" in html_output


def test_run_filters_out_non_matching_postings(tmp_path: Path):
    state_path = tmp_path / "state.json"
    filters = {**FILTERS, "job_keywords": ["전산"]}

    with (
        patch("main.saramin.fetch", return_value=[_posting("saramin", "1", title="마케팅 담당자")]),
        patch("main.worknet.fetch", return_value=[]),
        patch("main.jobda.fetch", return_value=[]),
        patch("main.jobkorea.fetch", return_value=[]),
    ):
        html_output = run(filters, SECRETS, state_path)

    assert "총 0건" in html_output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Implement `main.py`**

```python
import json
from pathlib import Path

import dashboard
import filter as job_filter
import state
from sources import jobda, jobkorea, saramin, worknet

BASE_DIR = Path(__file__).parent

_SOURCES = {
    "saramin": lambda job_keywords, secrets: saramin.fetch(job_keywords, secrets["saramin_access_key"]),
    "worknet": lambda job_keywords, secrets: worknet.fetch(job_keywords, secrets["worknet_auth_key"]),
    "jobda": lambda job_keywords, secrets: jobda.fetch(job_keywords),
    "jobkorea": lambda job_keywords, secrets: jobkorea.fetch(job_keywords),
}


def run(filters: dict, secrets: dict, state_path: Path) -> str:
    job_keywords = filters.get("job_keywords", [])
    all_postings = []
    failed_sources = []

    for name, fetch_fn in _SOURCES.items():
        try:
            all_postings.extend(fetch_fn(job_keywords, secrets))
        except Exception:
            failed_sources.append(name)

    matched = [p for p in all_postings if job_filter.matches(p, filters)]

    seen_ids = state.load_seen_ids(state_path)
    matched = state.mark_new(matched, seen_ids)
    state.save_seen_ids(state_path, matched)

    return dashboard.render(matched, failed_sources)


if __name__ == "__main__":
    filters = json.loads((BASE_DIR / "config" / "filters.json").read_text(encoding="utf-8"))
    secrets = json.loads((BASE_DIR / "config" / "secrets.json").read_text(encoding="utf-8"))
    html_output = run(filters, secrets, BASE_DIR / "state.json")
    (BASE_DIR / "dashboard.html").write_text(html_output, encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: All tests across every task PASS

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "Add main pipeline with per-source error isolation"
```

---

### Task 10: Windows Task Scheduler registration and setup docs

**Files:**
- Create: `README.md`
- Create: `scripts/register_task.ps1`

**Interfaces:**
- Consumes: `main.py` (Task 9) as the command the scheduled task runs
- Produces: a registered Windows scheduled task named `JobWatcher` that runs daily; no other code depends on this task

- [ ] **Step 1: Write `scripts/register_task.ps1`**

```powershell
$pythonPath = (Get-Command python).Source
$scriptPath = Join-Path $PSScriptRoot "..\main.py" | Resolve-Path
$workingDir = Split-Path $scriptPath -Parent

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $workingDir
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName "JobWatcher" -Action $action -Trigger $trigger -Settings $settings -Description "Daily job posting collection for job_watcher"
```

- [ ] **Step 2: Run it to register the task**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
```

Verify: `Get-ScheduledTask -TaskName "JobWatcher"` shows the task with `State: Ready`.

- [ ] **Step 3: Write `README.md`**

```markdown
# Job Watcher

매일 사람인·워크넷·잡다·잡코리아에서 채용공고를 모아 `dashboard.html`로 필터링해 보여주는 도구.

## 설치

1. Python 3.12+ 설치 (https://www.python.org/downloads/, "Add python.exe to PATH" 체크)
2. `pip install -r requirements.txt`
3. `playwright install chromium`
4. `config/secrets.json.example`을 `config/secrets.json`으로 복사하고 API 키 입력
   - 사람인 access-key: https://oapi.saramin.co.kr/join 에서 이용신청 후 발급
   - 워크넷 authKey: https://openapi.work.go.kr 에서 회원가입 후 발급

## 필터 조건 수정

`config/filters.json`을 텍스트 편집기로 열어 배열 항목을 추가/삭제:
- `job_keywords`: 제목에 하나 이상 포함되어야 함
- `regions`: 근무지에 하나 이상 포함되어야 함 (근무지 정보가 없는 공고는 통과)
- `experience_max_years`: 요구 경력 상한 (신입 포함, 경력 정보 없는 공고는 통과)
- `exclude_keywords`: 제목에 포함되면 제외

## 수동 실행

```bash
python main.py
```

`dashboard.html`이 생성/갱신됨. 브라우저로 열어서 확인.

## 매일 자동 실행

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
```

Windows 작업 스케줄러에 매일 오전 9시 실행되는 `JobWatcher` 작업이 등록됨. 등록 확인: `Get-ScheduledTask -TaskName "JobWatcher"`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md scripts/register_task.ps1
git commit -m "Add Task Scheduler registration script and setup docs"
```

- [ ] **Step 5: Manual verification**

Run `python main.py` once for real (with real `config/secrets.json` filled in) and open the generated `dashboard.html` in a browser to confirm postings render correctly end-to-end.
