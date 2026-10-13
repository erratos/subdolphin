"""Saving: file name, duplicates, writing without overwriting (through `save_subtitles`)."""

from __future__ import annotations

import itertools
import os
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from babelfish import Language
from subliminal import save_subtitles
from subliminal.subtitle import FORMAT_TO_EXTENSION, ExternalSubtitle, Subtitle, get_subtitle_path, get_subtitle_suffix

from .analysis import Analysis
from .config import Config

#: Beyond this, give up (`Film.<provider>-100.fr.srt`: something is wrong).
MAX_ATTEMPTS = 100


def name_endings(
    language: Language,
    provider: str,
    *,
    hearing_impaired: bool,
    extension: str,
    already_present: bool,
    language_format: str = 'alpha2',
) -> Iterator[str]:
    """File name endings to try in order: `.fr.srt` if there is no subtitle in this language yet, then
    `.<provider>.fr.srt`, `.<provider>-2.fr.srt`, etc.

    `.hi` is added by hand: subliminal's `[hi]` suffix is not understood by mpv.
    """
    ending = f'{get_subtitle_suffix(language, language_format=language_format)}'
    ending += f'{".hi" if hearing_impaired else ""}{extension}'
    if not already_present:
        yield ending
    yield f'.{provider}{ending}'
    for n in itertools.count(2):
        yield f'.{provider}-{n}{ending}'


def reserve(path: Path) -> bool:
    """Creates `path`, empty, only if it does not exist (`O_EXCL`): no existing file is ever replaced, even
    by another run writing at the same time. False if the name is already taken."""
    try:
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644))
    except FileExistsError:
        return False
    return True


def normalize(text: str) -> str:
    """Comparable text: no BOM, unified line endings, no trailing spaces, no extra blank lines.

    subliminal is not enough: it only removes the BOM when it guesses the encoding (`utf-8-sig`), not when
    the provider imposes it (`utf-8`); and it unifies line endings on bytes (not in UTF-16).
    """
    text = text.lstrip('﻿').replace('\r\n', '\n')
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def find_duplicate(text: str, external: Mapping[Path, ExternalSubtitle]) -> Path | None:
    """First subtitle already present (any language) identical to `text`, or None.

    The existing text is decoded by subliminal (guessed encoding, BOM, line endings).
    """
    reference = normalize(text)
    for path, existing in external.items():
        try:
            existing.content = path.read_bytes()
        except OSError:
            continue
        if normalize(existing.text) == reference:
            return path
    return None


@dataclass
class SaveResult:
    path: Path | None  # file written, or None for a duplicate
    duplicate_of: Path | None = None


def is_writable_dir(video_path: Path) -> bool:
    """To check **before** downloading, so as not to use up download quota for nothing."""
    return os.access(video_path.parent, os.W_OK)


def save(subtitle: Subtitle, analysis: Analysis, config: Config) -> SaveResult:
    """Saves an already downloaded subtitle next to the video, overwriting nothing.

    Writing is done by subliminal (`save_subtitles`, with the configured encoding and format); the name is
    reserved first, because `save_subtitles` overwrites an existing file.
    """
    video = analysis.video
    if video is None:
        raise ValueError('video not recognised')
    if identical := find_duplicate(subtitle.text, analysis.external):
        return SaveResult(path=None, duplicate_of=identical)
    endings = name_endings(
        subtitle.language,
        subtitle.provider_name,
        hearing_impaired=bool(subtitle.hearing_impaired),
        extension=FORMAT_TO_EXTENSION.get(config.subtitle_format or subtitle.subtitle_format, '.srt'),
        already_present=any(s.language == subtitle.language for s in analysis.external.values()),
        language_format=config.language_format,
    )
    for ending in itertools.islice(endings, MAX_ATTEMPTS):
        path = Path(get_subtitle_path(video.name, extension=ending))
        if not reserve(path):
            continue
        try:
            saved = save_subtitles(
                video,
                [subtitle],
                single=True,
                extension=ending,
                encoding=config.encoding,
                subtitle_format=config.subtitle_format,
            )
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        if not saved:  # subtitle without content: save_subtitles skips it
            path.unlink(missing_ok=True)
            raise ValueError('empty subtitle')
        return SaveResult(path=path)
    raise FileExistsError(f'{MAX_ATTEMPTS} names already taken')
