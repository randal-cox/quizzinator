import re
import datetime
import pytest
from quizzinator.utils import pp

def test_pp_prints_pretty(capsys):
  """pp should pretty-print data structures to stdout."""
  data = {'alpha': [1, 2, {'beta': 3}]}
  pp(data)
  captured = capsys.readouterr()
  out = captured.out
  # Compare against pprint.pformat
  import pprint
  expected = pprint.pformat(data, indent=2) + "\n"
  assert out == expected, f"Expected: {expected!r}\nGot: {out!r}"
