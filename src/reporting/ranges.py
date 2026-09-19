"""Reporting date arithmetic for the analytics dashboard.

Pure Python, no database. Contract: docs/ANALYTICS.md ("Definitions", "Reporting range",
"Chart granularity", "Compare"). A business date is a Singapore calendar date; every span here
is an inclusive range of business dates. Nothing hardcodes a year length: spans and comparison
windows are derived by date arithmetic, so leap years fall out naturally.
"""
from datetime import date, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Asia/Singapore")

DEFAULT_RANGE = "30d"
RANGE_KEYS = ("7d", "30d", "90d", "mtd", "ytd")
ROLLING_DATES = {"7d": 7, "30d": 30, "90d": 90}

# One calendar year including a leap day; year to date always fits, and it is also the run window.
MAX_SPAN_DATES = 366
# Up to this many dates the chart uses one point per date; above it, ISO weeks.
DAILY_MAX_DATES = 90


class Span(NamedTuple):
    """Inclusive range of business dates."""

    start: date
    end: date

    @property
    def length(self):
        return (self.end - self.start).days + 1


class Bucket(NamedTuple):
    """Inclusive range of business dates summed into one chart point."""

    start: date
    end: date


def latest_complete_date(cutoff):
    """*L*: the latest business date that has ended at or before the cutoff.

    The cutoff's own date has not finished (a cutoff at exactly 00:00 is the start of that date),
    so L is always the day before the cutoff's business date.
    """
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    return cutoff.astimezone(BUSINESS_TZ).date() - timedelta(days=1)


def run_window_start(latest):
    """First business date of a run's stored window: MAX_SPAN_DATES dates ending at *L*."""
    return latest - timedelta(days=MAX_SPAN_DATES - 1)


def coerce_range(value):
    """Whitelist a client-supplied range key. Returns (key, valid); invalid falls back to the default."""
    if value in RANGE_KEYS:
        return value, True
    return DEFAULT_RANGE, False


def resolve_span(range_key, latest):
    """Span for a whitelisted range key, ending at *L*. Unknown keys raise ValueError."""
    if range_key in ROLLING_DATES:
        span = Span(latest - timedelta(days=ROLLING_DATES[range_key] - 1), latest)
    elif range_key == "mtd":
        span = Span(latest.replace(day=1), latest)
    elif range_key == "ytd":
        span = Span(latest.replace(month=1, day=1), latest)
    else:
        raise ValueError(f"unknown range: {range_key!r}")
    check_span(span)
    return span


def check_span(span):
    """Validate ordering and the length cap (also the gate for a future custom from/to range)."""
    if span.start > span.end:
        raise ValueError("span start is after its end")
    if span.length > MAX_SPAN_DATES:
        raise ValueError(f"span exceeds {MAX_SPAN_DATES} business dates")


def comparison_span(span):
    """Equal-length block of dates immediately before the span."""
    return Span(span.start - timedelta(days=span.length), span.start - timedelta(days=1))


def comparison_available(compare, window_start, history_start):
    """Whether a comparison span can be shown, per ANALYTICS.md.

    It must lie wholly inside the run window and start on or after the history start (the
    earliest date that has rows); with no history at all, nothing can be compared.
    """
    if history_start is None:
        return False
    return compare.start >= window_start and compare.start >= history_start


def granularity(span):
    return "daily" if span.length <= DAILY_MAX_DATES else "weekly"


def buckets(span, mode):
    """Chart buckets for a span: "daily" single dates, or "weekly" ISO weeks (Monday start) clipped to the span."""
    if mode == "daily":
        return [Bucket(day, day) for day in _each_date(span)]
    if mode != "weekly":
        raise ValueError(f"unknown granularity: {mode!r}")
    result = []
    cursor = span.start
    while cursor <= span.end:
        week_end = cursor + timedelta(days=6 - cursor.weekday())
        result.append(Bucket(cursor, min(week_end, span.end)))
        cursor = result[-1].end + timedelta(days=1)
    return result


def shift_buckets(bucket_list, days):
    """Shift buckets back by a number of days (comparison buckets line up one-to-one with the selected ones)."""
    delta = timedelta(days=days)
    return [Bucket(item.start - delta, item.end - delta) for item in bucket_list]


def _each_date(span):
    return (span.start + timedelta(days=offset) for offset in range(span.length))
