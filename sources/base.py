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
