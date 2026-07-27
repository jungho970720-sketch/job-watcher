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
