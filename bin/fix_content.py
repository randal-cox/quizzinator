#./venv/bin/python

import subprocess, pathlib, sys, os, textwrap, tempfile

root = pathlib.Path(".").resolve()
q_path = root / "data/consent/questions.txt"
h_path = root / "data/consent/hints.csv"

q_bytes = q_path.read_bytes()
h_bytes = h_path.read_bytes()

script = f"""
from git_filter_repo import FilterRepo, Blob, FileChange

Q = {q_bytes!r}
H = {h_bytes!r}

def commit_callback(commit, metadata):
    pass

def file_info_callback(file_info, metadata):
    # file_info.path is bytes
    if file_info.path == b"data/consent/questions.txt":
        file_info.blob = metadata.new_blob(Q)
    elif file_info.path == b"data/consent/hints.csv":
        file_info.blob = metadata.new_blob(H)

FilterRepo(commit_callback=commit_callback, file_info_callback=file_info_callback).run()
"""

with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f:
    f.write(script)
    tmp = f.name

try:
    subprocess.check_call(["git", "filter-repo", "--force", "--script", tmp])
finally:
    os.unlink(tmp)
