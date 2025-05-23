import re
from dataclasses import dataclass
from typing import List, Optional

from .questions import Option, Question
# should move to questions
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
