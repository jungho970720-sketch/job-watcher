import json
import sys
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
        except Exception as exc:
            failed_sources.append(name)
            # Log only the exception type, never str(exc)/traceback: requests'
            # raise_for_status() embeds the full request URL (including
            # access-key=.../authKey=... query params) in the message, so
            # logging it would leak secrets into stdout/stderr and log files.
            print(f"[{name}] fetch failed: {type(exc).__name__}", file=sys.stderr)

    matched = [p for p in all_postings if job_filter.matches(p, filters)]

    seen_ids = state.load_seen_ids(state_path)
    matched = state.mark_new(matched, seen_ids)
    state.save_seen_ids(state_path, matched, previous_seen_ids=seen_ids)

    return dashboard.render(matched, failed_sources)


if __name__ == "__main__":
    filters = json.loads((BASE_DIR / "config" / "filters.json").read_text(encoding="utf-8"))
    secrets = json.loads((BASE_DIR / "config" / "secrets.json").read_text(encoding="utf-8"))
    html_output = run(filters, secrets, BASE_DIR / "state.json")
    (BASE_DIR / "dashboard.html").write_text(html_output, encoding="utf-8")
