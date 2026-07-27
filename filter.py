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
