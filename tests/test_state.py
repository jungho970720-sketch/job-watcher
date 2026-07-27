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


def test_save_seen_ids_merges_with_previous_ids_instead_of_overwriting(tmp_path: Path):
    path = tmp_path / "state.json"
    posting_a = _posting("saramin", "1")
    posting_b = _posting("worknet", "2")

    # Day 1: both sources succeed.
    save_seen_ids(path, [posting_a, posting_b])
    previous_seen_ids = load_seen_ids(path)
    assert previous_seen_ids == {"saramin:1", "worknet:2"}

    # Day 2: worknet's source fails to fetch, so only posting_a is seen today.
    # Passing the previously-loaded seen_ids must preserve worknet:2 rather
    # than wiping it out.
    save_seen_ids(path, [posting_a], previous_seen_ids=previous_seen_ids)

    loaded = load_seen_ids(path)
    assert "worknet:2" in loaded
    assert loaded == {"saramin:1", "worknet:2"}
