"""Video analysis: scan (substituted name), embedded tracks, external subtitles."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from subliminal import refine, scan_video
from subliminal.core import search_external_subtitles
from subliminal.exceptions import GuessingError
from subliminal.subtitle import EmbeddedSubtitle, ExternalSubtitle
from subliminal.video import Episode, Movie, Video

from .config import Config

#: Embedded track formats, as given by the `metadata` refiner (knowit names, lower case).
IMAGE_FORMATS = {'pgs', 'vobsub', 'dvbsub'}
TEXT_FORMATS = {'srt', 'ass', 'ssa', 'tx3g', 'mov text', 'webvtt', 'vtt'}


@dataclass
class Analysis:
    path: Path
    guessit_name: str
    video: Video | None  # None: guessit did not recognise the title
    external: dict[Path, ExternalSubtitle]  # found by `search_external_subtitles`
    embedded: list[EmbeddedSubtitle]  # found by the `metadata` refiner


def kind(track: EmbeddedSubtitle) -> str:
    """'image', 'text' or 'unknown'."""
    if track.subtitle_format in IMAGE_FORMATS:
        return 'image'
    if track.subtitle_format in TEXT_FORMATS:
        return 'text'
    return 'unknown'


def readable_title(video: Video) -> str:
    """"The Fall (2006)" or "Doctor Who (2005) S01E02": also pre-fills the title input."""
    if isinstance(video, Episode):
        series = f'{video.series} ({video.year})' if video.year else video.series
        episodes = ''.join(f'E{e:02d}' for e in video.episodes)
        return f'{series} S{video.season:02d}{episodes}'
    if isinstance(video, Movie):
        return f'{video.title} ({video.year})' if video.year else video.title
    return os.path.basename(video.name)


def analyze(path: str | os.PathLike[str], config: Config, title: str | None = None) -> Analysis:
    """Analyses a video; `title` (typed by hand) replaces the file name for guessit.

    The `metadata` refiner is applied here (embedded tracks, frame rate, resolution…), even when the title
    is not recognised. Raises `ValueError` if the file does not exist or has no video extension.
    """
    path = Path(path)
    name = title.strip() + path.suffix if title else config.guessit_name(path)
    try:
        video = scan_video(path, name=name)
    except GuessingError:
        video = None
    probed = video if video is not None else Video(os.fspath(path))
    refine(probed, refiners=['metadata'], embedded_subtitles=True)
    return Analysis(
        path=path,
        guessit_name=name,
        video=video,
        external={path.parent / f: st for f, st in sorted(search_external_subtitles(path).items())},
        embedded=[s for s in probed.subtitles if isinstance(s, EmbeddedSubtitle)],
    )
