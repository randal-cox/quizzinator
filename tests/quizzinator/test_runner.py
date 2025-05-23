# import os
# import csv
# import time
# import pytest
# from datetime import datetime
# from pathlib import Path
# from quizinator.runner import run_survey
# from quizinator.parser import Question, Option
#
# class DummyClient:
#     def __init__(self, answers):
#         # answers: dict keyed by question.prompt_text to answer string
#         self.answers = answers
#
#     def query(self, prompt):
#         # extract question text (second line of prompt)
#         lines = prompt.splitlines()
#         qtext = lines[1] if len(lines) > 1 else ''
#         # Return dict mimicking Ollama.query
#         return {
#             'role': 'assistant',
#             'content': self.answers.get(qtext, ""),
#             'think': '',
#             'extracted': self.answers.get(qtext, "")
#         }
#         # ignore any seed or additional args
#         # extract question text (second line of prompt)
#         lines = prompt.splitlines()
#         qtext = lines[1] if len(lines) > 1 else ''
#         return self.answers.get(qtext, "")
#
#         # extract question text (second line of prompt)
#         lines = prompt.splitlines()
#         qtext = lines[1] if len(lines) > 1 else ''
#         return self.answers.get(qtext, "")
#
# @pytest.fixture(autouse=True)
# def fixed_timestamp(monkeypatch):
#     # Freeze timestamp_str and time.time
#     import quizinator.runner as runner
#     monkeypatch.setattr(runner, 'timestamp_str', lambda: '2025-04-29T12-00-00')
#     monkeypatch.setattr(time, 'time', lambda: 1000)
#
# @pytest.fixture
# def questions():
#     q1 = Question(
#         name='Q1',
#         prompt_text='Q: First question?',
#         options=[Option(code=1, text='Yes'), Option(code=2, text='No')],
#         multi=False
#     )
#     q2 = Question(
#         name='Q2',
#         prompt_text='Q: Second question?',
#         options=[Option(code=1, text='A'), Option(code=2, text='B'), Option(code=3, text='C')],
#         multi=True
#     )
#     return [q1, q2]
#
# @pytest.fixture
# def setup_file(tmp_path):
#     path = tmp_path / 'setup.txt'
#     path.write_text('---SETUP---')
#     return str(path)
#
# def read_csv(outfile):
#     with open(outfile, newline='', encoding='utf-8') as f:
#         return list(csv.DictReader(f))
#
#
# def no_test_run_survey_single_job(tmp_path, questions, setup_file):
#     # Provide answers mapping by prompt_text
#     answers = {
#         questions[0].prompt_text: 'X',
#         questions[1].prompt_text: 'Y'
#     }
#     client = DummyClient(answers)
#     out_dir = tmp_path
#     run_survey(
#         questions,
#         setup_file,
#         client,
#         out_dir=str(out_dir),
#         n_runs=1,
#         seed=None,
#         jobs=1
#     )
#
#     expected_file = out_dir / '2025-04-29T12-00-00_seed1000.csv'
#     assert expected_file.exists(), f"Output file not found: {expected_file}"
#
#     rows = read_csv(expected_file)
#     # should have exactly 1 row for 1 respondent
#     assert len(rows) == 1
#     row = rows[0]
#     assert row['RespondentID'] == '1'
#     # RunTimestamp parseable
#     datetime.fromisoformat(row['RunTimestamp'])
#     assert row['Q1'] == 'X'
#     assert row['Q2'] == 'Y'
#
# @pytest.mark.parametrize('jobs', [1, 2])
# def no_test_run_survey_parallel(tmp_path, questions, setup_file, jobs):
#     # Reuse same answers for all respondents
#     answers = {
#         questions[0].prompt_text: 'A1',
#         questions[1].prompt_text: 'B2'
#     }
#     client = DummyClient(answers)
#     out_dir = tmp_path
#     run_survey(
#         questions,
#         setup_file,
#         client,
#         out_dir=str(out_dir),
#         n_runs=3,
#         seed=123,
#         jobs=jobs
#     )
#
#     expected_file = out_dir / '2025-04-29T12-00-00_seed123.csv'
#     assert expected_file.exists(), f"Output file not found: {expected_file}"
#
#     rows = read_csv(expected_file)
#     assert len(rows) == 3
#     for idx, row in enumerate(rows, start=1):
#         assert row['RespondentID'] == str(idx)
#         # same answers each run
#         assert row['Q1'] == 'A1'
#         assert row['Q2'] == 'B2'
