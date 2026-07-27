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
