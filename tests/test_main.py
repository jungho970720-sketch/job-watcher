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


def test_run_logs_only_exception_type_to_stderr_without_leaking_secrets(tmp_path: Path, capsys):
    state_path = tmp_path / "state.json"
    secret_value = "super-secret-access-key"
    secrets = {"saramin_access_key": secret_value, "worknet_auth_key": secret_value}

    with (
        patch(
            "main.saramin.fetch",
            side_effect=RuntimeError(f"failed request with access-key={secret_value}"),
        ),
        patch("main.worknet.fetch", return_value=[]),
        patch("main.jobda.fetch", return_value=[]),
        patch("main.jobkorea.fetch", return_value=[]),
    ):
        run(FILTERS, secrets, state_path)

    captured = capsys.readouterr()
    assert "[saramin] fetch failed: RuntimeError" in captured.err
    assert secret_value not in captured.err
    assert secret_value not in captured.out


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
