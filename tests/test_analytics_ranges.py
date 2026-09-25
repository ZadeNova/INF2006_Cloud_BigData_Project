"""Reporting date arithmetic (no database). Expected values are worked out by hand in comments."""
from datetime import date, datetime, timedelta, timezone

import pytest

from reporting import ranges
from reporting.ranges import Bucket, Span

SGT = ranges.BUSINESS_TZ


# --- L: latest complete business date -------------------------------------------------------

@pytest.mark.parametrize("cutoff, expected", [
    (datetime(2025, 1, 1, 0, 0, tzinfo=SGT), date(2024, 12, 31)),        # midnight belongs to the next date
    (datetime(2025, 1, 1, 23, 59, 59, tzinfo=SGT), date(2024, 12, 31)),  # 1 Jan still in progress to its last second
    # 16:00 UTC is 00:00 the next day in Singapore (UTC+8, no daylight saving)
    (datetime(2025, 1, 1, 16, 0, tzinfo=timezone.utc), date(2025, 1, 1)),
    (datetime(2025, 1, 1, 15, 59, tzinfo=timezone.utc), date(2024, 12, 31)),
    (datetime(2024, 3, 1, 0, 0, tzinfo=SGT), date(2024, 2, 29)),         # leap day is a real date
])
def test_latest_complete_date(cutoff, expected):
    assert ranges.latest_complete_date(cutoff) == expected


def test_latest_complete_date_requires_aware_cutoff():
    with pytest.raises(ValueError):
        ranges.latest_complete_date(datetime(2025, 1, 1))


# --- preset spans ---------------------------------------------------------------------------

def test_presets_at_end_of_leap_year():
    latest = date(2024, 12, 31)
    assert ranges.resolve_span("7d", latest) == Span(date(2024, 12, 25), latest)
    assert ranges.resolve_span("30d", latest) == Span(date(2024, 12, 2), latest)
    # 31 Dec minus 89 days: 1 Dec is -30, 1 Nov is -60, 3 Oct is -89
    assert ranges.resolve_span("90d", latest) == Span(date(2024, 10, 3), latest)
    assert ranges.resolve_span("mtd", latest) == Span(date(2024, 12, 1), latest)
    assert ranges.resolve_span("ytd", latest) == Span(date(2024, 1, 1), latest)


def test_ytd_length_follows_the_calendar_year():
    assert ranges.resolve_span("ytd", date(2024, 12, 31)).length == 366   # leap year
    assert ranges.resolve_span("ytd", date(2025, 12, 31)).length == 365   # cap of 366 still accepts it


def test_ytd_on_leap_day_is_sixty_dates():
    span = ranges.resolve_span("ytd", date(2024, 2, 29))    # 31 January + 29 February
    assert span == Span(date(2024, 1, 1), date(2024, 2, 29))
    assert span.length == 60


def test_february_2024_month_to_date_is_twenty_nine_dates():
    assert ranges.resolve_span("mtd", date(2024, 2, 29)).length == 29
    assert ranges.resolve_span("mtd", date(2025, 2, 28)).length == 28


def test_month_to_date_on_the_first_is_one_date():
    assert ranges.resolve_span("mtd", date(2024, 3, 1)) == Span(date(2024, 3, 1), date(2024, 3, 1))


def test_seven_dates_across_the_leap_day():
    # 24, 25, 26, 27, 28, 29 Feb and 1 Mar
    span = ranges.resolve_span("7d", date(2024, 3, 1))
    assert span == Span(date(2024, 2, 24), date(2024, 3, 1))
    assert span.length == 7


def test_unknown_range_is_rejected():
    with pytest.raises(ValueError):
        ranges.resolve_span("1y", date(2024, 6, 15))


def test_span_cap_and_ordering():
    ranges.check_span(Span(date(2024, 1, 1), date(2024, 12, 31)))          # 366 dates accepted
    with pytest.raises(ValueError):
        ranges.check_span(Span(date(2024, 1, 1), date(2025, 1, 1)))         # 367 dates
    with pytest.raises(ValueError):
        ranges.check_span(Span(date(2024, 2, 2), date(2024, 2, 1)))         # start after end


def test_run_window_is_366_dates_ending_at_l():
    # 2024 has 366 dates, so the window starts on 1 Jan; 2025 has 365, so it starts on 31 Dec 2024
    assert ranges.run_window_start(date(2024, 12, 31)) == date(2024, 1, 1)
    assert ranges.run_window_start(date(2025, 12, 31)) == date(2024, 12, 31)
    for latest in (date(2024, 12, 31), date(2025, 12, 31), date(2024, 3, 1)):
        assert (latest - ranges.run_window_start(latest)).days + 1 == ranges.MAX_SPAN_DATES


# --- comparison span ------------------------------------------------------------------------

