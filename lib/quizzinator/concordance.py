import argparse, os, csv, json, itertools
from pathlib import Path

from .logging import logger
from .utils import pp
from .cli import cli_log_args, cli_set_args, cli_get_args
from .questions import parse_questions
from .answers import evaluate_role_consistency


def concordance_cli_args():
  p = argparse.ArgumentParser(
    prog="concordance",
    description="Compare LLM responses to the initial hints"
  )
  p.add_argument(
    "dir",
    help="Path to survey directory"
  )
  p.add_argument(
    "--experiment",
    type=str,
    default="generic",
    help="The name of the experiment to analyze"
  )
  p.add_argument(
    '--hints',
    type=str,
    default="",
    help="Add the names of questions that the LLM should know the answers to ahead of time, separated by commas"
  )
  return p.parse_args()

def concordance_main():
  args = concordance_cli_args()
  args.hints = args.hints.split(',')
  if args.hints == ['']: args.hints = []
  cli_set_args(args)
  cli_log_args(args)

  # Get everything the humans once answered
  path_hints = Path(args.dir) /  "hints.csv"
  humans: List[dict[str, str]] = []
  with open(path_hints, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
      humans.append(row)

  # Get the answers from the LLM
  path_data = Path(args.dir) / 'experiments' / args.experiment / 'info' / 'data.json'
  with open(path_data, encoding='utf-8') as f:
    responses = json.load(f)['responses']

  # get the questions
  questions = {}
  for q in parse_questions(Path(args.dir) / 'questions.txt'):
    questions[q.name] = q

  cycled_humans = itertools.islice(itertools.cycle(humans), len(responses))
  counts = {
    'all': 0,
  }
  for hint in args.hints:
    print(hint)
    for llm, human in list(zip(responses, cycled_humans)):
      human_response = set(human[hint].split(','))
      llm_response = set(llm[hint].replace(',','-').replace('[','').replace(']','').replace("'",'').split('-'))

      counts['all'] = counts.get('all',0) + 1

      # # exact match
      # if human_response == llm_response:
      #   counts['exact'] = counts.get('exact', 0) + 1
      #   print(f" matched with {len(human_response)} answers")
      #   print()
      #   continue

      # look for consistency
      a = evaluate_role_consistency(set(human_response), set(llm_response))
      print(f" {a}")
      if a == 'exact match':
        w = 'exact'
      elif a in ['semantically close', 'partial match']:
        w = 'close'
      elif a in ['contradiction', 'unrelated']:
        w = 'mismatch'
      else:
        print(f"unexpected matching {a}")

      counts[w] = counts.get(w,0) + 1

      # a nice display for the differences
      q = questions[hint]
      options = {}
      for o in q.options: options[o.code] = o.text
      all_answers = set([*human_response, *llm_response])
      all_answers = list(all_answers)
      all_answers = [a for a in all_answers if a != '']
      all_answers = sorted(all_answers, key=int)
      for answer in all_answers:
        msg = f'{answer:>2s}: '
        msg += 'h' if answer in human_response else '_'
        msg += ' '
        msg += 'l' if answer in llm_response else '_'
        msg += ': '
        msg += options[int(answer)]
        print(msg)


      print()

  print("==================================")
  print(f"{'Total':<30s}\t{counts['all']}")
  print(f"{'Exact':<30s}\t{counts['exact']}\t{100 * counts['exact'] / counts['all']:.1f}")
  close_cum = counts['exact'] + counts['close']
  print(f"{'Close':<30s}\t{close_cum}\t{100 * close_cum / counts['all']:.1f}")
  print(f"{'Mismatch':<30s}\t{counts['mismatch']}\t{100 * counts['mismatch'] / counts['all']:.1f}")
