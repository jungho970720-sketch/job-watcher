import json
from pathlib import Path

from sources.base import JobPosting


def load_seen_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("seen_ids", []))


def save_seen_ids(
    path: Path, postings: list[JobPosting], previous_seen_ids: set[str] = frozenset()
) -> None:
    seen_ids = sorted(set(previous_seen_ids) | {_key(p) for p in postings})
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
