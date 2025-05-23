import json
import sys
import os
import csv
import time
import re
import shutil
import platform
import subprocess

from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console

from .ollama import Ollama
from .utils import timestamp_str, pp
from .logging import logger
from .questions import build_question, build_prompt, load_hints, load_hints, make_full_questions, Question
from .dialog import Dialog
from .answers import get_legal_answer
from .cli import cli_log_args, cli_set_args, cli_get_args

def quiz_truncate(msg, max_len: int = 50) -> str:
    """
    Truncate msg (or its str() form) to at most max_len characters,
    appending "..." if it was longer.
    """
    text = str(msg)
    truncated = text[:max_len]
    if len(truncated) < len(text):
        truncated += "..."
    # the [ and \n are to prevent errors from rich
    truncated = truncated.replace('[', ' ').replace('\n', ' ')
    return truncated

def quiz_answers(dialog: Dialog) -> dict:
    questions = {}
    answers = 0
    for q in dialog.history:
        name = q['answer']['name']
        questions[name] = questions.get(name, {
            'name': name,
            'number': q['answer']['number'],
            'answer': None,
            'ok': False
        })
        if not q['answer']['ok']: continue
        questions[name]['answer'] = q['answer']['answer']
        answers += 1
    return [questions, answers]

def quiz_save(path: Path, dialog: Dialog, meta: dict) -> None:

    # the quiz dialog html
    root = Path(__file__).resolve().parent / "templates" / "dialog"
    shutil.copy(root / "index.html", path / 'index.html')
    shutil.copy(root / "styles.css", path / 'styles.css')
    shutil.copy(root / "scripts.js", path / 'scripts.js')
    with open(path / 'dialog.js', "w", encoding="utf-8") as f:
      f.write("document.quizzinator.dialog = ")
      json.dump(dialog.history, f, indent=2, sort_keys=True)
      f.write(';\n')

      f.write("document.quizzinator.meta = ")
      json.dump(meta, f, indent=2, sort_keys=True)
      f.write(';\n')
    # if we are on darwin, open this
    # if platform.system() == "Darwin": subprocess.run(["open", path / 'index.html'], check=True)

    # extract the questions summary
    questions, _ = quiz_answers(dialog)

    # the json for later
    with (path / 'cache.json').open('w',encoding='utf') as f: json.dump(dialog.cache, f, indent=4)
    with (path / 'history.json').open('w',encoding='utf') as f: json.dump(dialog.history, f, indent=4)
    with (path / 'questions.json').open('w',encoding='utf') as f: json.dump(questions, f, indent=4)

    # the file signal
    with (path / 'done').open('w',encoding='utf') as f: f.write('')

def quiz_run_one(index: int, total: int, questions: list[Question], cache: dict, model: str, timeout: float, verbose: bool, attempts: int) -> None:
    dialog = None
    i = 0
    while i < attempts:
        try:
            dialog = _quiz_run_one(index, total, questions, cache, model, timeout, verbose, attempts)
            if dialog is None:
                logger.warn(f'got no response from quiz -> retrying')
                continue

            # check how much is completed
            qs, successes = quiz_answers(dialog)
            if successes / len(qs) < 0.8:
                logger.warning(f'only had answers to {successes} of {len(qs)} -> retrying')
                i += 1
                continue

            # actually successful
            return dialog
        except TimeoutError:
            logger.error(f"Quiz #{index} timed out - reattempting {i} of {attempts - 1}" )
            i += 1
    return dialog

