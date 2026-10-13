"""Fake objects shared by the tests (no network)."""

from __future__ import annotations

from collections.abc import Iterable

from babelfish import Language
from subliminal.subtitle import Subtitle
from subliminal.video import Video


class FakeSubtitle(Subtitle):
    provider_name = 'fake'

    def __init__(
        self,
        matches: Iterable[str] = (),
        *,
        language: str = 'fr',
        hearing_impaired: bool = False,
        text: str | None = None,
        subtitle_id: str = 'id',
    ) -> None:
        super().__init__(Language.fromietf(language), subtitle_id, hearing_impaired=hearing_impaired, encoding='utf-8')
        self._matches = set(matches)
        if text is not None:
            self.content = text.encode('utf-8')

    def get_matches(self, video: Video) -> set[str]:
        return set(self._matches)

    @property
    def info(self) -> str:
        return f'Fake.Release.{self.id}'


SRT = '1\n00:00:01,000 --> 00:00:02,000\nBonjour, cœur’\n\n2\n00:00:03,000 --> 00:00:04,000\nAu revoir\n'
