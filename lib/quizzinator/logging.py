from datetime import datetime
from contextlib import contextmanager
from rich.console import Console
import sys, time, inspect
from typing import Optional

from .utils import human_duration
class Progress:
    def __init__(self, logger, name, steps=None, width=25,
                 show_steps=True, show_eta=True, silent: bool = False):
        self.logger     = logger
        self.name       = name
        self.steps      = steps
        self.width      = width
        self.show_steps = show_steps
        self.show_eta   = show_eta
        self.silent     = silent

    def __enter__(self):
        self.start = time.time()
        self.logger.info(f"[bold]{self.name}[/bold] started.")
        self.logger.indent_level += self.logger.indent_step
        self.current = 0
        return self

    def step(self, message: str, level: str = "INFO"):
        self.current += 1
        elapsed = time.time() - self.start

        parts = []
        if self.steps:
            filled = int(self.current / self.steps * self.width)
            parts.append("=" * filled + " " * (self.width - filled))
            if self.show_steps:
                parts.append(f"Step {self.current}/{self.steps}")
            if self.show_eta:
                # expected time remaining
                expected = (self.steps - self.current) * (elapsed / self.current)
                timestr = human_duration(expected)
                parts.append(f"done in [cyan]{timestr}[/cyan]")
        else:
            if self.show_steps:
                parts.append(f"Step {self.current}")
        parts.append(message)

        if not self.silent:
            msg = " | ".join(parts)
            self.logger.log(level, msg)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # always restore indent
        self.logger.indent_level -= self.logger.indent_step

        if exc_type is SystemExit:
            # let the exit propagate, skip footer
            return False

        # if you want to log on *any* exception (other than SystemExit),
        # you could do so here before re-raising.
        if exc_type is not None:
            # optional: self.logger.error(f"[bold]{self.name} aborted![/bold]")
            return False  # re-raise the original exception

        # normal, no‐exception path → print the footer
        elapsed = time.time() - self.start
        m, s    = divmod(int(elapsed), 60)
        self.logger.info(f"[bold]{self.name} completed in {m}:{s:02d}[/bold]")
        return False  # don’t swallow anything


class Logger:
    LEVEL_STYLES = {
        "DEBUG":    "",
        "INFO":     "",
        "WARNING":  "orange1",
        "ERROR":    "red",
        "CRITICAL": "white on red",
    }

    def __init__(self, indent_step: int = 2):
        # highlight=True  => let Rich colorize numbers/strings/booleans in the message
        # markup=True     => let [bold], [red] tags be honored
        self.console      = Console(highlight=True, markup=True)
        self.indent_level = 0
        self.indent_step  = indent_step
        # default per-call markup
        self._use_markup  = True

    def _format_parts(self, level: str, message: str):
        """
        Returns (prefix, msg) where prefix is timestamp│LEVEL│indent
        (always printed with highlight=False so no auto-coloring),
        and msg is the user payload (printed with highlight=True).
        """
        ts     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        indent = " " * self.indent_level
        style  = self.LEVEL_STYLES.get(level, "")
        if style:
            lvl = f"[{style}]{level:<8}[/]"
        else:
            lvl = f"{level:<8}"
        prefix = f"{ts} | {lvl} | {indent}"
        return prefix, message

    def log(self, level: str, message: str, *, markup: Optional[bool] = None):
        """
        markup=None => use default (True)
        markup=False => disable all [tags] on this call
        """
        use_markup = self._use_markup if markup is None else markup
        for line in str(message).splitlines() or [""]:
            prefix, msg = self._format_parts(level, line)
            # print prefix as plain text (no highlight, but still allow our [LEVEL] tags)
            self.console.print(prefix, end="", highlight=False, markup=True)
            # print msg with highlight and per-call markup setting
            self.console.print(msg,    highlight=True,  markup=use_markup)

    def debug(self,   message: str, *, markup: Optional[bool] = None):
        self.log("DEBUG",   message, markup=markup)
    def info(self,    message: str, *, markup: Optional[bool] = None):
        self.log("INFO",    message, markup=markup)
    def warning(self, message: str, *, markup: Optional[bool] = None):
        self.log("WARNING", message, markup=markup)
    def error(self,   message: str, *, markup: Optional[bool] = None):
        self.log("ERROR",   message, markup=markup)
    def critical(self,message: str, *, markup: Optional[bool] = None):
        self.log("CRITICAL",message, markup=markup)
        sys.exit()

    def exit(self, message: str = "Exiting"):
        frame    = inspect.currentframe().f_back
        lineno   = frame.f_lineno
        filename = frame.f_code.co_filename
        self.critical(f"{message} ─ exit from line {lineno} of {filename}")
        sys.exit()

    @contextmanager
    def section(self, name: str, timer: bool = False):
        start = time.time()
        self.info(f"[bold]{name}[/bold]")
        self.indent_level += self.indent_step
        try:
            yield
        finally:
            self.indent_level -= self.indent_step
            msg = f"[bold]{name} completed[bold]"
            if timer:
                elapsed = time.time() - start
                m, s = divmod(int(elapsed), 60)
                msg += f" in {m}:{s:02d}"
            self.info(msg)

    def progress(self, *args, **kwargs):
        return Progress(self, *args, **kwargs)


    @contextmanager
    def no_color(self):
        """
        Temporarily disable all markup on subsequent calls in this block.
        """
        prev = self._use_markup
        self._use_markup = False
        try:
            yield
        finally:
            self._use_markup = prev


# module‐level default
logger = Logger()
