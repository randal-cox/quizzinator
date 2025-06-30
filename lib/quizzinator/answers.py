import os.path
import re

from typing import Optional
from pathlib import Path

from .logging import logger
from .cli import cli_get_args

def gender_rule_numbers_to_names(number: str):
  number = number.strip()
  if number == "": return None
  lookup = {
    '1': 'Man',
    '2': 'Woman',
    '3': 'Non Binary',
    '4': 'Trans woman',
    '5': 'Trans man',
    '6': 'Gender - nonconforming',
    '7': 'Genderfluid',
    '8': 'Genderqueer',
    '9': 'Two - spirit',
    '10': 'Intersex',
    '11': 'Agender',
    '12': 'Other',
  }
  if number in lookup: return lookup[number]
  raise ValueError(f'Unknown gender rule number "{number}"')

def role_rule_numbers_to_names(number: str):
  number = number.strip()
  if number == "": return None
  lookup = {
    '1': 'Top',
    '2': 'Bottom',
    '3': 'Switch',
    '4': 'Sadist',
    '5': 'Masochist',
    '6': 'Master',
    '7': 'Slave',
    '8': 'Dominant',
    '9': 'Submissive',
    '10': 'Other'
  }
  if number in lookup: return lookup[str(number)]
  raise ValueError(f'Unknown role rule number "{number}"')

def evaluate_gender_consistency(hint_set: set[str], response_set: set[str]) -> str:
  hint_set = [gender_rule_numbers_to_names(n) for n in hint_set]
  response_set =[gender_rule_numbers_to_names(n) for n in response_set]
  if hint_set == response_set:
    return 'exact'
  return 'discordant'

def evaluate_role_consistency_which(s: set[str]):
  group = {
    "Master":     'L',
    "Top":        'L',
    "Dominant":   'L',
    "Sadist":     'L',

    "Slave":      'r',
    "Bottom":     'r',
    "Submissive": 'r',
    "Masochist":  'r',

    "Switch":     '/',

    'Other':      '?',
  }
  t = set([group.get(v, None) for v in s])
  if None in t: raise ValueError(f"Illegal value in {s}")
  if 'L' in t and 'r' in t: t.add('/')
  if '/' in t: return '/'
  if 'L' in t: return 'L'
  if 'r' in t: return 'r'
  return ''

def evaluate_role_consistency(hint_set: set[str], response_set: set[str]) -> str:
  """Used in concordance to test for 'close-enough' Roles"""

  # convert the numbers to names
  #print(["===>", hint_set, response_set])
  named_hint_set = [role_rule_numbers_to_names(n) for n in hint_set if n is not '']
  named_response_set = [role_rule_numbers_to_names(n) for n in response_set if n is not '']
  #print(["===>", named_hint_set, named_response_set])
  if named_hint_set == named_response_set: return 'exact'

  hint_kind = evaluate_role_consistency_which(named_hint_set)
  response_kind = evaluate_role_consistency_which(named_response_set)
  if hint_kind == response_kind:
    return 'concordant'
  else:
    return 'discordant'


def pattern_consensus(pattern: str, text: str) -> str | bool:
  """
  Find all occurrences of `pattern` in `text`. If they all agree on one value, return it; otherwise return False.
  Returns False if no matches or conflicting matches.
  """
  flags = re.IGNORECASE | re.MULTILINE
  matches = re.findall(pattern, text.strip(), flags=flags)
  if not matches:
    return False
  # If the regex has capturing groups, re.findall returns tuples
  # Normalize to a flat list of strings
  flat = []
  for m in matches:
    if isinstance(m, tuple):
      flat.extend(filter(None, m))
    else:
      flat.append(m)
  # Deduplicate
  uniq = set(flat)
  if len(uniq) == 1:
    return uniq.pop()
  return False

def pattern_all(pattern: str, text: str) -> list[str]:
  """
  Find all occurrences of `pattern` in `text`, flatten any
  capture-group tuples, dedupe *but preserve order*, and return
  the list of strings (or empty list if none).
  """
  flags = re.IGNORECASE | re.MULTILINE
  raw = re.findall(pattern, text, flags)
  flat = []
  for m in raw:
    if isinstance(m, tuple):
      for g in m:
        if g is not None:
          flat.append(g)
    else:
      flat.append(m)
  # preserve first-seen order when deduping
  seen = set()
  ordered = []
  for v in flat:
    if v not in seen:
      seen.add(v)
      ordered.append(v)
  return ordered


import re
from typing import Optional, Union, List

