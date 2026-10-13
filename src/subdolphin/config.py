"""Reads subliminal's TOML configuration: providers, refiners, name substitution."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import babelfish
from babelfish import Language
from platformdirs import PlatformDirs
from subliminal.extensions import get_default_providers, get_default_refiners
from subliminal.utils import NameResolver, merge_extend_and_ignore_unions

from .texts import t

DIRS = PlatformDirs('subliminal')
DEFAULT_PATH = DIRS.user_config_path / 'subliminal.toml'

#: Built-in rule, applied after the configuration's own patterns: strip the mount point, which guessit
#: would take for a title.
DEFAULT_NAME_PATTERNS = ('s|^/run/media/[^/]+/[^/]+/||', 's|^/media/[^/]+/[^/]+/||')


class ConfigError(Exception):
    """Unusable subliminal configuration (message ready to display)."""


@dataclass
class Config:
    """The subliminal settings subdolphin uses.

    `provider_configs` and `refiner_configs` hold secrets: they are left out of `repr` and must never be
    displayed or logged.
    """

    path: Path
    languages: frozenset[Language]
    providers: tuple[str, ...]
    refiners: tuple[str, ...]
    provider_configs: dict[str, dict[str, Any]] = field(repr=False)
    refiner_configs: dict[str, dict[str, Any]] = field(repr=False)
    name_resolvers: tuple[NameResolver, ...] = field(repr=False)
    cache_dir: Path
    max_workers: int | None = None
    #: `[download]` settings passed as is to subliminal (same defaults as its command line).
    encoding: str | None = 'utf-8'  # None: keep the original encoding (`encoding = ""`)
    subtitle_format: str | None = None  # None: keep the original format
    language_format: str = 'alpha2'
    subtitle_categories: str = ''  # e.g. "n,hi", or "fo" (forced only)
    min_score: int = 0  # in % of the maximum score, as the command line
    skip_wrong_fps: bool = False
    #: Automatic mode: download even if the language is already there (`force`), ignoring external files
    #: (`force_external_subtitles`) or embedded tracks (`force_embedded_subtitles`).
    force: bool = False
    force_external: bool = False
    force_embedded: bool = False

    def guessit_name(self, path: str | os.PathLike[str]) -> str:
        """Name passed to guessit: the configuration's patterns, then the built-in rule."""
        name = os.fspath(path)
        for resolver in self.name_resolvers:
            name = resolver(name) or name
        return name


def _lists(section: dict[str, Any], key: str) -> dict[str, list[str]]:
    return {
        'select': list(section.get(key, [])),
        'extend': list(section.get(f'extend_{key}', [])),
        'ignore': list(section.get(f'ignore_{key}', [])),
    }


def parse(data: dict[str, Any], path: Path) -> Config:
    """Builds the `Config` from the already-read TOML, with the rules of subliminal's command line."""
    download = data.get('download', {})
    empty = {'select': [], 'extend': [], 'ignore': []}

    codes = download.get('language', [])
    if isinstance(codes, str):
        codes = [codes]
    try:
        languages = frozenset(Language.fromietf(code) for code in codes)
    except (ValueError, babelfish.Error) as e:
        raise ConfigError(t('err.config_toml', path=path, error=e)) from e
    if not languages:
        raise ConfigError(t('err.config_language', path=path))

    resolvers = []
    name = download.get('name')
    try:
        if name:
            resolvers.append(NameResolver.from_name(name))
        resolvers.append(NameResolver.from_name(DEFAULT_NAME_PATTERNS))
    except ValueError as e:
        raise ConfigError(t('err.config_name', path=path, error=e)) from e

    providers = merge_extend_and_ignore_unions(empty, _lists(download, 'provider'), get_default_providers())
    refiners = merge_extend_and_ignore_unions(empty, _lists(download, 'refiner'), get_default_refiners())

    defaults = data.get('default', {})
    cache_dir = Path(defaults.get('cache_dir', DIRS.user_cache_dir)).expanduser()

    return Config(
        path=path,
        languages=languages,
        providers=tuple(sorted(providers)),
        refiners=tuple(r for r in get_default_refiners() if r in refiners),
        provider_configs={k: dict(v) for k, v in data.get('provider', {}).items()},
        refiner_configs={k: dict(v) for k, v in data.get('refiner', {}).items()},
        name_resolvers=tuple(resolvers),
        cache_dir=cache_dir,
        max_workers=download.get('max_workers'),
        encoding=download.get('encoding', 'utf-8') or None,
        subtitle_format=download.get('subtitle_format') or None,
        language_format=download.get('language_format', 'alpha2'),
        subtitle_categories=download.get('subtitle_categories', ''),
        min_score=int(download.get('min_score', 0)),
        skip_wrong_fps=bool(download.get('skip_wrong_fps', False)),
        force=bool(download.get('force', False)),
        force_external=bool(download.get('force_external_subtitles', False)),
        force_embedded=bool(download.get('force_embedded_subtitles', False)),
    )


def load(path: str | os.PathLike[str] | None = None) -> Config:
    """Reads subliminal's configuration file (missing: default settings)."""
    path = Path(path).expanduser() if path else DEFAULT_PATH
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            with path.open('rb') as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            raise ConfigError(t('err.config_toml', path=path, error=e)) from e
    return parse(data, path)