def _quiz_run_one(index: int, total: int, questions: list[Question], cache: dict, model: str, timeout: float, verbose: bool, attempts: int) -> None:
    """
    Run exactly one respondent through the survey:
      - Prints each raw prompt
      - Calls client.query()
      - Prints question name + extracted answer
      - Pretty-prints the full entry (sans 'think')
    """
    # get the questions to ask the LLM
    args = cli_get_args()
    todo = ['_Context'] + args.questions
    with (logger.progress(
        f"Quiz {index:,} of {args.n:,}",
        steps=len(todo),
        width=25,
        show_steps=False,
        silent = verbose
    ) as prog):
        div1 = '=' * 33
        div2 = '-' * 33
        dialog = Dialog(model=model, timeout=timeout, cache=cache)
        ret = []
        for i, name in enumerate(todo):
            qs = [q for q in questions if q.name == name]
            if len(qs) == 0:
                logger.critical(f"Illegal question {name} requested")
            if len(qs) > 1:
                logger.critical(f"question {name} appears multiple times in questions")
            q = qs[0]
            prompt = build_prompt(q)
            if verbose:
                #logger.info(div1)
                logger.info(f"[bold]Question #{i+1:,} of {len(todo):,}: {q.name}[/bold]")
                logger.info("  [bold magenta]Quizzinator[/bold magenta]:")
                msg = quiz_truncate(prompt)
                #print(['quiz_run_one, line 77', msg])
                logger.info(f'  [magenta]{msg}[/magenta]')

            # should iterate up to n times until we get an OK for entry
            current_prompt = prompt
            count = 0
            ok = False
            while count < attempts:
                t0 = time.time()
                user, llm = dialog.query(current_prompt)
                user['answer'] = {
                    'name': q.name,
                    'number': i,
                    'count': count,
                    'ok': False,
                    'answer': None,
                }
                ret.append(user)
                ok, answer = get_legal_answer(current_prompt, llm['content'], q.mode, [o.code for o in q.options])
                llm['answer'] = {
                    'name': q.name,
                    'number': i,
                    'count': count,
                    'ok': ok,
                    'answer': answer,
                }
                ret.append(llm)
                dt = int(time.time() - t0)

                # If we succeed on extracting a good answer, get out of this loop!
                if ok:
                    if verbose:
                        #logger.info(div2)
                        if type(answer) is list: answer = ','.join(answer)
                        msg = quiz_truncate(answer)
                        logger.info(f"  [bold green]LLM good answer after {dt:,} seconds[/bold green]")
                        logger.info(f"  [green]{msg}[/green]")
                    break

                # If we failed, then take care of logging that
                if verbose:
                    #logger.info(div2)
                    msg = quiz_truncate(llm['content'])
                    logger.info(f"  [bold red]LLM bad answer after {dt:,} seconds[/bold red]")
                    logger.info(f"  [red]{msg}[/red]")

                current_prompt = build_prompt(q, True)
                if verbose and count + 1 < attempts:
                    #logger.info(div2)
                    logger.info("  [bold magenta]Quizzinator REPEATS:[/bold magenta]")
                    msg = quiz_truncate(current_prompt)
                    logger.info(f"  [magenta]{msg}[/magenta]")
                    #logger.info(div2)
                count += 1

            prog.step(f"{'√' if ok else 'x'} question {q.name}")
        dialog.kill()
        return dialog

def quiz_todo(path: str, experiment: str, n: int, reset: bool) -> list[list[int, Path, bool]]:
    path_experiment = Path(os.path.join(path, 'experiments', experiment))
    path_experiment.mkdir(parents=True, exist_ok=True)

    path_quizzes = path_experiment / 'quizzes'
    path_quizzes.mkdir(parents=True, exist_ok=True)

    todo = [
        [i, path_quizzes / str(i), not (path_quizzes / str(i) / 'done').exists() or reset]
        for i in range(n)
    ]
    for t in todo:
        t[1].mkdir(parents=True, exist_ok=True)

    return todo

def quiz_done(path: str, experiment: str) -> list[tuple[int, Path, bool]]:
  path_experiment = Path(os.path.join(path, 'experiments', experiment))
  path_experiment.mkdir(parents=True, exist_ok=True)

  path_quizzes = path_experiment / 'quizzes'

  # Get all numerically named directories in path_quizzes that have a 'history.json' file
  done_quizzes = [(int(folder), path_quizzes / folder, (path_quizzes / folder / "history.json").exists())
                 for folder in os.listdir(path_quizzes)
                 if folder.isdigit() and os.path.isdir(path_quizzes / folder)]

  return done_quizzes