def extract_llm_answer(
    text: str,
    target: str | None = None,
    *,
    multi: bool = False
) -> Optional[Union[str, List[str]]]:
  """
  Try each regex in order.  As soon as one yields matches:
    - if multi=True, return all unique matches from that pattern
    - if multi=False and exactly one unique match, return it
    - otherwise (multi=False and >1 matches), skip to the next pattern
  If none match, return None.
  """
  flags = re.IGNORECASE | re.MULTILINE
  tpat  = target or r'\d+(?:-\d+)*|[A-Z]'
  tgt   = rf'\#?({tpat})'

  patterns = [
    # 0) Final answer always most important
    r'\*\*\s*Final Answer\s*:?[\\*\\s]*Answer:\s*_T_',

    # Boxed is next most certain
    r'\\boxed\{([^}]+)\}',

    # “Answer Selected:” for *any* target (unquoted, comma/dash-sep, etc)
    r'Answer Selected:\s*_T_',
    r"Answer Selected:\s*'_T_'",
    r'Answer Selected:\s*"_T_"',

    # Now the regular “Answer:” patterns
    r'Answer:\s*_T_',
    r'Answer:\s*\(_T_\)',
    r'Answer:\s*"_T_"',
    r"Answer:\s*'_T_'",
    r'\*\*\s*Answer\s*:?[\\*\\s]*_T_',
    r'<answer>_T_</answer>',

    # 5) fallback fuzzy patterns
    r'^_T_$',
    r'\*\*_T_\*\*',
    r'\*\*\(_T_\)\*\*',
    r'\(_T_\)',
  ]

  for pat in patterns:
    # build the real regex
    regex = pat.replace('_T_', tgt)
    raw   = re.findall(regex, text.strip(), flags)

    if not raw:
      continue

    # flatten tuples vs strings
    flat: List[str] = []
    for m in raw:
      if isinstance(m, tuple):
        flat.extend([g for g in m if g])
      elif isinstance(m, str):
        m = m.replace(',','-').replace(' ','')
        if '-' in m:
          flat += m.split('-')
        else:
          flat.append(m)
      else:
        flat.append(m)

    # dedupe while preserving order
    uniq = sorted(list(set(flat)))

    if not uniq:
      continue

    # if multi, return every unique match right away
    if multi:
      return uniq

    # single mode: only accept exactly one match
    if len(uniq) == 1:
      return uniq[0]
    # else >1 → ambiguous for this pattern, keep searching

  # no pattern yielded an acceptable answer
  return None




def get_legal_answer(prompt: str, text: str, mode: str, legal_values: dict[str]) -> list:
  if '### Final Answer' in text:
    text = text.split('### Final Answer', 1)[1]

  if mode == 'ignore':
    return [True, '']

  if mode == 'free':
    return [True, text]

  if mode == 'line':
    # first try the normal extractor:
    extracted = extract_llm_answer(text, r'.+', multi=False)
    # if nothing matched, grab the first non-empty line
    if extracted is None:
      for line in text.splitlines():
        line = line.strip()
        if line:
          extracted = line
          break
    return [extracted is not None, extracted]

  if mode == 'word':
    # 1) try the extractor with a “one-or-more non-space” target
    extracted = extract_llm_answer(text, r'\S+', multi=False)

    # 2) fallback: first non-empty word in the raw text
    if extracted is None:
      for tok in re.split(r'\s+', text):
        tok = tok.strip()
        if tok:
          extracted = tok
          break

    return [extracted is not None, extracted]

  if mode == 'number':
    extracted = extract_llm_answer(text, r'[\d,]+')
    ok = extracted is not None
    if not ok: log_failures(mode, prompt, text)
    return [ok, extracted]

  if mode in ('date'):
    extracted = extract_llm_answer(text, r'\S+')
    ok = extracted is not None
    if not ok:
      log_failures(mode, prompt, text)
    else:
      try:
        parsed = datetime.strptime(extracted, "%Y-%m-%d")
        return [True, parsed]
      except ValueError:
        log_failures(mode, prompt, text)
        return [False, extracted]

  if mode == 'single':
    # choose an appropriate target regex
    tmap = {
      'number': r'[\d,]+',
      'date': r'\S+',
    }
    extracted = extract_llm_answer(text, '|'.join(map(str, reversed(legal_values))))
    ok = extracted is not None
    if not ok: log_failures(mode, prompt, text)
    if mode == 'date' and ok:
      try:
        parsed = datetime.strptime(extracted, "%Y-%m-%d")
        return [True, parsed]
      except ValueError:
        return [False, extracted]
    return [ok, extracted]


  if mode == 'multi':

    lv = '|'.join(map(str, reversed(legal_values)))
    # allow comma or hyphen, with optional surrounding spaces
    sep = r'(?:\s*[-,]\s*)'
    mv = rf'(?:{lv})(?:{sep}(?:{lv}))*'
    #
    # # build a “legal‐values” alternation: e.g. '1|2|3|4|5|6|7'
    # lv = '|'.join(map(str, reversed(legal_values)))
    #
    # # allow comma **or** hyphen between values, with optional spaces
    # sep = r'(?:\s*[-,]\s*)'
    # mv = rf'(?:{lv})(?:{sep}(?:{lv}))*'

    extracted = extract_llm_answer(text, mv, multi=True)
                 #.replace(',','-').replace(' ', ''))
    if extracted:
      # strip any stray whitespace just in case
      return [True, [v.strip() for v in extracted]]

    log_failures(mode, prompt, text)
    return [False, text]

  raise ValueError(f'Unknown mode {mode}')


def log_failures(mode, prompt, text):
  args = cli_get_args()
  path = Path(args.dir) / "errors.txt"
  # no matches → log failure as before
  div1 = '=' * 60 + '\n'
  div2 = '-' * 60 + '\n'
  with open(path, 'a') as f:
    f.write(div1)
    f.write(f'mode = {mode}\n')
    f.write(div2)
    f.write(f'prompt\n{prompt}\n')
    f.write(div2)
    f.write(f'text\n{text}\n')
    f.write(div2)
    f.write(f'Expect\n\n')
