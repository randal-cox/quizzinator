# import pytest
# from pathlib import Path
# from quizinator.parser import parse_questions, Question, Option
#
# @ pytest.fixture
#
# def sections():
#     path = Path(__file__).parent / "test_parser.txt"
#     return parse_questions(str(path))
#
#
# def test_total_questions_count(sections):
#     # Expect exactly 55 questions parsed
#     assert len(sections) == 55, f"Got {len(sections)} sections, expected 55"
#
#
# def test_first_question_structure(sections):
#     q = sections[0]
#     assert isinstance(q, Question)
#     assert q.name == "PuPSafeword"
#     # Prompt should include Q: prefix
#     assert q.prompt_text.startswith("Q: How important is it to explicitly establish a safe word")
#     # Should have 5 options A1..A5
#     assert len(q.options) == 5
#     # Check first and last option
#     first_opt = q.options[0]
#     last_opt = q.options[-1]
#     assert isinstance(first_opt, Option)
#     assert first_opt.code == 1
#     assert first_opt.text == "Not important at all"
#     assert not first_opt.is_other
#     assert last_opt.code == 5
#     assert last_opt.text == "Extremely important"
#
#
# def test_mid_question_options_and_flags(sections):
#     # PuPBottomRemove is the 5th question
#     q = sections[4]
#     assert q.name == "PuPBottomRemove"
#     assert "ask to remove activities" in q.prompt_text
#     # Should have 7 options A1..A7
#     assert len(q.options) == 7
#     # multi should remain False (no M prefix)
#     assert q.multi is False
#
#
# def test_gender_question_multi_and_other(sections):
#     # Gender is a multi-select question with code M1..M12
#     q = next(s for s in sections if s.name == "Gender")
#     assert q.multi is True
#     # Should have 12 options
#     assert len(q.options) == 12
#     # Option 12 should be marked as 'other'
#     opt12 = next(o for o in q.options if o.code == 12)
#     assert opt12.is_other is True
#     assert "Other" in opt12.text
#
#
# def test_usornot_and_final_free_text(sections):
#     # USorNot should have no options
#     us = next(s for s in sections if s.name == "USorNot")
#     assert us.options == []
#     assert us.multi is False
#     # FinalThoughts should also be free-text
#     final = sections[-1]
#     assert final.name == "FinalThoughts"
#     assert final.options == []
#
#
# def test_unique_question_names(sections):
#     names = [q.name for q in sections]
#     assert len(names) == len(set(names)), "Duplicate question names found"
