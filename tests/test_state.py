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
