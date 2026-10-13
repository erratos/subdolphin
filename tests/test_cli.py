import json
import logging
from pathlib import Path

import pytest
from helpers import FakeSubtitle

from subdolphin import auto, cli
from subdolphin.search import sort_candidates


@pytest.fixture
def config(tmp_path: Path) -> Path:
    path = tmp_path / 'subliminal.toml'
    path.write_text('[download]\nlanguage = ["fr"]\nname = ["s|^.*/||"]\n')
    return path


@pytest.fixture
def no_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replaces the network search: two candidates."""
    monkeypatch.setattr(cli, 'refine_video', lambda video, config: None)
    monkeypatch.setattr(
        cli,
        'list_candidates',
        lambda video, config: sort_candidates(
            [FakeSubtitle({'title'}, subtitle_id='b', hearing_impaired=True), FakeSubtitle({'hash'}, subtitle_id='a')],
            video,
        ),
    )


@pytest.fixture(autouse=True)
def clean_logging():
    """`main` sets up subliminal's logger: restore it after each test."""
    logger = logging.getLogger('subliminal')
    handlers, level = list(logger.handlers), logger.level
    yield
    logger.handlers[:] = handlers
    logger.setLevel(level)


def test_list_unrecognised_title(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str]) -> None:
    video = tmp_path / '2006.mkv'
    video.touch()
    assert cli.main(['--config', str(config), 'list', str(video), '--json']) == 3
    assert json.loads(capsys.readouterr().out)['recognized'] is None


def test_list_text(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], no_providers: None) -> None:
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    (tmp_path / 'The Fall (2006).fr.hi.srt').touch()
    assert cli.main(['--config', str(config), 'list', str(video)]) == 0
    output = capsys.readouterr().out
    assert 'Reconnu : film « The Fall (2006) »' in output
    assert 'The Fall (2006).fr.hi.srt (fr, malentendants)' in output
    assert '  1   100,0 %  ★  fake' in output
    assert '2 candidat(s) trouvé(s), 2 affiché(s).' in output


def test_list_json(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], no_providers: None) -> None:
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    assert cli.main(['--config', str(config), 'list', str(video), '--json', '-n', '1']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['recognized'] == {'type': 'movie', 'title': 'The Fall (2006)'}
    assert result['candidate_count'] == 2
    assert [(c['id'], c['hash_match'], c['provider']) for c in result['candidates']] == [('a', True, 'fake')]


def test_debug_shows_subliminal_log(
    tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], no_providers: None
) -> None:
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    assert cli.main(['--config', str(config), '--debug', 'list', str(video)]) == 0
    assert 'DEBUG:subliminal' in capsys.readouterr().err


def test_help_documents_the_subliminal_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(['list', '--help'])
    assert 'subliminal --debug download -l fr --force -d /tmp/essai' in capsys.readouterr().out


def test_unusable_configuration(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / 'subliminal.toml'
    path.write_text('[download]\n')
    assert cli.main(['--config', str(path), 'list', str(tmp_path / 'x.mkv')]) == 2
    assert 'Aucune langue' in capsys.readouterr().err


def test_missing_video(config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(['--config', str(config), 'list', str(tmp_path / 'missing.mkv')]) == 2
    assert 'Vidéo inutilisable' in capsys.readouterr().err


def test_list_min_score(tmp_path: Path, capsys: pytest.CaptureFixture[str], no_providers: None) -> None:
    path = tmp_path / 'subliminal.toml'
    path.write_text('[download]\nlanguage = ["fr"]\nname = ["s|^.*/||"]\nmin_score = 60\n')
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    assert cli.main(['--config', str(path), 'list', str(video)]) == 0
    output = capsys.readouterr().out
    assert '2 candidat(s) trouvé(s), dont 1 à 60 % ou plus ; 1 affiché(s).' in output


def test_auto_text(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    monkeypatch.setattr(auto, 'configure_cache', lambda config: None)
    (tmp_path / '2006.mkv').touch()
    assert cli.main(['--config', str(config), 'auto', '--text', str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert 'Vidéo 1 / 1 : 2006.mkv' in output
    assert 'Titre non reconnu (utiliser « Choisir un sous-titre… ») : 1\n    2006.mkv' in output


def test_english_interface(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    monkeypatch.setenv('LANG', 'en_US.UTF-8')
    monkeypatch.setattr(auto, 'configure_cache', lambda config: None)
    (tmp_path / '2006.mkv').touch()
    assert cli.main(['--config', str(config), 'auto', '--text', str(tmp_path)]) == 0
    assert 'Title not recognised (use "Choose a subtitle…"): 1' in capsys.readouterr().out


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(['--version'])
    assert capsys.readouterr().out.startswith('subdolphin 0.2.0')
