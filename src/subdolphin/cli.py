"""Command line: subdolphin list / choose / auto / menu."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Any

from subliminal.video import Episode

from . import auto, menu, ui_kdialog, ui_terminal
from . import config as configuration
from .analysis import Analysis, analyze, kind, readable_title
from .choose import choose, describe
from .search import DEFAULT_COUNT, Candidate, above_threshold, list_candidates, refine_video
from .texts import percent, t


def candidate_line(index: int, c: Candidate) -> str:
    fps = f'{c.fps:g}' if c.fps else ''
    machine_translated = t('mark.machine_translated') if c.machine_translated else '  '
    return (
        f'{index:3d}  {percent(c.percent):>8}  {"★" if c.hash_match else " "}  {c.provider:<16}  '
        f'{"HI" if c.hearing_impaired else "  "}  {machine_translated}  {fps:<6}  {c.release}'
    )


def print_analysis(analysis: Analysis) -> None:
    print(t('list.video', name=analysis.path.name))
    print(t('list.guessit_name', name=analysis.guessit_name))
    if analysis.video is None:
        print(t('list.unrecognized'))
    else:
        key = 'list.episode' if isinstance(analysis.video, Episode) else 'list.movie'
        print(t(key, title=readable_title(analysis.video)))
    if analysis.embedded:
        print(t('list.embedded'))
        for track in analysis.embedded:
            print(f'  {describe(track)}, {t(f"kind.{kind(track)}")} ({track.subtitle_format})')
    else:
        print(t('list.embedded_none'))
    if analysis.external:
        print(t('list.external'))
        for path, subtitle in analysis.external.items():
            print(f'  {path.name} ({describe(subtitle)})')
    else:
        print(t('list.external_none'))


def print_candidates(candidates: list[Candidate], min_score: int, count: int) -> None:
    """Candidates at or above `min_score` (configuration setting, as subliminal's command line)."""
    kept = above_threshold(candidates, min_score)
    print()
    if not kept:
        print(t('list.none'))
    else:
        print(t('list.header'))
        for index, candidate in enumerate(kept[:count], 1):
            print(candidate_line(index, candidate))
        print()
    shown = min(count, len(kept))
    if min_score:
        print(t('list.total_threshold', n=len(candidates), kept=len(kept), threshold=min_score, shown=shown))
    else:
        print(t('list.total', n=len(candidates), shown=shown))
    if kept:
        print(t('list.legend'))


def to_json(analysis: Analysis, candidates: list[Candidate], min_score: int, count: int) -> dict[str, Any]:
    """Structured result (no secret: no username, key or token)."""
    video = analysis.video
    kept = above_threshold(candidates, min_score)
    return {
        'path': str(analysis.path),
        'guessit_name': analysis.guessit_name,
        'recognized': None if video is None else {
            'type': 'episode' if isinstance(video, Episode) else 'movie',
            'title': readable_title(video),
        },
        'embedded': [
            {
                'language': str(e.language) if e.language else None, 'format': e.subtitle_format,
                'kind': kind(e), 'forced': bool(e.foreign_only), 'hearing_impaired': bool(e.hearing_impaired),
            }
            for e in analysis.embedded
        ],
        'external': [
            {
                'file': path.name, 'language': str(s.language) if s.language else None,
                'hearing_impaired': bool(s.hearing_impaired), 'forced': bool(s.foreign_only),
            }
            for path, s in analysis.external.items()
        ],
        'candidate_count': len(candidates),
        'min_score': min_score,
        'kept_count': len(kept),
        'candidates': [
            {
                'provider': c.provider, 'id': c.subtitle.id, 'score': c.score, 'max_score': c.max_score,
                'percent': round(c.percent, 1), 'hash_match': c.hash_match, 'release': c.release,
                'language': str(c.subtitle.language), 'hearing_impaired': c.hearing_impaired,
                'machine_translated': c.machine_translated, 'fps': c.fps,
            }
            for c in kept[:count]
        ],
    }  # fmt: skip


def cmd_list(args: argparse.Namespace, config: configuration.Config) -> int:
    try:
        analysis = analyze(args.video, config, title=args.title)
    except (ValueError, OSError) as e:
        print(t('err.video', error=e), file=sys.stderr)
        return 2
    candidates: list[Candidate] = []
    if analysis.video is not None:
        refine_video(analysis.video, config)
        candidates = list_candidates(analysis.video, config)
    if args.json:
        print(json.dumps(to_json(analysis, candidates, config.min_score, args.count), ensure_ascii=False, indent=2))
    else:
        print_analysis(analysis)
        if analysis.video is not None:
            print_candidates(candidates, config.min_score, args.count)
    return 0 if analysis.video is not None else 3


def cmd_choose(args: argparse.Namespace) -> int:
    """Run from Dolphin: every error is shown in a window."""
    if not ui_kdialog.available():
        print(t('err.kdialog'), file=sys.stderr)
        return 2
    ui = ui_kdialog.Kdialog(t('ui.title'))
    try:
        config = configuration.load(args.config)
    except configuration.ConfigError as e:
        ui.error(str(e))
        return 2
    return choose(args.video, config, ui, args.count)


def cmd_auto(args: argparse.Namespace) -> int:
    """Run from Dolphin (windows) or in a terminal (`--text`)."""
    if args.text:
        ui: ui_kdialog.Kdialog | ui_terminal.Terminal = ui_terminal.Terminal()
    elif ui_kdialog.available():
        ui = ui_kdialog.Kdialog(t('ui.title'))
    else:
        print(t('err.kdialog'), file=sys.stderr)
        return 2
    try:
        config = configuration.load(args.config)
    except configuration.ConfigError as e:
        ui.error(str(e))
        return 2
    summary = auto.run(args.paths, config, ui)
    return 1 if summary.errors else 0


def cmd_menu(args: argparse.Namespace) -> int:
    if args.action == 'remove':
        removed = menu.remove()
        print(t('menu.removed') if removed else t('menu.none'))
        for path in removed:
            print(f'  {path}')
        return 0
    command = menu.current_command()
    try:
        paths = menu.install(command)
    except (OSError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    print(t('menu.installed', command=command))
    for path in paths:
        print(f'  {path}')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='subdolphin', description=t('cli.description'))
    parser.add_argument('--config', type=Path, metavar='FILE', help=t('cli.config', path=configuration.DEFAULT_PATH))
    parser.add_argument('--debug', action='store_true', help=t('cli.debug'))
    parser.add_argument('--version', action='version', version=f'%(prog)s {version("subdolphin")}')
    commands = parser.add_subparsers(dest='command', required=True)

    def add_command(name: str, key: str) -> argparse.ArgumentParser:
        return commands.add_parser(
            name,
            help=t(key),
            description=t(key),
            epilog=t(f'{key}_epilog'),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

    list_parser = add_command('list', 'cli.list')
    list_parser.add_argument('video', type=Path, metavar='VIDEO', help=t('cli.video'))
    list_parser.add_argument('--title', metavar='TITLE', help=t('cli.title'))
    list_parser.add_argument('-n', '--count', type=int, metavar='N', default=DEFAULT_COUNT,
                             help=t('cli.count', n=DEFAULT_COUNT))  # fmt: skip
    list_parser.add_argument('--json', action='store_true', help=t('cli.json'))

    choose_parser = add_command('choose', 'cli.choose')
    choose_parser.add_argument('video', type=Path, metavar='VIDEO', help=t('cli.video'))
    choose_parser.add_argument('-n', '--count', type=int, metavar='N', default=None, help=t('cli.count_all'))

    auto_parser = add_command('auto', 'cli.auto')
    auto_parser.add_argument('paths', type=Path, nargs='+', metavar='PATH', help=t('cli.paths'))
    auto_parser.add_argument('--text', action='store_true', help=t('cli.text'))

    menu_parser = add_command('menu', 'cli.menu')
    menu_parser.add_argument('action', choices=['install', 'remove'], help=t('cli.menu_action'))
    return parser


def setup_logging(debug: bool) -> None:
    """subliminal's log on standard error with `--debug` (set up as its command line), nothing otherwise."""
    logger = logging.getLogger('subliminal')
    if debug:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    else:
        logger.addHandler(logging.NullHandler())


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.debug)
    if args.command == 'menu':
        return cmd_menu(args)
    if args.command == 'choose':
        return cmd_choose(args)
    if args.command == 'auto':
        return cmd_auto(args)
    try:
        config = configuration.load(args.config)
    except configuration.ConfigError as e:
        print(e, file=sys.stderr)
        return 2
    return cmd_list(args, config)


if __name__ == '__main__':
    sys.exit(main())
