import argparse, os, csv, json, itertools
from pathlib import Path

from .logging import logger
from .utils import pp
from .cli import cli_log_args, cli_set_args, cli_get_args
from .questions import parse_questions

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
  counts = [0,0]
  for hint in args.hints:
    print(hint)
    for llm, human in list(zip(responses, cycled_humans)):
      human_response = human[hint].split(',')
      llm_response = llm[hint].replace(',','-').replace('[','').replace(']','').replace("'",'').split('-')
      counts[1] += 1
      if human_response == llm_response:
        counts[0] += 1
        print(f" matched with {len(human_response)} answers")
        print()
        continue
      q = questions[hint]
      options = {}
      for o in q.options: options[o.code] = o.text

      all_answers = set([*human_response, *llm_response])
      all_answers = list(all_answers)
      all_answers = [a for a in all_answers if a != '']
      all_answers = sorted(all_answers, key=int)

      print(f" mismatched")
      for answer in all_answers:
        msg = f'{answer:>2s}: '
        msg += 'h' if answer in human_response else '_'
        msg += ' '
        msg += 'l' if answer in llm_response else '_'
        msg += ': '
        msg += options[int(answer)]
        print(msg)
      print()

  print(f"{args.experiment}: Exactly matched {counts[0]:,} of {counts[1]:,} [{100.0 * counts[0] / counts[1]:.1f}%]")