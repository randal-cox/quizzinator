import re, time

from .ollama import Ollama
from .logging import logger

class Dialog:
  def __init__(self, model: str = 'deepseek-r1:1.5b', timeout: float = 10.0, cache=None):
    """
    Create the dialog object

    model - the name of the model passed to ollama
    timeout - how long to wait for the llm
    cache - optional dictionary containing the expected responses from the llm (used for testing)
    """
    # details about the model for lazy instantiation
    self._model = model
    self._timeout = timeout
    self._ollama = None

    # keep track of the total history of the dialog
    self.history = []

    # the cache of prompt => raw pairs so we can test without calling the LLM
    self.cache = cache or {}
    self._use_cache = cache is not None

  def ollama(self):
    """Lazy creation of the Ollama client"""
    self._ollama = self._ollama or Ollama(self._model, self._timeout)
    return self._ollama

  def kill(self):
    if self._ollama: self._ollama.kill()

  def get_from_cache(self, key: str) -> str:
    """Query the cache of responses from the LLM"""
    return self.cache.get(key, None)

  def set_to_cache(self, key: str, value: str ) -> None:
    """Update the cache of responses from the LLM"""
    self.cache[key] = value

  @staticmethod
  def think_and_response(raw: str) -> tuple[str, str]:
    """Peel off the think part from the regular response."""
    # Split the text into two segments: think and response
    split_text = re.split(r'</think>', raw)

    # Join all segments before the last one and clean it from <think> tags
    think = "<think>".join(split_text[:-1]).replace("<think>", "").strip()

    # Take the last segment as a response
    response = split_text[-1].strip()

    return think, response

  def _user(self, prompt: str) -> dict[str, str | float]:
    """Append a user entry to history."""
    ret = {
      # mark it as the quizzinator doing this part of the conversation
      'role': 'user',

      # sections of the response
      'raw': prompt,
      'content': prompt,
      'think': '',
      'start': time.time(),
      'elapsed': 0.0,
    }
    self.history.append(ret)
    return ret

  def _llm(
      self, raw: str,
      think: str,
      content: str,
      start: float = None,
  ) -> dict[str, str | float]:
    ret = {
      # mark it as the quizzinator doing this part of the conversation
      'role': 'llm',

      # sections of the response
      'raw': raw,
      'content': content,
      'think': think,
      'start': start,
      'elapsed': time.time() - start,
    }
    self.history.append(ret)
    return ret

  def query(self, prompt: str) -> dict[str, str]:
    # record the user part of the conversation
    user = self._user(prompt)

    # get the LLM response (or get from the cache)
    t0 = time.time()
    if not self._use_cache:
      raw = self.ollama().query(prompt)
      if not raw:
        self.kill()
        raise TimeoutError("Failed to get ollama response")
      self.set_to_cache(prompt, raw)
    raw = self.get_from_cache(prompt)
    if not raw: raise Exception("no proper response in cache")
    think, content = self.think_and_response(raw)
    llm = self._llm(raw, think, content, t0)
    return [user, llm]
