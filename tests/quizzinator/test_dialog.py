import pytest
import json
from pathlib import Path
import time

# Adjust this import path to where your Dialog class is defined
from quizzinator.dialog import Dialog

# Define a simple back-and-forth conversation
PROMPT1 = "Who Are You?"
PROMPT2 = "I am glad to meet you! Are you having a nice day?"

@pytest.mark.slow
def test_slow_query_and_save_cache():
    """
    Slow test: actually calls the live LLM via Ollama for two prompts, then saves the resulting cache to cache.json.
    """
    dialog = Dialog()
    # ensure live LLM is used
    dialog.cache = {}
    dialog._use_cache = False

    # Perform a back-and-forth conversation
    user1, llm1 = dialog.query(PROMPT1)
    user2, llm2 = dialog.query(PROMPT2)

    # Basic assertions on the first round
    assert user1['role'] == 'user'
    assert user1['content'] == PROMPT1
    assert llm1['role'] == 'llm'
    assert isinstance(llm1['raw'], str) and llm1['raw']

    # Basic assertions on the second round
    assert user2['role'] == 'user'
    assert user2['content'] == PROMPT2
    assert llm2['role'] == 'llm'
    assert isinstance(llm2['raw'], str) and llm2['raw']

    # Save the cache for fast tests
    # uncomment this in order to update the expected dialog if we change things
    # cache_file = Path(__file__).parent / 'test_dialog.json'
    # with open(cache_file, 'w') as f:
    #     json.dump(dialog.cache, f, indent=2)


def test_query_from_cache():
    """
    Fast test: loads cache.json and ensures query() uses the cache for both prompts without calling the LLM.
    """
    cache_file = Path(__file__).parent / 'test_dialog.json'
    assert cache_file.exists(), "Cache file not found; run the slow test first"
    with open(cache_file) as f:
        cache = json.load(f)

    dialog = Dialog(cache=cache)
    dialog._use_cache = True

    # Replay the back-and-forth conversation from cache
    for prompt in (PROMPT1, PROMPT2):
        user_entry, llm_entry = dialog.query(prompt)

        # Ensure history entries are correct
        assert dialog.history[-2]['role'] == 'user'
        assert dialog.history[-2]['content'] == prompt
        assert dialog.history[-1]['role'] == 'llm'

        # Verify think_and_response output matches llm entry
        raw = cache[prompt]
        think, content = Dialog.think_and_response(raw)
        assert llm_entry['think'] == think
        assert llm_entry['content'] == content


def test_think_and_response_multiple_tags():
    raw = "<think>foo</think><think>bar</think>baz"
    think, response = Dialog.think_and_response(raw)
    assert think == "foobar"
    assert response == "baz"


def test_think_and_response_no_tags():
    raw = "no think"
    think, response = Dialog.think_and_response(raw)
    assert think == ""
    assert response == "no think"


def test_cache_methods():
    dialog = Dialog(cache={})
    dialog.set_to_cache('key', 'value')
    assert dialog.get_from_cache('key') == 'value'
    assert dialog.get_from_cache('missing') is None


def test_user_and_llm_history():
    dialog = Dialog(cache={})

    # Test _user method
    user_entry = dialog._user("prompt")
    assert user_entry['role'] == 'user'
    assert user_entry['raw'] == 'prompt'
    assert user_entry['content'] == 'prompt'
    assert user_entry['think'] == ''
    assert 'start' in user_entry