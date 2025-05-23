import pexpect
import signal
import json
import sys
import time


from .string import pythonify_string, remove_escape_sequences
from .logging import logger
from .utils import ngram_repeat

class Ollama:
  def __init__(self, model: str = 'deepseek-r1:1.5b', timeout: float = 120.0):
    """
    model:    the ollama model name to run
    timeout:  how long (in seconds) to wait for each response
    """
    self.model = model
    self.timeout = timeout

    # Start the command-line process
    self.child: pexpect.spawn | None = None
    self.spawn()

  def spawn(self) -> None:
    """Start up a fresh ollama subprocess and consume its initial prompt."""
    # don't do this if it is already alive
    if self.alive(): return

    #logger.info(f"Spawning '{self.model}'")
    cmd = f"ollama run {self.model}"
    try:
      self.child = pexpect.spawn(cmd, encoding='utf-8', timeout=self.timeout, maxread=1000000)
      self.child.expect('>>> ')
      self.child.setecho(False)
    except pexpect.exceptions.TIMEOUT:
      raise TimeoutError(f"Ollama prompt did not appear within {self.timeout}s using `{cmd}`")
    except pexpect.exceptions.EOF:
      output = getattr(self.child, 'before', '')
      raise EOFError(f"Ollama process `{cmd}` exited unexpectedly during startup. Output before EOF:\n{output}")

    # disable formatting/wrapping
    self.child.sendline('/set noformat')
    self.child.expect('>>> ')
    self.child.sendline('/set nowordwrap')
    self.child.expect('>>> ')

  def kill(self) -> None:
    """Make sure any child process is dead"""
    if self.alive():
      #logger.info("Killing ollama")
      self.child.kill(signal.SIGKILL)
      start_time = time.time()
      while self.child.isalive():
        if time.time() - start_time > 5.0:  # Timeout after 5 seconds
          raise Exception("Could not kill ollama after ")
        time.sleep(0.01)  # Check every 10 milliseconds
      self.child = None

  def alive(self) -> bool:
    if self.child and self.child.isalive(): return True
    return False

  def restart(self) -> None:
    """Kill the current process, clear history, and restart."""
    self.kill()
    self.spawn()

  def _push(self, prompt):
    if not prompt.endswith("\n"): prompt += "\n"
    chunk_size = 64
    for i in range(0, len(prompt), chunk_size):
      part = prompt[i:i + chunk_size]
      self.child.send(part)
      # Immediately drain any output so the pty master buffer frees up
      try:
        # maxread is by default ~2000 bytes, so this will
        # gobble up all waiting data without blocking.
        self.child.read_nonblocking(size=self.child.maxread, timeout=100)
      except pexpect.exceptions.TIMEOUT:
        pass
      time.sleep(0.01)

  def _pull(self):
    buffer = ""
    start = time.time()
    last_size = 0
    last_time = start_time = time.time()
    while True:
      try:
        chunk = self.child.read_nonblocking(size=1024, timeout=0.1)
        buffer += chunk
        if '<think>' in buffer:
          buffer = '<think>' + buffer.split('<think>')[1]
        if (time.time() - last_time > self.timeout):
          logger.info(f"delay in reading response; now up to {len(buffer):,} characters after {int(time.time() - start_time):,} seconds")

          # if we've stalled for the timeout AND there is no new data, then we should just bail out
          if len(buffer) == last_size:
            logger.error("No response after timeout period")
            self.kill()
            raise TimeoutError("Timed out on pull - no response after timeout")

          # it might still be very repetitious
          repeat, count = ngram_repeat(self._clean(buffer), L=30, K=2)
          if count > 3:
            logger.warning(f"{count:,} repetitions of string [red]'{repeat.replace('\n', '-')}[/red]")
            raise TimeoutError("Timed out on pull - LLM repetitiously")
            # TODO: should save buffer for a post-mortem

          last_size = len(buffer)
          last_time = time.time()

        # if you see your prompt marker in buffer, we are done for now
        if ">>> " in buffer: break
      except pexpect.exceptions.TIMEOUT:
        pass
      # safety net - if the LLM keeps talking forever, we should just bail on it
      if time.time() - start > self.timeout * 3:
        logger.error("Response is taking too long")
        #print(buffer)
        self.kill()
        raise TimeoutError("Timed out on pull -LLM talked forever")
    #logger.info(f"got response after {int(time.time() - start_time):,} secs")
    # strip off everything *after* the last prompt, so buffer.before…
    return buffer.split(">>> ")[0]

  @classmethod
  def _clean(cls, response: str) -> str:
    # there is a LOT of crap in this feed!

    # remove all the terrible terminal escape sequences
    response = remove_escape_sequences(response)

    # unicode quotes
    response = response.replace("\u0022", '"')
    response = response.replace("\u0027", "'")
    response = response.replace("\u201C", '"')
    response = response.replace("\u201D", '"')
    response = response.replace("\u2018", "'")
    response = response.replace("\u2019", "'")

    # fix m-dash and unicode quotes
    response = response.replace('\u2014', '-')
    response = response.replace('\u2013', '-')

    # fix brail progress indicators
    response = ''.join(c for c in response if not 0x2800 <= ord(c) <= 0x28ff)

    # the funny newline stuff
    response = response.replace('\r\n', '\n')

    # make sure any strange unicode and white space ASCII is made visible
    response = pythonify_string(response.strip())

    # there is a bunch of leading crap that usually gets erased by the terminal escape sequences
    if '<think>' in response:
      response = '<think>' + response.split('<think>')[1]

    return response
  def query(self, prompt: str) -> str:
    """
    Safely send even huge prompts by breaking them into small byte chunks.

    Not doing this causes mysterious hangs and vast amounts of debugging :(
    """
    if '\n' in prompt: prompt = '"""' + prompt + '"""'
    self._push(prompt)
    response = self._pull()
    response = self._clean(response)
    return response