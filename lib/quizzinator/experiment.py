import argparse, sys, os, time, shutil, csv, json, datetime
from zipfile import ZipFile

from collections import OrderedDict
from pathlib import Path

import pandas as pd

from .logging import logger
from .utils import pp, timestamp_str
from .cli import cli_log_args, cli_set_args, cli_get_args

from .parser import parse_questions
from .questions import load_hints, load_hints, make_full_questions, parse_questions
from .quiz import quiz_todo, quiz_run_one, quiz_save, quiz_done

def experiment_cli_args():
  p = argparse.ArgumentParser(
    prog="experiment",
    description="Run LLM-based survey simulations"
  )
  p.add_argument(
    "dir",
    help="Path to survey directory"
  )
  p.add_argument(
    "--experiment",
    type=str,
    default="generic",
    help="The name of the experiment to generate"
  )
  p.add_argument(
    '--hints',
    type=str,
    default="",
    help="Add the names of questions that the LLM should know the answers to ahead of time, separated by commas"
  )
  p.add_argument(
    '--questions',
    type=str,
    default="",
    help="Add the names of questions that are asked, separated by commas [def = all questions]"
  )
  p.add_argument(
    "--timeout",
    type=int,
    default=60,
    help="Seconds before we timeout responses from the LLM"
  )
  p.add_argument(
    "--n",
    type=int,
    default=0,
    help="Number of respondents. 0 for match to hints.csv"
  )
  p.add_argument(
    "--attempts",
    type=int,
    default=2,
    help="How many times we will ask the question before giving up"
  )
  p.add_argument(
    "-m", "--model",
    default="",
    help="Ollama model name to use, like deepseek-r1:1.5b"
  )
  p.add_argument(
    '--from-hints',
    action='store_true',
    help='If set, just create data from the hints file, not from LLM queries'
  )
  p.add_argument(
    '--skip-identity',
    action='store_true',
    help='If set, do not inform the LLM about identity questions'
  )
  p.add_argument(
    '--skip-setup',
    action='store_true',
    help='If set, do not show inform the LLM about the context of the survey'
  )
  p.add_argument(
    '-v', '--verbose',
    action='store_true',
    help='Show dialog as it happens'
  )
  p.add_argument(
    '-r', '--reset',
    action='store_true',
    help='If set, recompute'
  )
  p.add_argument(
    '--use-cache',
    action='store_true',
    help='If set, load from cache instead of querying the LLM'
  )
  return p.parse_args()

def experiment_cli_get_n() -> int:
  args = cli_get_args()

  if args.n != 0: return args.n

  path_dir = Path(args.dir)
  path_hints = path_dir / 'hints.csv'
  hints_length = 0
  if path_hints.is_file():
    with open(path_hints, encoding='utf-8') as f:
      hints_length = len(f.readlines())
  ret = args.n
  if ret < 1 and hints_length > 0:
    ret = hints_length
    logger.warning(f"Changed n to {ret} to match the hints file")
  if ret < 1:
    ret = 25
    logger.warning(f"Changed n to {ret} as a default")
  return ret

def experiment_cli_get_reset():
  """Update reset if --use-cache is invoked"""
  args = cli_get_args()

  if not args.use_cache or args.reset: return
  args.reset = True
  logger.warn("--use-cache implies reset=True")

