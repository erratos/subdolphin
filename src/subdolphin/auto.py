"""The "Best subtitle automatically" flow: what `subliminal download` does."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from babelfish import Language
from subliminal.core import AsyncProviderPool, collect_video_filepaths
from subliminal.score import get_scores
from subliminal.video import VIDEO_EXTENSIONS

from .analysis import Analysis, analyze
from .config import Config
from .saving import is_writable_dir, save
from .search import configure_cache, refine_video
from .texts import t

#: Names shown per section of the summary (beyond: "… and N more").
MAX_NAMES = 10


class Progress(Protocol):
    def advance(self, index: int, text: str) -> None: ...
    def cancelled(self) -> bool: ...


class Interface(Protocol):
    """Windows of the automatic mode (`ui_kdialog.Kdialog`, `ui_terminal.Terminal`, or a fake one)."""

    def progress(self, text: str, total: int) -> AbstractContextManager[Progress]: ...
    def inform(self, text: str) -> None: ...


@dataclass
class Summary:
    total: int = 0
    processed: int = 0
    saved: list[Path] = field(default_factory=list)  # subtitles written
    already_have: list[Path] = field(default_factory=list)
    nothing_found: list[Path] = field(default_factory=list)
    unrecognized: list[Path] = field(default_factory=list)
    duplicates: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)
    cancelled: bool = False


def collect(paths: Iterable[Path]) -> list[Path]:
    """Videos to process: the given files, and those of the folders (`collect_video_filepaths`, as the
    command line: hidden folders, "sample" and symbolic links are ignored; no archives)."""
    videos: list[Path] = []
    for path in paths:
        if path.is_dir():
            videos += [Path(p) for p in collect_video_filepaths(path, archives=False)]
        elif path.name.lower().endswith(VIDEO_EXTENSIONS):
            videos.append(path)
    return list(dict.fromkeys(videos))


def languages_to_search(analysis: Analysis, config: Config) -> set[Language]:
    """As the command line: configured languages minus those already there, unless `force*` is set."""
    present: set[Language] = set()
    if not (config.force or config.force_external):
        present |= {s.language for s in analysis.external.values()}
    if not (config.force or config.force_embedded):
        present |= {e.language for e in analysis.embedded}
    return set(config.languages) - present


def process(path: Path, config: Config, pool: AsyncProviderPool, summary: Summary) -> None:
    """One video: analysis, choice and download by subliminal, saving without overwriting."""
    analysis = analyze(path, config)
    if analysis.video is None:
        summary.unrecognized.append(path)
        return
    languages = languages_to_search(analysis, config)
    if not languages:
        summary.already_have.append(path)
        return
    if not is_writable_dir(path):
        summary.errors.append((path, t('auto.read_only')))
        return
    video = analysis.video
    refine_video(video, config)
    downloaded = pool.download_best_subtitles(
        pool.list_subtitles(video, languages),
        video,
        languages,
        min_score=get_scores(video)['hash'] * config.min_score // 100,
        subtitle_categories=config.subtitle_categories,
        skip_wrong_fps=config.skip_wrong_fps,
    )
    if not downloaded:
        summary.nothing_found.append(path)
        return
    for subtitle in downloaded:
        result = save(subtitle, analysis, config)
        if result.path is None:
            summary.duplicates.append(path)
        else:
            summary.saved.append(result.path)


def run(paths: Iterable[Path], config: Config, ui: Interface) -> Summary:
    """Processes every video (can be cancelled between two videos), then shows the summary."""
    videos = collect(paths)
    summary = Summary(total=len(videos))
    if videos:
        configure_cache(config)
        with (
            ui.progress(t('auto.start', n=len(videos)), len(videos)) as progress,
            AsyncProviderPool(
                max_workers=config.max_workers,
                providers=list(config.providers),
                provider_configs=config.provider_configs,
            ) as pool,
        ):
            for index, path in enumerate(videos):
                if progress.cancelled():
                    summary.cancelled = True
                    break
                progress.advance(index, t('auto.video', index=index + 1, total=len(videos), name=path.name))
                try:
                    process(path, config, pool, summary)
                except Exception as e:  # noqa: BLE001  # one failing video does not stop the others
                    # Message only for system errors: others may quote a URL with a key.
                    error = f'{type(e).__name__}: {e}' if isinstance(e, OSError) else type(e).__name__
                    summary.errors.append((path, error))
                summary.processed += 1
    ui.inform(summary_text(summary, config))
    return summary


def summary_text(summary: Summary, config: Config) -> str:
    if not summary.total:
        return t('auto.no_video')

    def names(paths: list[Path]) -> list[str]:
        lines = [f'    {p.name}' for p in paths[:MAX_NAMES]]
        if len(paths) > MAX_NAMES:
            lines.append('    ' + t('auto.more', n=len(paths) - MAX_NAMES))
        return lines

    nothing = (
        t('auto.nothing_found', threshold=config.min_score, n=len(summary.nothing_found))
        if config.min_score
        else t('auto.nothing_found_no_threshold', n=len(summary.nothing_found))
    )
    lines = [t('auto.summary_title', n=summary.total), '']
    lines += [t('auto.saved', n=len(summary.saved)), *names(summary.saved)]
    lines += [t('auto.already_have', n=len(summary.already_have))]
    lines += [nothing, *names(summary.nothing_found)]
    lines += [t('auto.unrecognized', n=len(summary.unrecognized)), *names(summary.unrecognized)]
    if summary.duplicates:
        lines += [t('auto.duplicates', n=len(summary.duplicates)), *names(summary.duplicates)]
    if summary.errors:
        lines += [t('auto.errors', n=len(summary.errors))]
        lines += [t('auto.error_line', name=p.name, error=error) for p, error in summary.errors[:MAX_NAMES]]
    if summary.cancelled:
        lines += ['', t('auto.cancelled', done=summary.processed, total=summary.total)]
    if summary.errors or summary.nothing_found:
        lines += ['', t('auto.help')]
    return '\n'.join(lines)
