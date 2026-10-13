"""Terminal output (`--text`), to try things out or diagnose without windows."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager


class Terminal:
    @contextmanager
    def progress(self, text: str, total: int) -> Iterator[Line]:
        print(text, flush=True)
        yield Line()

    def inform(self, text: str) -> None:
        print(text)

    def error(self, text: str) -> None:
        print(text, file=sys.stderr)


class Line:
    """Progress: one line per video; cancel with Ctrl+C."""

    def advance(self, index: int, text: str) -> None:
        print(text, flush=True)

    def cancelled(self) -> bool:
        return False