def test_comparison_span_spans_the_leap_day():
    span = Span(date(2024, 3, 1), date(2024, 3, 7))
    comparison = ranges.comparison_span(span)
    assert comparison == Span(date(2024, 2, 23), date(2024, 2, 29))   # ends on the leap day
    assert comparison.length == span.length


def test_comparison_span_in_a_non_leap_year():
    comparison = ranges.comparison_span(Span(date(2025, 3, 1), date(2025, 3, 7)))
    assert comparison == Span(date(2025, 2, 22), date(2025, 2, 28))


def test_comparison_available_rules():
    window_start, history_start = date(2024, 1, 1), date(2024, 1, 10)
    inside = Span(date(2024, 2, 1), date(2024, 2, 7))
    assert ranges.comparison_available(inside, window_start, history_start)
    # starts exactly at the history start: allowed
    assert ranges.comparison_available(Span(date(2024, 1, 10), date(2024, 1, 16)), window_start, history_start)
    # starts before the first date the run holds
    assert not ranges.comparison_available(Span(date(2024, 1, 9), date(2024, 1, 15)), window_start, history_start)
    # starts before the run window even though history claims otherwise
    assert not ranges.comparison_available(Span(date(2023, 12, 31), date(2024, 1, 6)), window_start, date(2023, 1, 1))
    # no history at all
    assert not ranges.comparison_available(inside, window_start, None)


# --- chart granularity and buckets ----------------------------------------------------------

@pytest.mark.parametrize("length, expected", [(90, "daily"), (91, "weekly")])
def test_granularity_switches_after_ninety_dates(length, expected):
    start = date(2024, 1, 1)
    assert ranges.granularity(Span(start, start + timedelta(days=length - 1))) == expected


def test_daily_buckets_include_the_leap_day():
    result = ranges.buckets(Span(date(2024, 2, 27), date(2024, 3, 2)), "daily")
    assert [item.start for item in result] == [
        date(2024, 2, 27), date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1), date(2024, 3, 2)]
    assert all(item.start == item.end for item in result)


def test_weekly_buckets_are_iso_weeks_clipped_to_the_span():
    # 6 Mar 2024 is a Wednesday, 20 Mar a Wednesday: 5 + 7 + 3 dates
    result = ranges.buckets(Span(date(2024, 3, 6), date(2024, 3, 20)), "weekly")
    assert result == [
        Bucket(date(2024, 3, 6), date(2024, 3, 10)),     # Wed to Sun, clipped at the start
        Bucket(date(2024, 3, 11), date(2024, 3, 17)),    # full Monday to Sunday week
        Bucket(date(2024, 3, 18), date(2024, 3, 20)),    # Mon to Wed, clipped at the end
    ]


def test_weekly_buckets_of_whole_weeks_are_not_clipped():
    result = ranges.buckets(Span(date(2024, 3, 4), date(2024, 3, 17)), "weekly")   # Monday to Sunday, two weeks
    assert result == [Bucket(date(2024, 3, 4), date(2024, 3, 10)), Bucket(date(2024, 3, 11), date(2024, 3, 17))]


def test_unknown_granularity_is_rejected():
    with pytest.raises(ValueError):
        ranges.buckets(Span(date(2024, 3, 4), date(2024, 3, 17)), "monthly")


# The longest daily span (90 points) and the 366-date weekly span; bucket shapes have the dedicated tests above.
@pytest.mark.parametrize("key", ["90d", "ytd"])
def test_buckets_tile_the_span_exactly(key):
    span = ranges.resolve_span(key, date(2024, 12, 31))
    result = ranges.buckets(span, ranges.granularity(span))
    assert result[0].start == span.start and result[-1].end == span.end
    for previous, following in zip(result, result[1:]):
        assert following.start == previous.end + timedelta(days=1)
    assert sum((item.end - item.start).days + 1 for item in result) == span.length
    assert len(result) <= 90     # the chart never carries more than 90 points


def test_shifted_buckets_tile_the_comparison_span_and_line_up_one_to_one():
    span = Span(date(2024, 3, 6), date(2024, 3, 20))              # 15 dates
    selected = ranges.buckets(span, "weekly")
    comparison = ranges.comparison_span(span)                       # 20 Feb to 5 Mar
    shifted = ranges.shift_buckets(selected, span.length)
    assert shifted == [
        Bucket(date(2024, 2, 20), date(2024, 2, 24)),
        Bucket(date(2024, 2, 25), date(2024, 3, 2)),
        Bucket(date(2024, 3, 3), date(2024, 3, 5)),
    ]
    assert shifted[0].start == comparison.start and shifted[-1].end == comparison.end
    for previous, following in zip(shifted, shifted[1:]):
        assert following.start == previous.end + timedelta(days=1)
    for chosen, other in zip(selected, shifted):                     # bucket k has the same length in both series
        assert (chosen.end - chosen.start) == (other.end - other.start)
