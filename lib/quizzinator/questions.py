import re
import os
import csv

from dataclasses import dataclass
from typing import List, Optional, Tuple
from functools import lru_cache

from .utils import pp
from .logging import logger
from .cli import cli_log_args, cli_set_args, cli_get_args

@dataclass
class Option:
    code: int
    text: str
    is_other: bool = False

@dataclass
class Question:
    name: str
    prompt_text: str
    options: List[Option]
    multi: bool
    mode: str

@lru_cache
def parse_questions(path: str) -> List[Question]:
    """
    Read questions.txt, split on '---', and build Question objects.
    """
    with open(path, encoding="utf-8") as f:
        raw = f.read().split("\n---\n")
    questions = []
    for block in raw:
        lines = block.strip().splitlines()
        free = []
        name = None
        opts = []
        multi = False
        mode = 'free'
        for line in lines:
            if line.startswith('N:'):
                name = line.split("N:",1)[1].strip()
            elif line.startswith("A:"):
                mode = line.split("A:", 1)[1].strip()
            elif re.match(r"[AM]\d+:", line):
                kind, rest = line.split(":",1)
                if kind.startswith("M"): multi = True
                opts.append(
                    Option(
                        code=int(re.findall(r"\d+", kind)[0]),
                        text=rest.strip(),
                        is_other="Other" in rest
                    )
                )
            else:
                if ':' in line:
                    print(['line is free', line, line[0], line[1]])
                free.append(line)
        if not name: continue

        # compute the mode
        if len(opts) == 0:
            pass
        elif multi:
            mode = 'multi'
        else:
            mode = 'single'


        prompt = "\n".join(free)
        questions.append(Question(name=name,
                                  prompt_text=prompt,
                                  options=opts,
                                  multi=multi,
                                  mode=mode
                                  ))
    return questions

@lru_cache(maxsize=None)
def load_hints(
    path_responses: str,
    path_questions: str,
    columns: Tuple[str, ...]
) -> List[str]:
    """
    Internal helper for load_hints that accepts a tuple of columns for caching.
    """
    # Load human responses for the specified columns
    humans: List[dict[str, str]] = []
    with open(path_responses, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            humans.append({col: row.get(col, '').strip() for col in columns})

    # Parse questions and filter to only those in columns
    questions: List[Question] = [
        q for q in parse_questions(path_questions)
        if q.name in columns
    ]

    hints: List[str] = []
    for human in humans:
        lines: List[str] = [
            '=' * 100 + "\n"
            "To give you a sense of who you are, in the past you have answered some demographics questions like this:\n"
        ]

        for question in questions:
            lines.append(f"Question: {question.prompt_text}\n")
            answer = human.get(question.name, '')
            for option in question.options:
                lines.append(f"  ({option.code}): {option.text}\n")
            if not question.options:
                # Free-text question
                lines.append(f"Your answer: {answer or 'No answer'}\n")
            else:
                if not answer:
                    lines.append("You did not answer\n")
                else:
                    codes = [a.strip() for a in answer.split(',')]
                    responses: List[str] = []
                    for code in codes:
                        opt = next((o for o in question.options if str(o.code) == code), None)
                        if opt:
                            responses.append(f"({opt.code}): {opt.text}\n")
                        else:
                            responses.append(code)

                    if len(responses) > 1:
                        lines.append(f"You answered {','.join(responses)}\n")
                    else:
                        lines.append(f"You answered {responses[0]}")

            # Separator between questions
            lines.append('-' * 100 + "\n\n")

        # Remove trailing separator
        if lines and lines[-1].startswith('-'):
            lines.pop()

        lines.append('=' * 100 + "\n")
        lines.append(
            "When I ask you questions like the above, you should answer in similar ways, because "
            "this reflects who you are. You are the person who would answer the above questions "
            "like this. You should reflect that when answering similar questions."
        )
        lines.append('\n\n')

        hints.append("\n".join(lines))

    return hints

def build_question(question):
    """
    Given a Question and the setup text, build the full prompt string.
    """

    lines = [question.prompt_text, ""]
    for opt in sorted(question.options, key=lambda o: o.code):
        lines.append(f"({opt.code}) {opt.text}\n")
    return lines

def build_prompt(question, redo=False):
    """
    Given a question and the setup text, build the full prompt string.
    """
    lines = build_question(question)
    lines.append("\n\n")

    if question.mode == 'free':
        pass
    elif question.mode == 'number':
        lines.append(
            "Answer with a number. To make sure I am getting your final answer correct, "
            "say something like 'Answer: #' "
            "where # is the number you'd like to indicate."
        )
    elif question.mode == 'word':
        lines.append(
            "Answer with a single word. To make sure I am getting your final answer correct, "
            "say something like 'Answer: WORD' "
            "where WORD is the answer you'd like to give."
        )
    elif question.mode == 'line':
        lines.append(
            "Answer with a single line. To make sure I am getting your final answer correct, "
            "say something like 'Answer: RESPONSE' "
            "where RESPONSE is the answer you'd like to give"
        )
    elif question.mode == 'date':
        lines.append(
            "Answer with a single date. To make sure I am getting your final answer correct, "
            "say something like 'Answer: DATE' "
            "where DATE is the answer you'd like to give. Make DATE in the form YYY-MM-DD"
        )
    elif question.multi:
        lines.append(
            "To make sure I am getting your final answer correct, say something like 'Answer: X' "
            "where X is your choice or choices from the list. You can select one or more answers "
            "from the list but limit it to just the answers you think are important. If you need "
            "to select more than one answer, separate them by dashes (e.g., Answer: 20-31-57)"
        )
    else:
        lines.append(
            "To make sure I am getting your final answer correct, say something like 'Answer: X' "
            "where X is what you the choice you have made. Select only one answer. Just type the "
            "number you want to select."
        )

    if redo:
        lines.insert(
            0,
            (
                'I am having trouble figuring out which of the options you meant. '
                'Could you please try again, selecting from the values given so that '
                'I can better figure out which one you mean. Again, it works best if you '
                'say something like "Answer: X". Thanks, that will help me understand you!'
            ) + '\n\n'
        )
    return "\n".join(lines)

def make_full_questions(
    dir: str,
    hints: list[str],
    index: int,  # which quiz number we are on
    skip_identity: bool = False,
    skip_setup: bool = False
):
    # locate files
    qfile = os.path.join(dir, "questions.txt")


    # create the intial 'question' that just gives the LLM context
    q0 = []
    if not skip_identity:
        # you are a human taking a test
        q0.append(open(os.path.join(dir, "setup", "human.txt"), encoding="utf-8").read())

        # you are a human with randomly identity features or ones matched up to our hints file
        prompt = open(os.path.join(dir, "setup", "identity.txt"), encoding="utf-8").read()
        if len(hints) > 0:
            hints = load_hints(
                os.path.join(dir, "hints.csv"),
                os.path.join(dir, "questions.txt"),
                columns=tuple(hints)
            )
            prompt = hints[index % len(hints)]
        q0.append(prompt)

        # don't make up questions
        prompt = open(os.path.join(dir, "setup", "answers.txt"), encoding="utf-8").read()
        q0.append(prompt)


    if not skip_setup:
        prompt = open(os.path.join(dir, "setup", "consent.txt"), encoding="utf-8").read()
        q0.append(prompt)

    # put the context inside the first question - this is an effeciency thing
    q0 = "\n".join(q0) + ("\n====================\n\n")
    questions = parse_questions(qfile)
    questions[0].prompt_text = q0 + questions[0].prompt_text
    return questions
