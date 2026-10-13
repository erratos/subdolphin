"""The "Choose a subtitle…" flow, independent of the windows (`ui` object)."""

from __future__ import annotations

import html
from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from babelfish import Language
from subliminal.subtitle import Subtitle

from .analysis import Analysis, analyze, kind, readable_title
from .config import Config
from .saving import is_writable_dir, save
from .search import Candidate, above_threshold, download, list_candidates, refine_video
from .texts import percent, t, t_or

#: Tags of the first two lines of the list.
CORRECT = 'correct'
OPTIONS = 'options'

#: Languages always offered in the options, besides the configured ones.
OFFERED_LANGUAGES = ('fr', 'en')
#: subliminal's categories (`subtitle_categories`): regular, hearing impaired, forced.
CATEGORIES = ('n', 'hi', 'fo')


class Interface(Protocol):
    """What the flow asks of the windows (`ui_kdialog.Kdialog`, or a fake one in tests)."""

    def choose(self, text: str, lines: list[tuple[str, str]]) -> str | None: ...
    def check(self, text: str, boxes: list[tuple[str, str, bool]]) -> list[str] | None: ...
    def ask(self, text: str, default: str) -> str | None: ...
    def inform(self, text: str) -> None: ...
    def error(self, text: str) -> None: ...
    def notify(self, text: str) -> None: ...
    def waiting(self, text: str) -> AbstractContextManager[None]: ...


@dataclass
class Retry:
    """New search requested from the list."""

    title: str | None = None  # new title (None: the same)
    config: Config | None = None  # options for this search (None: the same)


# --- List texts -----------------------------------------------------------------------------------


def describe(subtitle: Subtitle) -> str:
    """"fr, hearing impaired": language and category of a subtitle already there (file or track)."""
    details = [str(subtitle.language) if subtitle.language else t('language.unknown')]
    if subtitle.hearing_impaired:
        details.append(t('track.hearing_impaired'))
    if subtitle.foreign_only:
        details.append(t('track.forced'))
    return ', '.join(details)


def line(candidate: Candidate) -> str:
    """"86.7%  ★ opensubtitlescom — The.Fall.2006… · HI · 23.976 fps"."""
    marks = [m for m, yes in (('HI', candidate.hearing_impaired),
                              (t('mark.machine_translated'), candidate.machine_translated)) if yes]  # fmt: skip
    if candidate.fps:
        marks.append(t('ui.fps', fps=f'{candidate.fps:g}'))
    start = f'{percent(candidate.percent)}  {"★ " if candidate.hash_match else ""}{candidate.provider}'
    return ' · '.join([f'{start} — {candidate.release}', *marks])


def language_name(language: Language) -> str:
    return t_or(f'language.{language}', language.name)


def options_summary(config: Config) -> str:
    """"languages fr · all categories"."""
    if config.subtitle_categories:
        codes = [c for c in config.subtitle_categories.split(',') if c in CATEGORIES]
        categories = ', '.join(t(f'ui.category_short_{c}') for c in codes)
    else:
        categories = t('ui.all_categories')
    languages = ', '.join(sorted(str(lg) for lg in config.languages))
    return t('ui.options_summary', languages=languages, categories=categories)


def header(analysis: Analysis, candidates: Sequence[Candidate], kept: Sequence[Candidate], config: Config,
           count: int | None) -> str:  # fmt: skip
    """List header, in HTML (kdialog shows it as rich text): recognised title in bold."""
    assert analysis.video is not None
    title = f'<b>{html.escape(readable_title(analysis.video))}</b>'
    if not candidates:
        first = t('ui.none_found', title=title)
    else:
        if config.min_score:
            first = t('ui.found_threshold', title=title, n=len(candidates), kept=len(kept), threshold=config.min_score)
        else:
            first = t('ui.found', title=title, n=len(candidates))
        if count is not None and count < len(kept):
            first += t('ui.order_limited', shown=count)
        else:
            first += t('ui.order_all')
    lines = [first]
    if analysis.external:
        present = ' ; '.join(f'{p.name} ({describe(s)})' for p, s in analysis.external.items())
        lines.append(html.escape(t('ui.present', items=present)))
    if analysis.embedded:
        tracks = ' ; '.join(f'{describe(e)}, {t(f"kind.{kind(e)}")}' for e in analysis.embedded)
        lines.append(html.escape(t('ui.embedded', items=tracks)))
    lines.append(html.escape(t('ui.legend')))
    return '<br>'.join(lines)


# --- Options for this search ---------------------------------------------------------------------


