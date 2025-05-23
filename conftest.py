#!/venv/bin/python3.12
import os, sys
import pytest

def pytest_addoption(parser):
  parser.addoption(
    "--slow",
    action="store_true",
    default=False,
    help="Run slow tests marked with @pytest.mark.slow",
  )


def pytest_collection_modifyitems(config, items):
  if config.getoption("--slow"):
    # --slow specified: do not skip anything
    return

  # otherwise skip tests marked slow
  skip_slow = pytest.mark.skip(reason="need --slow to run")
  for item in items:
    if "slow" in item.keywords:
      item.add_marker(skip_slow)

from quizzinator.logging import logger
@pytest.fixture(autouse=True)
def mute_ollama_spawn_logging(monkeypatch):
    """
    Silence logger.warning calls coming from OllamaClient.spawn()
    so your tests don’t print out that line.
    """
    # Keep a reference to the real function if you ever want to restore it:
    real_warn = logger.warning

    def fake_warning(msg, *args, **kwargs):
        if msg.startswith("Spawning"):
            return  # drop only the spawn message
        if "Finished spawn" in msg:
            return  # drop only the spawn message
        if msg.startswith("Killing ollama"):
            return  # drop only the spawn message
        return real_warn(msg, *args, **kwargs)

    monkeypatch.setattr(logger, "warning", fake_warning)
