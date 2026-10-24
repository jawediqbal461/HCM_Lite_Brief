"""A single notion of "now" for the business rules.

Attendance dates and the office-hours comparison must both use the company's own
timezone: a check-in at 14:00 in Karachi is late even though it is 09:00 UTC, and
"today" on a dashboard has to mean the same day the attendance module stamped.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = ZoneInfo("UTC")


def company_tz(settings) -> ZoneInfo:
    name = getattr(settings, "timezone", None) or "UTC"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def business_now(settings) -> datetime:
    """Timezone-aware current time in the company's timezone."""
    return datetime.now(company_tz(settings))


def business_today(settings) -> date:
    return business_now(settings).date()
