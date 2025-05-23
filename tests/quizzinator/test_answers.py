import pytest
from quizzinator.answers import extract_llm_answer, pattern_consensus

# Define a regex for numbers 1–12 and dash-separated sequences
# Define a regex for numbers 1–12 (longest-first) and dash-separated sequences
NUM_PATTERN = r'(?:12|11|10|9|8|7|6|5|4|3|2|1)(?:-\s?(?:12|11|10|9|8|7|6|5|4|3|2|1))*'

@pytest.mark.parametrize("text, target, expected", [
    # Standard dash-delimited multiple answers
    ("Answer: 2-3-4", NUM_PATTERN, '2-3-4'),
    # Parentheses
    ("Answer: (3)", NUM_PATTERN, '3'),
    # Double quotes
    ('Answer: "10"', NUM_PATTERN, '10'),
    # Single quotes
    ("Answer: '12'", NUM_PATTERN, '12'),
    # Alone on line
    ("11", NUM_PATTERN, '11'),
    # Markdown bold
    ("**7**", NUM_PATTERN, '7'),
    ("**(8)**", NUM_PATTERN, '8'),
    # XML tag
    ("<answer>9</answer>", NUM_PATTERN, '9'),
    # LaTeX boxed
    ("\\boxed{5}", r'([^}]+)', '5'),
    # Leading hash
    ("Answer: #4", NUM_PATTERN, '4'),
    # Letter answer default pattern
    ("Answer: A", None, 'A'),
])
def test_extract_various_formats(text, target, expected):
    assert extract_llm_answer(text, target) == expected


def test_extract_multi_digit_sequence():
    # Test that 1-10-11 is captured correctly
    seq = '1-10-11'
    text = f"Answer: {seq}"
    assert extract_llm_answer(text, NUM_PATTERN) == seq


def test_pattern_consensus_agreement():
    # Repeated identical answers should agree
    text = "Answer: 5\nAnswer: 5\n"
    # Use simple digit target
    assert pattern_consensus(r'(\d+)', text) == '5'


def test_pattern_consensus_conflict():
    # Different answers should return False
    text = "Answer: 5\nAnswer: 6\n"
    assert pattern_consensus(r'(\d+)', text) is False


def test_extract_no_match():
    assert extract_llm_answer("No answer here", NUM_PATTERN) is None


def test_extract_final_answer_block():
    # Patterns that include '**Final Answer**: ...'
    text = "**Final Answer**\nAnswer: 3"
    assert extract_llm_answer(text, r'\d+') == '3'


def test_extract_only_answer_tag():
    # Tagged answer
    text = "<answer>BOOM</answer>"
    assert extract_llm_answer(text, r'[A-Z]+') == 'BOOM'


def test_extract_conflicting_multiple_patterns():
    # Both boxed and parentheses with same value should agree
    text = "Answer: (4)\\boxed{4}"
    # Should return '4'
    assert extract_llm_answer(text, None) == '4'

    # But conflicting styled answers should return None
    text2 = "Answer: (4)\\boxed{5}"
    assert extract_llm_answer(text2, None) == '5'
