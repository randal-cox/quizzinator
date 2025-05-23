import pytest
from quizzinator.utils import human_duration
import pytest

def test_example_4h13m11s_default():
    # 4 hours, 13 minutes, 11 seconds -> "4h 13.2m"
    assert human_duration(4 * 3600 + 13 * 60 + 11) == "4h 13.2m"

def test_weeks_days_default():
    # 8 days, 3 hours -> 1 week + 1 day + 3 hours
    seconds = 8 * 24 * 3600 + 3 * 3600
    # Default significance=2 picks weeks and days (with fractional day)
    assert human_duration(seconds) == "1w 1.1d"

def test_weeks_days_hours_significance_3():
    seconds = 8 * 24 * 3600 + 3 * 3600
    # significance=3 picks weeks, days, and hours (fractional hours)
    assert human_duration(seconds, significance=3) == "1w 1d 3.0h"

def test_zero_default():
    # zero seconds fallback to integer seconds
    assert human_duration(0) == "0s"

def test_zero_significance_1():
    # zero seconds with single-unit decimal
    assert human_duration(0, significance=1) == "0.0s"

def test_fractional_seconds_sig1():
    # 1.234 seconds -> "1.2s"
    assert human_duration(1.234, significance=1) == "1.2s"

def test_minutes_seconds_default():
    seconds = 1 * 60 + 30
    # Default significance=2 picks minutes and seconds (fractional seconds)
    assert human_duration(seconds) == "1m 30.0s"

def test_minutes_seconds_significance_1():
    seconds = 1 * 60 + 30
    # With significance=1, shows only minutes with decimal
    assert human_duration(seconds, significance=1) == "1.5m"

def test_more_units_than_significance():
    seconds = 65  # 1 minute, 5 seconds
    # significance > number of non-zero units behaves like default logic
    assert human_duration(seconds, significance=5) == "1m 5s"
