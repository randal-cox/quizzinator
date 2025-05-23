import pytest
from quizzinator.ollama import Ollama

def test_clean():
  test_cases = [
    ('A test with—m-dash', 'A test with-m-dash'),
    ('A test with this‘unicode quote', 'A test with this\'unicode quote'),
    ('Another test with this“unicode quote', 'Another test with this"unicode quote'),
    ('\x1B[0m\x1B[0m\x1B[0m\x1B[0m', ''),
    ('Another test with the\nescape sequence', 'Another test with the\nescape sequence'),
  ]

  o = Ollama()
  for input_string, expected_output in test_cases:
    result = o._clean(input_string)
    assert result == expected_output

@pytest.mark.slow
def test_spawn():
  o = Ollama()
  # invoke spawn to start subprocess
  o.spawn()
  assert o.child.isalive() == True
  o.kill()

@pytest.mark.slow
def test_alive():
  o = Ollama()

  # Test that Ollama is alive when it is started
  o.spawn()
  assert o.alive() == True

  # Test that Ollama is not alive after it is killed
  o.kill()
  assert o.alive() == False

  # Test that Ollama is alive again after it is restarted
  o.restart()
  assert o.alive() == True

  # Clean up after test
  o.kill()
@pytest.mark.slow
def test_kill():
  ollama_obj = Ollama()
  ollama_obj.spawn()
  ollama_obj.kill()
  assert ollama_obj.alive() == False

@pytest.mark.slow
def no_test_restart():
  ollama_obj = Ollama()
  ollama_obj.spawn()
  ollama_obj.restart()
  assert ollama_obj.alive() == True
  ollama_obj.kill()
  assert ollama_obj.alive() == False

@pytest.mark.slow
def test_query():
  ollama_obj = Ollama()
  r = ollama_obj.query('type the letter A')
  assert '<think>' in r
  assert '</think>' in r
  assert 'A' in r
  ollama_obj.kill()