def experiment_run_csv(quiz_dir, csv_file_path):
  csv_data = []

  # Iterating over each folder in quiz_dir
  folders = [folder for folder in os.listdir(quiz_dir) if
           folder.isdigit() and os.path.isdir(os.path.join(quiz_dir, folder))]
  for folder in sorted(folders, key=int):
    json_file_path = os.path.join(quiz_dir, folder, "questions.json")

    # Verifying that json_file_path is an existing file
    if not os.path.isfile(json_file_path):
      continue

    with open(json_file_path, 'r') as file:
      data = json.load(file)

    row_data = OrderedDict({"number": folder})

    for key, value in data.items():
      row_data[key] = value['answer']

    csv_data.append(row_data)

  keys = csv_data[0].keys()
  with open(csv_file_path, 'w', newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(csv_data)

def experiment_run():
  """Actually run the LLM-based quizzes"""
  args = cli_get_args()
  args.dir = Path(args.dir)
  todo = quiz_todo(args.dir, args.experiment, args.n, args.reset)
  todo = [t for t in todo if t[-1]]
  with logger.section(f"Running {args.dir}/experiments/{args.experiment}", timer=False):
    with logger.progress("Administering quizzes", steps=len(todo)) as prog:
      for index, path_quiz, _ in todo:
        questions, hint_answer = make_full_questions(args.dir, args.hints, index, args.skip_identity, args.skip_setup)
        path_cache = path_quiz / "cache.json"
        cache = None
        if path_cache.exists() and args.use_cache:
          with path_cache.open("r", encoding='utf-8') as f:
            logger.info("Using a cache")
            cache = json.load(f)

        now = timestamp_str()
        t0 = time.time()
        dialog = quiz_run_one(index, len(todo), hint_answer, questions, cache, args.model, args.timeout, args.verbose, args.attempts)
        if not dialog:
          prog.step(f"Failed for quiz #{index}", "ERROR")
          continue
        dt = time.time() - t0
        meta = {
          'index': index,
          'size': args.n,
          'duration': dt,
          'start': now,
          'model': args.model,
        }
        quiz_save(path_quiz, dialog, meta)
        prog.step(f"Finished quiz #{index + 1:,}")
  experiment_run_post_meta()
  experiment_run_post_csv()
  experiment_run_post_quizzes()

def experiment_run_post_meta():
  args = cli_get_args()

  # update the meta
  path_meta = experiment_path_meta()

  # Read existing meta.json or use an empty dictionary if the file does not exist
  meta = {}
  if path_meta.exists():
    with open(path_meta, 'r') as f:
      meta = json.load(f)

  # upodate with data on the start and end times
  done_quizzes = quiz_done(args.dir, args.experiment)
  start_times = []
  end_times = []
  for _, path_quiz, done in done_quizzes:
    if done:
      with open(path_quiz / 'history.json', 'r') as f:
        history_list = json.load(f)
        for history in history_list:
          start = history['start']
          elapsed = history['elapsed']
          start_times.append(start)
          end_times.append(start + elapsed)
  # Save start and end times to the existing meta dictionary and save it to meta.json
  meta['start'] = min(start_times) if start_times else 'N/A'
  meta['end'] = max(end_times) if end_times else 'N/A'
  path_meta = experiment_path_meta()
  with open(path_meta, 'w') as f:
    json.dump(meta, f, indent=4)

def experiment_run_post_csv():
  """save the csv file"""
  args = cli_get_args()
  path_quizzes = args.dir / 'experiments' / args.experiment / 'quizzes'
  path_csv = args.dir / 'experiments' / args.experiment / 'data.csv'
  experiment_run_csv( path_quizzes, path_csv)

def experiment_run_post_quizzes():
  """save the quiz html inside the info/quizzes dir"""
  args = cli_get_args()
  args_dir = Path(os.path.abspath(args.dir))

  path_quizzes = args_dir / 'experiments' / args.experiment / 'quizzes'
  path_info_quizzes = args_dir / 'html' / args.experiment / 'quizzes'
  path_info_quizzes.mkdir(parents=True, exist_ok=True)  # make directory, ignore if it already exists
  for child in path_quizzes.iterdir():
    if not child.is_dir(): continue
    bn = os.path.basename(child)
    if not bn.isdigit(): continue
    # where to save the files
    dst_dir = path_info_quizzes / bn  # create equivalent directory in path_info_quizzes
    dst_dir.mkdir(parents=True, exist_ok=True)  # make directory, ignore if it already exists
    for file in child.glob('*'):  # go through all files in folder
      if file.suffix in ['.js', '.html', '.css']:  # if file ends with '.js', '.html', or '.css'
        # print(file)
        # print("===> " + str(dst_dir))
        # print()
        shutil.copy2(file, dst_dir)  # copy the file


def experiment_from_hints():
  """Create an experiment folder based on the hints file"""
  args = cli_get_args()

  src = Path(args.dir) / 'hints.csv'
  dst = Path(args.dir) / 'experiments' / args.experiment / 'data.csv'
  if not args.reset and os.path.exists(dst): return

  # Read existing meta.json
  meta = {}
  path_meta = experiment_path_meta()
  if path_meta.exists():
    with open(path_meta, 'r') as f:
      meta = json.load(f)

  meta['start'] = time.time()
  df = pd.read_csv(src)
  if args.n: df = df.sample(n=args.n)
  df.to_csv(dst, index=False)
  meta['end'] = time.time()

  # save the meta
  with open(experiment_path_meta(), 'w') as f:
    json.dump(meta, f, indent=4)

def copytree(source_dir, target_dir, ignore=None):
  """shutil.copytree freaks if the target is already there, so we had to reinvent the wheel"""
  for name in os.listdir(source_dir):
    if ignore and name in ignore:
      continue

    source = Path(source_dir) / name
    target = Path(target_dir) / name

    if source.is_dir():
      target.mkdir(exist_ok=True)
      copytree(str(source), str(target), ignore)
    else:
      shutil.copy2(str(source), str(target))

def experiment_html(dir_path):
  args = cli_get_args()

  # Copy the templates/experiment files
  source_dir = Path(__file__).parent / "templates" / "experiment"
  target_dir = Path(args.dir) / "html" / args.experiment
  if not os.path.exists(target_dir):
    target_dir.mkdir(exist_ok=True)

  copytree(source_dir, target_dir, ["quizzes"])

  # Read the csv data
  csv_path = Path(dir_path) / "data.csv"
  csv_data = []
  with open(csv_path) as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
      csv_data.append(row)

  # Generate meta
  with open(dir_path / "meta.json") as meta_file:
    meta = json.load(meta_file)
  meta['project'] = str(args.dir)
  meta['name'] = dir_path.name
  meta['size'] = len(csv_data)
  meta['from_hints'] = args.from_hints


  # need to include document.quizzinator.hints
  hints = {}
  q_test = {}
  for q in parse_questions(Path(args.dir) / 'questions.txt'):
    h = hints[q.name] = hints.get(q.name, {})
    q_test[q.name] = q.prompt_text
    for o in q.options:
      h[o.code] = o.text

  # Generate data.js
  data_js = {
    "quizzinator": {
      "quizData": csv_data,
      "meta": meta,
      "hints": hints,
      "questions": q_test,
    }
  }

  # also the text of the question

  data_js_path = target_dir / "data.js"
  with open(data_js_path, "w") as data_js_file:
    data_js_file.write("window.document = window.document || {};\n")
    data_js_file.write("window.document.quizzinator = window.document.quizzinator || {};\n")

    data_js_file.write("document.quizzinator.quizData = ")
    json.dump(data_js["quizzinator"]["quizData"], data_js_file, indent=4)

    data_js_file.write(";\ndocument.quizzinator.meta = ")
    json.dump(data_js["quizzinator"]["meta"], data_js_file, indent=4)
    data_js_file.write(";")

    data_js_file.write(";\ndocument.quizzinator.hints = ")
    json.dump(hints, data_js_file, indent=4)
    data_js_file.write(";")

    data_js_file.write(";\ndocument.quizzinator.qtext = ")
    json.dump(q_test, data_js_file, indent=4)
    data_js_file.write(";")

  # generate data.json - drop all the js stuff
  data_json_path = target_dir / "data.json"
  data = {
    'meta': meta,
    'responses': csv_data,
    "hints": hints,
    "questions": q_test,
  }
  with open(data_json_path, "w") as f:
    json.dump(data, f, indent=4)


def experiment_check():
  """Check that the required files and directories are present"""
  args = cli_get_args()
  root = Path(args.dir)
  src_hints = root / 'hints.csv'
  if not os.path.exists(src_hints):
    logger.critical(f"Couldn't find hints file: {src_hints} - this should be a csv file with columns seen in questions.txt")
  src_questions = root / 'questions.txt'
  if not os.path.exists(src_questions):
    logger.critical(f"Couldn't find questions file: {src_questions} - this should formatted as described in README.md")
  src_setup = root / 'setup'
  if not os.path.isdir(src_setup):
    logger.critical(f"Couldn't find questions dir: {src_setup} - need a setup dir")
  for n in ['answers', 'consent', 'human', 'identity']:
    src = src_setup / (n + '.txt')
    if not os.path.exists(src_setup):
      logger.critical(f"Couldn't find file: {src} - needed in setup dir, see README.md for details")

  # make sure we have directories used by this code for output
  os.makedirs(root / 'experiments', exist_ok=True)
  os.makedirs(root / 'experiments' / args.experiment, exist_ok=True)
  os.makedirs(root / 'html', exist_ok=True)

def experiment_pre_meta():
  """reconcile any meta json file with the current arguments"""

  args = cli_get_args()
  path_meta = experiment_path_meta()

  # Read existing meta.json or use an empty dictionary if the file does not exist
  meta = {}
  if path_meta.exists():
    with open(path_meta, 'r') as f:
      meta = json.load(f)

  # look for conflicts between a saved entry and the current command-line arguments
  if 'hints' in meta and args.hints and meta['hints'] != args.hints:
    pp(meta)
    print(path_meta)
    logger.critical(f"Command line arguments don't match meta for 'hints': {args.hints} vs {meta['hints']}")

  if 'model' in meta and args.model and meta['model'] != args.model:
    logger.critical(f"Command line arguments don't match meta for 'model': {args.model} vs {meta['model']}")
  if 'questions' in meta and args.questions and meta['questions'] != args.questions:
    logger.critical(f"Command line arguments don't match meta for 'questions': {args.questions} vs {meta['questions']}")

  # Save input arguments to meta.json
  meta['hints'] = args.hints
  meta['model'] = args.model
  meta['questions'] = args.questions

  if not meta['model'] and not args.from_hints:
    logger.critical("Specify a model like deepseek-r1:1.5b")

  if not meta['questions']:
    # ask all the questions!
    qs = parse_questions(Path(args.dir) / 'questions.txt')
    meta['questions'] = [q.name for q in qs]
    logger.warning("Adding all questions to the list of those asked")

  # finally save the meta information
  with open(path_meta, 'w') as f: json.dump(meta, f, indent=4)
  return meta


def experiment_path_meta():
  args = cli_get_args()
  return Path(args.dir) / 'experiments' / args.experiment / 'meta.json'

def experiment_package(path, name):
  # Store the original name and the parent directory
  original_name = os.path.basename(path)
  parent_directory = os.path.dirname(path)

  # Rename the directory
  new_path = os.path.join(parent_directory, name)
  os.rename(path, new_path)

  # Zip the renamed directory
  shutil.make_archive(new_path, 'zip', new_path)

  # Rename the directory back to the original name
  os.rename(new_path, path)
  logger.info(f"Packaged at {new_path}.zip")
def experiment_main():
  args = experiment_cli_args()
  args.hints = args.hints.split(',')
  if args.hints == ['']: args.hints = []
  args.questions = args.questions.split(',')
  if args.questions == ['']: args.questions = []

  cli_set_args(args)
  cli_log_args(args)

  # Handle some changes to the command-line args
  experiment_cli_get_n()
  experiment_cli_get_reset()

  # make sure the directory structure is OK
  experiment_check()

  meta = experiment_pre_meta()

  # then backfill the actual data
  # fill in the experiment template

  # Remove the "info" directory if it exists
  target_dir = Path(args.dir) / "html" / args.experiment
  if target_dir.exists() and target_dir.is_dir():
    shutil.rmtree(target_dir)

  if args.from_hints:
    # create the results from the hints
    meta['start'] = time.time()
    experiment_from_hints()
    meta['end'] = time.time()
    with open(experiment_path_meta(), 'w') as f:
      json.dump(meta, f, indent=4)
    # note this goes AFTER for from_hints
    experiment_html(Path(args.dir) / 'experiments' / args.experiment)
  else:
    # note this goes BEFORE for not from_hints
    experiment_run()
    experiment_html(Path(args.dir) / 'experiments' / args.experiment)
  # make sure we copy the data.csv file into info
  shutil.copy(
    Path(args.dir) / "experiments" / args.experiment / 'data.csv',
    target_dir / 'data.csv',
  )

  # make html/data.json
  # Temporary dictionary to hold all our data
  path_html = Path(args.dir) / "html"
  dict_data = {}

  # Traverse all directories under `path_html`
  for root, dirs, files in os.walk(path_html):
    for file in files:
      # Process all `data.json` files
      if file == 'data.json':
        name = os.path.basename(root)  # Get the name of the base directory
        with open(os.path.join(root, file), 'r') as f:
          dict_data[name] = json.load(f)

  # Write dictionary to `data.js` file
  with open(path_html / 'data.js', 'w') as f:
    f.write('document.quizzinator.data = ' + json.dumps(dict_data, indent=4) + ';')

  # TODO: copy to html from templates folder
  #  index.html
  #  script.js
  #  styles.css