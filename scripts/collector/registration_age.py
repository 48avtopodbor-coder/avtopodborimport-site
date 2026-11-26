"""Month-level registration dates and the rolling customs age window."""

import calendar
from collections import Counter
from datetime import date, timedelta
import re

DELIVERY_DAYS = 45
_YEAR_FIRST = re.compile(r"([0-9]{4})([-/.])([0-9]{1,2})(?:\2([0-9]{1,2}))?")
_CHINESE = re.compile(r"([0-9]{4})年([0-9]{1,2})月(?:([0-9]{1,2})日)?")
_DAY_FIRST = re.compile(r"([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{4})")


def registration_month(first_reg_date, year):
    """Keep the source month, using 1 July of the registration year as a fallback."""
    text = str(first_reg_date or "").strip()
    parts = _YEAR_FIRST.fullmatch(text)
    if parts:
        y, _, m, d = parts.groups()
    else:
        parts = _CHINESE.fullmatch(text)
        if parts:
            y, m, d = parts.groups()
        else:
            parts = _DAY_FIRST.fullmatch(text)
            if parts:
                d, m, y = parts.groups()
    if parts:
        try:
            return date(int(y), int(m), int(d or "1")).replace(day=1)
        except ValueError:
            pass
    year_text = str(year or "").strip()
    if re.fullmatch(r"[0-9]{1,4}", year_text) and int(year_text) > 0:
        return date(int(year_text), 7, 1)
    return None


def _years_before(day, years):
    year = day.year - years
    return date(year, day.month, min(day.day, calendar.monthrange(year, day.month)[1]))


def customs_registration_bounds(today=None):
    """Return the exclusive oldest and inclusive youngest registration dates."""
    clearance = (today or date.today()) + timedelta(days=DELIVERY_DAYS)
    return _years_before(clearance, 5), _years_before(clearance, 3)


def customs_years(today=None):
    oldest, youngest = customs_registration_bounds(today)
    return oldest.year, youngest.year


def in_customs_window(month, today=None):
    """A month qualifies when both its first and last day meet the age bounds."""
    if month is None:
        return False
    oldest, youngest = customs_registration_bounds(today)
    last_day = month.replace(day=calendar.monthrange(month.year, month.month)[1])
    return oldest < month.replace(day=1) and last_day <= youngest


def registration_year_summary(rows, expected_years=()):
    """Summarize years from the registration date, falling back to the stored year."""
    counts = Counter(dict.fromkeys(expected_years, 0))
    unknown = 0
    for first_reg_date, year in rows:
        month = registration_month(first_reg_date, year)
        if month is None:
            unknown += 1
        else:
            counts[month.year] += 1
    parts = [f"{year}: {count}" for year, count in sorted(counts.items())]
    if unknown:
        parts.append(f"неизвестно: {unknown}")
    return " | ".join(parts)
