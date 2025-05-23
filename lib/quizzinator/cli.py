"""
Global access to the parsed command-line arguments

To access the global args, use this code at the top of your file

  args = <process your command-line args
  cli_set_args(args)

Inside your functions where you want access, do this
  args = cli_get_args
"""

from .logging import logger

def cli_log_args(args):
  # Dump all args inside a named section (they’ll be indented)
  with logger.section("Parameters", timer=False):
    params = vars(args)
    width = max(len(k) for k in params)
    for key, val in sorted(params.items()):
      # wrap str arguments in quotes so that rich formats them nicely
      if type(val) == str: val = "'{}'".format(val)
      logger.info(f"{key:<{width}} : {val}")

def cli_set_args(this_args):
  global args
  args = this_args

def cli_get_args():
  return args

# module‐level default
args = None
