import requests

from sources.base import JobPosting, SourceAPIError

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
    # An invalid/expired key, a bad parameter, or an exceeded daily quota all
    # come back as HTTP 200 with {"code": N, "message": "..."} and no "jobs"
    # key, so raise_for_status() never fires. Detect it here — otherwise the
    # source silently contributes zero postings and the dashboard looks the
    # same as a genuinely quiet day.
    if "jobs" not in data:
        raise SourceAPIError(
            f"Saramin API error (code={data.get('code')}): {data.get('message')}"
        )

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
                # Saramin's "max" is the top of the accepted range (e.g. min=0,
                # max=20 means "신입 welcome, up to 20 years"), not a minimum
                # requirement like Worknet/JobKorea use. filter.py's
                # _matches_experience assumes "minimum years required"
                # semantics (years <= max_years), so we must use "min" here;
                # fall back to "max" only if "min" is absent.
                experience_years_required=(
                    _to_int(experience.get("min"))
                    if experience.get("min") is not None
                    else _to_int(experience.get("max"))
                ),
                posted_date=(job.get("posting-date") or "")[:10] or None,
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