def ask_options(config: Config, ui: Interface) -> Config | None:
    """Languages and categories for this search only (starting values: the configuration).

    Returns the modified configuration, or None if nothing changes (cancelled or incomplete choice).
    """
    codes = sorted({*OFFERED_LANGUAGES, *(str(lg) for lg in config.languages)})
    checked = set(config.subtitle_categories.split(',')) if config.subtitle_categories else set(CATEGORIES)
    boxes = [(f'language:{c}', t('ui.option_language', name=language_name(Language.fromietf(c))),
              Language.fromietf(c) in config.languages) for c in codes]  # fmt: skip
    boxes += [(f'category:{c}', t(f'ui.category_{c}'), c in checked) for c in CATEGORIES]
    answer = ui.check(t('ui.options'), boxes)
    if answer is None:
        return None
    languages = frozenset(Language.fromietf(a.removeprefix('language:')) for a in answer if a.startswith('language:'))
    categories = [c for c in CATEGORIES if f'category:{c}' in answer]
    if not languages or not categories:
        ui.inform(t('ui.options_incomplete'))
        return None
    if len(categories) == len(CATEGORIES) and not config.subtitle_categories:
        subtitle_categories = ''  # everything checked, as at the start: no filtering, no sorting
    else:
        # The configuration's order of preference first (subliminal sorts in this order), then the others.
        order = [c for c in config.subtitle_categories.split(',') if c in CATEGORIES] + list(CATEGORIES)
        subtitle_categories = ','.join(dict.fromkeys(c for c in order if c in categories))
    return replace(config, languages=languages, subtitle_categories=subtitle_categories)


# --- Flow ----------------------------------------------------------------------------------------


def offer(analysis: Analysis, candidates: list[Candidate], config: Config, ui: Interface,
          count: int | None) -> int | Retry:  # fmt: skip
    """List → download → save.

    Returns an exit code, or the new search requested (corrected title, changed options).
    """
    assert analysis.video is not None
    kept = above_threshold(candidates, config.min_score)
    lines = [(CORRECT, t('ui.line_correct')), (OPTIONS, t('ui.line_options', summary=options_summary(config)))]
    lines += [(str(i), line(c)) for i, c in enumerate(kept[:count])]
    while True:
        answer = ui.choose(header(analysis, candidates, kept, config, count), lines)
        if answer is None:
            return 1
        if answer == CORRECT:
            title = (ui.ask(t('ui.correct_title'), readable_title(analysis.video)) or '').strip()
            if title:
                return Retry(title=title)
            continue  # input cancelled: back to the list
        if answer == OPTIONS:
            new_config = ask_options(config, ui)
            if new_config is not None:
                return Retry(config=new_config)
            continue
        candidate = kept[int(answer)]
        with ui.waiting(t('ui.downloading', provider=candidate.provider)):
            downloaded = download(candidate, config)
        if not downloaded:
            ui.error(t('ui.download_failed', provider=candidate.provider, path=analysis.path))
            continue
        try:
            result = save(candidate.subtitle, analysis, config)
        except (OSError, ValueError) as e:
            ui.error(t('ui.save_error', error=e))
            return 2
        if result.path is None:
            assert result.duplicate_of is not None
            ui.inform(t('ui.duplicate', name=result.duplicate_of.name))
            continue
        ui.notify(t('ui.saved', name=result.path.name))
        return 0


def choose(path: Path, config: Config, ui: Interface, count: int | None = None) -> int:
    """Whole flow for one video; returns 0 (saved), 1 (cancelled) or 2 (error).

    The list shows every candidate at or above `min_score` (`count`: only the N best).
    """
    try:
        analysis = analyze(path, config)
    except (ValueError, OSError) as e:
        ui.error(t('ui.video_error', error=e))
        return 2
    if not is_writable_dir(path):
        ui.error(t('ui.read_only', folder=path.parent))
        return 2
    question = t('ui.title_not_found', name=path.name)
    while True:
        # Title not recognised: ask for it, then analyse again.
        if analysis.video is None:
            title = (ui.ask(question, path.stem) or '').strip()
            if not title:
                return 1
            analysis = analyze(path, config, title)
            question = t('ui.still_not_found', title=title)
            continue
        video = analysis.video
        with ui.waiting(t('ui.searching', title=readable_title(video))):
            refine_video(video, config)
            candidates = list_candidates(video, config)
        outcome = offer(analysis, candidates, config, ui, count)
        if isinstance(outcome, int):
            return outcome
        if outcome.config is not None:
            config = outcome.config
        if outcome.title is not None:
            analysis = analyze(path, config, outcome.title)
            question = t('ui.still_not_found', title=outcome.title)
