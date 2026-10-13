"""Search: refiners, candidate list (subliminal's provider pool), score, ordering, download."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta

from subliminal import compute_score, download_subtitles, refine
from subliminal.cache import region
from subliminal.cli.helpers import MutexLock
from subliminal.core import AsyncProviderPool
from subliminal.score import get_scores
from subliminal.subtitle import Subtitle, filter_and_sort_categories
from subliminal.video import Video

from .config import Config

DEFAULT_COUNT = 10


def configure_cache(config: Config) -> None:
    """Cache shared with subliminal's command line, configured as it does (`subliminal/cli/cli.py`)."""
    if region.is_configured:
        return
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    region.configure(
        'dogpile.cache.dbm',
        expiration_time=timedelta(days=30),
        arguments={'filename': os.fspath(config.cache_dir / 'subliminal.dbm'), 'lock_factory': MutexLock},
    )


def refine_video(video: Video, config: Config) -> None:
    """Completes the video with the configured refiners (hashes, TMDB…), as the command line does.

    `metadata` is skipped: `analysis.analyze` has already applied it.
    """
    configure_cache(config)
    refine(
        video,
        refiners=[r for r in config.refiners if r != 'metadata'],
        refiner_configs=config.refiner_configs,
        providers=list(config.providers),
        languages=set(config.languages),
    )


@dataclass
class Candidate:
    subtitle: Subtitle = field(repr=False)
    score: int
    max_score: int
    hash_match: bool  # sync guaranteed

    @classmethod
    def evaluate(cls, subtitle: Subtitle, video: Video) -> Candidate:
        return cls(
            subtitle=subtitle,
            score=compute_score(subtitle, video),
            max_score=get_scores(video)['hash'],
            hash_match='hash' in subtitle.get_matches(video),
        )

    @property
    def percent(self) -> float:
        return 100 * self.score / self.max_score

    @property
    def provider(self) -> str:
        return self.subtitle.provider_name

    @property
    def release(self) -> str:
        return str(self.subtitle.info)

    @property
    def hearing_impaired(self) -> bool:
        return bool(self.subtitle.hearing_impaired)

    @property
    def machine_translated(self) -> bool:
        return bool(getattr(self.subtitle, 'machine_translated', False))

    @property
    def fps(self) -> float | None:
        return self.subtitle.fps


def sort_candidates(subtitles: Sequence[Subtitle], video: Video, categories: str = '') -> list[Candidate]:
    """Order of `download_best_subtitles`: categories (`subtitle_categories`, which may also filter some
    out), then score; equal scores keep the providers' order."""
    candidates = [Candidate.evaluate(s, video) for s in filter_and_sort_categories(subtitles, categories)]
    return sorted(candidates, key=lambda c: c.score, reverse=True)


def above_threshold(candidates: Sequence[Candidate], min_score: int) -> list[Candidate]:
    """Candidates at `min_score` % of the maximum score or more, computed as the command line does
    (`download_best_subtitles`)."""
    return [c for c in candidates if c.score >= c.max_score * min_score // 100]


def list_candidates(video: Video, config: Config) -> list[Candidate]:
    """Every candidate, best first.

    Through the provider pool, as the command line does: `subliminal.list_subtitles` skips videos that
    already have the language (even as an embedded track), whereas we want to be able to get another one.
    """
    configure_cache(config)
    with AsyncProviderPool(
        max_workers=config.max_workers,
        providers=list(config.providers),
        provider_configs=config.provider_configs,
    ) as pool:
        subtitles = pool.list_subtitles(video, set(config.languages))
    return sort_candidates(subtitles, video, config.subtitle_categories)


def download(candidate: Candidate, config: Config) -> bool:
    """Downloads the candidate's content; False on failure (details: `subdolphin --debug`)."""
    download_subtitles(
        [candidate.subtitle],
        providers=[candidate.provider],
        provider_configs=config.provider_configs,
    )
    return candidate.subtitle.is_valid()
