import time, pprint, datetime
from collections import Counter

def timestamp_str() -> str:
    """YYYY-MM-DDThh-mm-ss"""
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def pp(arg):
  pprint.pprint(arg, indent=2)


def pythonify_string(s):
    ret = ""
    for char in s:
        if char in string.ascii_letters or char in string.digits or \
            char in string.punctuation or char.isspace():
            ret += char
        else:
            ret += '\\0' + oct(ord(char))[2:]
    return ret

def ngram_repeat(text: str, L: int = 30, K: int = 2) -> dict[str,int]:
    """
    Returns the worst offender string and its count
    """
    counts = Counter(text[i:i+L] for i in range(len(text)-L+1))
    ret =  {s:c for s,c in counts.items() if c >= K}
    ret = sorted(
        ret.items(),
        key=lambda item: item[1],      # sort by the count
        reverse=True                   # highest counts first
    )
    ret = [
        (s, cnt)
        for s, cnt in ret
        if len(set(s)) > 3
    ] or [
        ['', 0]
    ]

    return ret[0]

def human_duration(seconds: float, significance=2):
    """
    Convert an elapsed time in seconds to a human-readable string with a specified
    number of significant time units. Uses weeks (w), days (d), hours (h), minutes (m),
    and seconds (s). The last unit displayed includes one decimal place, folding in
    part of the next smaller unit.
    """
    # Define units from largest to smallest
    unit_defs = [
        ('w', 7 * 24 * 3600),  # weeks
        ('d', 24 * 3600),      # days
        ('h', 3600),           # hours
        ('m', 60),             # minutes
        ('s', 1),              # seconds
    ]

    # Compute integer and fractional parts for each unit
    segments = {}
    rem = seconds
    for name, unit_seconds in unit_defs:
        int_part = int(rem // unit_seconds)
        frac_part = int_part + (rem % unit_seconds) / unit_seconds
        segments[name] = [int_part, frac_part]
        rem -= int_part * unit_seconds

    # Build the output using up to 'significance' non-zero units
    parts = []
    count = 0
    for name, _ in unit_defs:
        int_part, frac_part = segments[name]
        if int_part > 0 and count < significance:
            if count < significance - 1:
                parts.append(f"{int_part}{name}")
            else:
                parts.append(f"{frac_part:.1f}{name}")
            count += 1

    # Fallback to seconds if no non-zero units
    if not parts:
        if significance == 1:
            parts = [f"{seconds:.1f}s"]
        else:
            parts = [f"{int(seconds)}s"]

    return ' '.join(parts)
