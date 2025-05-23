# tests/test_extract_llm_answer.py
import re
import datetime
import pytest
from quizzinator.utils import timestamp_str

def test_timestamp_str_format():
  """timestamp_str should match YYYY-MM-DDThh-mm-ss format and be parseable."""
  ts = timestamp_str()
  # Match pattern
  assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", ts), f"Bad format: {ts}"
  # Parse back into datetime
  dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
  assert isinstance(dt, datetime.datetime)

def test_timestamp_str_current_bounds():
  """timestamp_str should represent a time within one second of now."""
  now = datetime.datetime.now()
  ts = timestamp_str()
  dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
  # dt should be within 1 second of now
  assert abs((dt - now).total_seconds()) < 1, f"Timestamp {dt} is not within 1s of now {now}"
