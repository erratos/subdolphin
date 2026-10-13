from pathlib import Path

import pytest
from babelfish import Language

from subdolphin.config import ConfigError, load, parse

PATH = Path('/tmp/subliminal.toml')

# Same structure as a real configuration, with fake secrets.
DATA = {
    'download': {
        'language': ['fr'],
        'name': ['s|^/run/media/[^/]+/[^/]+/||'],
        'ignore_refiner': ['omdb'],
        'ignore_provider': ['podnapisi'],
    },
    'provider': {
        'opensubtitlescom': {'username': 'fake-user', 'password': 'fake-password', 'max_result_pages': 10},
        'addic7ed': {'username': 'fake-user', 'password': 'fake-password'},
    },
    'refiner': {'tmdb': {'apikey': 'fake-key'}},
}


def test_read_as_the_command_line() -> None:
    config = parse(DATA, PATH)
    assert config.languages == {Language('fra')}
    assert 'podnapisi' not in config.providers
    assert {'opensubtitlescom', 'addic7ed', 'gestdown', 'opensubtitles'} <= set(config.providers)
    assert config.refiners == ('hash', 'metadata', 'tmdb', 'tvdb')
    assert config.provider_configs['opensubtitlescom']['max_result_pages'] == 10
    assert config.refiner_configs == {'tmdb': {'apikey': 'fake-key'}}


def test_no_secret_in_repr() -> None:
    assert 'fake' not in repr(parse(DATA, PATH))


def test_selected_providers() -> None:
    config = parse({'download': {'language': 'fr', 'provider': ['addic7ed'], 'extend_provider': ['gestdown']}}, PATH)
    assert config.providers == ('addic7ed', 'gestdown')


def test_ignore_all() -> None:
    assert parse({'download': {'language': ['fr'], 'ignore_provider': ['ALL']}}, PATH).providers == ()


@pytest.mark.parametrize(
    'data',
    [
        {},
        {'download': {'language': []}},
        {'download': {'language': ['not-a-language']}},
        {'download': {'language': ['fr'], 'name': ['s|(|x|']}},
    ],
)
def test_unusable_configuration(data: dict) -> None:
    with pytest.raises(ConfigError):
        parse(data, PATH)


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        ('/run/media/user/External Disk/[Movies]/Film (2006).mkv', '[Movies]/Film (2006).mkv'),
        ('/media/user/Disk/Series/S1/Serie S01E02.mkv', 'Series/S1/Serie S01E02.mkv'),
        ('/home/user/Videos/Film.mkv', '/home/user/Videos/Film.mkv'),
    ],
)
def test_guessit_name(path: str, expected: str) -> None:
    assert parse(DATA, PATH).guessit_name(path) == expected
    # Without a pattern in the configuration, the built-in rule gives the same result.
    assert parse({'download': {'language': ['fr']}}, PATH).guessit_name(path) == expected


def test_configuration_pattern_before_built_in_rule() -> None:
    data = {'download': {'language': ['fr'], 'name': ['s|^/home/[^/]+/||']}}
    assert parse(data, PATH).guessit_name('/home/user/Videos/Film.mkv') == 'Videos/Film.mkv'


def test_fixed_name() -> None:
    data = {'download': {'language': ['fr'], 'name': 'Fixed.mkv'}}
    assert parse(data, PATH).guessit_name('/run/media/u/D/Film.mkv') == 'Fixed.mkv'


def test_download_settings() -> None:
    data = {'download': {'language': ['fr'], 'min_score': 50, 'subtitle_categories': 'n,hi', 'encoding': ''}}
    config = parse(data, PATH)
    assert (config.min_score, config.subtitle_categories, config.encoding) == (50, 'n,hi', None)
    assert parse({'download': {'language': ['fr']}}, PATH).min_score == 0


def test_cache_dir() -> None:
    assert parse({'download': {'language': ['fr']}}, PATH).cache_dir.name == 'subliminal'
    data = {'default': {'cache_dir': '/tmp/subliminal-cache'}, 'download': {'language': ['fr']}}
    assert parse(data, PATH).cache_dir == Path('/tmp/subliminal-cache')


def test_load_a_file(tmp_path: Path) -> None:
    path = tmp_path / 'subliminal.toml'
    path.write_text('[download]\nlanguage = ["fr", "en"]\n')
    assert load(path).languages == {Language('fra'), Language('eng')}


def test_load_an_invalid_file(tmp_path: Path) -> None:
    path = tmp_path / 'subliminal.toml'
    path.write_text('[download\n')
    with pytest.raises(ConfigError):
        load(path)


def test_load_without_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match='Aucune langue'):
        load(tmp_path / 'missing.toml')
