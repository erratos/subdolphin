"""kdialog windows (no business logic)."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager

#: Size of the candidate list: wide enough for release names.
LIST_SIZE = '1100x560'


class Kdialog:
    """kdialog windows. Every question returns None when the user cancels."""

    def __init__(self, title: str) -> None:
        self.title = title

    def _kdialog(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['kdialog', '--title', self.title, *arguments], capture_output=True, text=True)

    def choose(self, text: str, lines: Sequence[tuple[str, str]]) -> str | None:
        """List of `(tag, text)` lines; returns the chosen tag."""
        items = [item for line in lines for item in line]
        result = self._kdialog('--geometry', LIST_SIZE, '--menu', text, *items)
        tag = result.stdout.strip()
        return tag if result.returncode == 0 and tag else None

    def check(self, text: str, boxes: Sequence[tuple[str, str, bool]]) -> list[str] | None:
        """Check boxes `(tag, text, checked)`; returns the checked tags."""
        items = [item for tag, label, checked in boxes for item in (tag, label, 'on' if checked else 'off')]
        result = self._kdialog('--separate-output', '--checklist', text, *items)
        return result.stdout.split() if result.returncode == 0 else None

    def ask(self, text: str, default: str) -> str | None:
        result = self._kdialog('--inputbox', text, default)
        return result.stdout.rstrip('\n') if result.returncode == 0 else None

    def inform(self, text: str) -> None:
        self._kdialog('--msgbox', text)

    def error(self, text: str) -> None:
        self._kdialog('--error', text)

    def notify(self, text: str) -> None:
        """Passive notification, without waiting for it to disappear."""
        subprocess.Popen(
            ['kdialog', '--title', self.title, '--passivepopup', text, '5'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @contextmanager
    def _bar(self, text: str, maximum: int, cancellable: bool) -> Iterator[Bar]:
        """kdialog progress bar, driven through D-Bus, closed at the end of the `with` block."""
        result = self._kdialog('--progressbar', text, str(maximum))
        reference = result.stdout.split()
        bar = Bar(reference if result.returncode == 0 and len(reference) == 2 else None)
        if cancellable:
            bar.call('showCancelButton', 'true')
        try:
            yield bar
        finally:
            bar.call('close')

    @contextmanager
    def waiting(self, text: str) -> Iterator[None]:
        """Waiting window (spinning bar) during the `with` block."""
        with self._bar(text, 0, cancellable=False):
            yield

    def progress(self, text: str, total: int) -> AbstractContextManager[Bar]:
        """"Video n / total" bar with a Cancel button."""
        return self._bar(text, total, cancellable=True)


class Bar:
    """Open progress bar (`reference`: D-Bus service and object; None: no window)."""

    def __init__(self, reference: list[str] | None) -> None:
        self.reference = reference
        self.qdbus = shutil.which('qdbus6') or shutil.which('qdbus')

    def call(self, *arguments: str) -> str:
        if self.reference is None or self.qdbus is None:
            return ''
        result = subprocess.run([self.qdbus, *self.reference, *arguments], capture_output=True, text=True)
        return result.stdout.strip()

    def advance(self, index: int, text: str) -> None:
        self.call('Set', '', 'value', str(index))
        self.call('setLabelText', text)

    def cancelled(self) -> bool:
        return self.call('wasCancelled') == 'true'


def available() -> bool:
    return shutil.which('kdialog') is not None
