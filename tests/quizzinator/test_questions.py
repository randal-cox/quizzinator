import pytest
from pathlib import Path
import shutil

# Imports from the questions module
from quizzinator.questions import (
    parse_questions,
    Question,
    Option,
    load_hints,
    build_question,
    build_prompt,
    make_full_questions
)

# Paths to test data files
TEST_DIR = Path(__file__).parent
TEST_CSV = TEST_DIR / 'test_questions' / 'hints.csv'
TEST_TXT = TEST_DIR / 'test_questions' / 'questions.txt'

# Columns for hint generation
COLUMNS = ('PuPSafeword', 'PuPNegotiation')

# ----------------------------------
# Tests for parse_questions
# ----------------------------------

def test_parse_questions_happy_path():
    questions = parse_questions(str(TEST_TXT))
    assert isinstance(questions, list)
    assert len(questions) == 4

    names = [q.name for q in questions]
    assert names == ["PuPSafeword", "PuPNegotiation", "Gender", "SexualOrientation"]

    q1 = questions[0]
    assert q1.name == "PuPSafeword"
    assert q1.multi is False
    assert q1.mode == "single"
    assert [opt.code for opt in q1.options] == [1, 2, 3, 4, 5]
    assert not any(opt.is_other for opt in q1.options)

    q3 = questions[2]
    assert q3.name == "Gender"
    assert q3.multi is True
    assert q3.mode == "multi"
    assert q3.options[-1].is_other is True


def test_parse_questions_skips_blocks_without_name(tmp_path):
    content = (
        "Some intro text\n"
        "---\n"
        "N: X\n"
        "Question text?\n"
        "A1: Yes\n"
        "A2: No\n"
    )
    qfile = tmp_path / "q2.txt"
    qfile.write_text(content, encoding="utf-8")
    questions = parse_questions(str(qfile))
    assert len(questions) == 1
    assert questions[0].name == "X"
    assert questions[0].mode == "single"


def test_empty_file(tmp_path):
    qfile = tmp_path / "empty.txt"
    qfile.write_text("", encoding="utf-8")
    assert parse_questions(str(qfile)) == []

# ----------------------------------
# Tests for load_hints
# ----------------------------------

def test_load_hints_returns_correct_number_of_hints():
    hints = load_hints(str(TEST_CSV), str(TEST_TXT), COLUMNS)
    assert isinstance(hints, list)
    assert len(hints) == 17


def test_load_hints_contains_question_prompts_and_answers():
    hints = load_hints(str(TEST_CSV), str(TEST_TXT), COLUMNS)
    questions_map = {q.name: q for q in parse_questions(str(TEST_TXT))}

    for hint in hints:
        assert "To give you a sense" in hint, "Missing intro text"
        for col in COLUMNS:
            q = questions_map[col]
            assert f"Question: {q.prompt_text}" in hint
            assert any(f"({opt.code}):" in hint for opt in q.options), f"No answer for {col}"
        assert '-----' in hint


def test_load_hints_specific_answers_present():
    hints = load_hints(str(TEST_CSV), str(TEST_TXT), COLUMNS)
    first_hint = hints[0]
    assert '(5): Extremely important' in first_hint
    assert '(5): Completely negotiated' in first_hint


def test_load_hints_handles_no_answer(tmp_path):
    tmp_csv = tmp_path / 'hints.csv'
    lines = TEST_CSV.read_text().splitlines()
    header = lines[0].split(',')
    idx = header.index('PuPNegotiation')
    row = lines[1].split(',')
    row[idx] = ''
    lines[1] = ','.join(row)
    tmp_csv.write_text("\n".join(lines), encoding='utf-8')

    hints = load_hints(str(tmp_csv), str(TEST_TXT), COLUMNS)
    assert 'You did not answer' in hints[0]

# ----------------------------------
# Tests for build_question and build_prompt
# ----------------------------------

