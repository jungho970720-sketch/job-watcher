from dataclasses import dataclass


class SourceAPIError(Exception):
    """A source's API returned an error payload instead of job data.

    Saramin and Worknet both answer an invalid/expired key with HTTP 200 and an
    error body, so `raise_for_status()` never fires. Parsing such a body yields
    zero postings, which is indistinguishable from "no matching jobs today" —
    the failure would be invisible on the dashboard. Sources raise this instead
    so main.py records the source as failed and shows a warning banner.
    """


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
