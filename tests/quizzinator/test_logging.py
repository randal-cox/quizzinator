import re
import time
import pytest
from quizzinator.logging import Logger

# Helper to freeze and increment time.time()
class TimeIterator:
    def __init__(self, start: float = 0, step: float = 1):
        self.current = start
        self.step = step
    def __call__(self):
        t = self.current
        self.current += self.step
        return t

@pytest.fixture(autouse=True)
def freeze_time(monkeypatch):
    # Freeze time() to deterministic increments
    ti = TimeIterator(start=1600000000, step=1)
    monkeypatch.setattr(time, 'time', ti)
    yield

# Utility to strip ANSI escape sequences from Rich
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def clean_output(raw: str) -> list[str]:
    return [ANSI_RE.sub('', line) for line in raw.splitlines()]

# ----------------------- Tests -----------------------

def test_format_and_info_output(capsys):
    logger = Logger()
    logger.info("Hello World")
    raw = capsys.readouterr().out
    lines = clean_output(raw)
    assert len(lines) == 1
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| INFO\s+\| Hello World", lines[0])


def test_warning_and_error_output(capsys):
    logger = Logger()
    logger.warning("Watch out")
    logger.error("Something bad")
    raw = capsys.readouterr().out
    lines = clean_output(raw)
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| WARNING\s+\| Watch out", lines[0])
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ERROR\s+\| Something bad", lines[1])


def test_section_without_timer(capsys):
    logger = Logger(indent_step=4)
    with logger.section("TestSec", timer=False):
        logger.info("Inside")
    raw = capsys.readouterr().out
    lines = clean_output(raw)
    # Header and footer lines contain bold names stripped
    assert any("TestSec" in line for line in lines)
    # Inside line indented
    inside = [l for l in lines if "Inside" in l][0]
    assert re.search(r"\| INFO\s+\|\s{4,}Inside", inside), f"Unexpected indentation in: {inside}"


def test_section_with_timer(capsys):
    logger = Logger(indent_step=2)
    with logger.section("SecT", timer=True):
        logger.info("Step1")
        time.sleep(0)
    raw = capsys.readouterr().out
    lines = clean_output(raw)
    # Footer includes completed in 0:0X
    footer = lines[-1]
    assert re.search(r"SecT completed in 0:0\d", footer)


def test_progress_with_steps(capsys):
    steps = 3
    width = 6
    logger = Logger(indent_step=3)
    with logger.progress("Prog", steps=steps, width=width) as prog:
        for i in range(steps):
            prog.step(f"msg{i}")
    raw = capsys.readouterr().out
    lines = clean_output(raw)
    # Check header
    assert any("Prog started" in l for l in lines)
    # Check bars
    bar_lines = [l for l in lines if "Step" in l and "|" in l]
    assert len(bar_lines) == steps
    # Footer
    assert any("Prog completed in" in l for l in lines)


def test_progress_no_steps(capsys):
    logger = Logger()
    with logger.progress("NoSteps", steps=None) as prog:
        prog.step("first")
        prog.step("second")
    lines = clean_output(capsys.readouterr().out)
    # Should have step logs without bars
    assert any("Step 1 | first" in l for l in lines)
    assert any("Step 2 | second" in l for l in lines)
    # Footer
    assert any("NoSteps completed in" in l for l in lines)