def test_build_question_ordering():
    opts = [Option(2, 'Second'), Option(1, 'First'), Option(3, 'Third')]
    q = Question(name='Q', prompt_text='Prompt?', options=opts, multi=False, mode='single')
    lines = build_question(q)
    assert lines[0] == 'Prompt?'
    assert lines[1] == ''
    assert lines[2:] == ['(1) First', '(2) Second', '(3) Third']

def test_build_prompt_free_mode():
    opts = [Option(1, 'Only')]
    q = Question(name='Q', prompt_text='Free?', options=opts, multi=False, mode='free')
    prompt = build_prompt(q)
    # Ensure free mode prompt equals the joined question lines
    assert prompt.strip() == "\n".join(build_question(q)).strip()

@ pytest.mark.parametrize('mode, contains', [
    ('number', 'Answer with a number.'),
    ('word', 'Answer with a single word.'),
    ('line', 'Answer with a single line.'),
    ('date', 'Answer with a single date.'),
])
def test_build_prompt_modes(mode, contains):
    opts = [Option(1, 'Opt')]
    q = Question(name='Q', prompt_text='P?', options=opts, multi=False, mode=mode)
    output = build_prompt(q)
    assert contains in output


def test_build_prompt_multi_vs_single():
    opts = [Option(1,'A'), Option(2,'B')]
    q_multi = Question(name='Q', prompt_text='M?', options=opts, multi=True, mode='multi')
    multi_output = build_prompt(q_multi)
    assert 'select more than one answer' in multi_output

    q_single = Question(name='Q', prompt_text='S?', options=opts, multi=False, mode='single')
    single_output = build_prompt(q_single)
    assert 'Select only one answer' in single_output


def test_build_prompt_redo_prefix():
    opts = [Option(1,'A')]
    q = Question(name='Q', prompt_text='R?', options=opts, multi=False, mode='single')
    out = build_prompt(q, redo=True)
    assert out.startswith('I am having trouble figuring out')
    assert 'R?' in out

# ----------------------------------
# Tests for make_full_questions
# ----------------------------------

def create_test_survey_dir(tmp_path, include_hints: bool):
    # Locate the “test_questions” folder next to this test file
    src_dir = Path(__file__).parent / "test_questions"

    # Copy into a new subfolder (so copytree has a clean target)
    dest_dir = tmp_path / "setup"
    shutil.copytree(src_dir, dest_dir)

    # Optionally remove hints.csv
    if not include_hints:
        hints_path = dest_dir / "hints.csv"
        if hints_path.exists():
            hints_path.unlink()

    return str(dest_dir)


def test_make_full_questions_with_hints(tmp_path):
    survey_path = create_test_survey_dir(tmp_path, include_hints=True)
    # non-empty hints triggers identity.txt and a foreshadowing intro
    qs = make_full_questions(survey_path, hints=['x'], index=0)
    # Should have identity, hints intro, setup, plus parsed questions
    assert len(qs) == 4, f"Expected 4 items, got {len(qs)}"
    # First question is identity text
    assert qs[0].prompt_text.startswith('Pretend you')
    # Remaining are parsed questions in order
    names = [q.name for q in qs]
    assert names == ["PuPSafeword", "PuPNegotiation", "Gender", "SexualOrientation"]
def test_make_full_questions_without_hints(tmp_path):
    survey_path = create_test_survey_dir(tmp_path, include_hints=False)
    # empty hints triggers identity and generic intros
    qs = make_full_questions(survey_path, hints=[], index=0)
    assert len(qs) == 4, f"Expected 4 items, got {len(qs)}"
    # First question is identity.txt
    assert qs[0].prompt_text.startswith('Pretend you')
    # Remaining are parsed questions in order
    names = [q.name for q in qs]
    assert names == ["PuPSafeword", "PuPNegotiation", "Gender", "SexualOrientation"]

def test_build_question_ordering():
    opts = [Option(2, 'Second'), Option(1, 'First'), Option(3, 'Third')]
    q = Question(name='Q', prompt_text='Prompt?', options=opts, multi=False, mode='single')
    lines = build_question(q)
    assert lines[0] == 'Prompt?'
    assert lines[1] == ''
    assert lines[2:] == ['(1) First\n', '(2) Second\n', '(3) Third\n']

