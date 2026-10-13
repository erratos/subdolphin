import json
import logging
from pathlib import Path

import pytest
from aides import FauxSousTitre

from subdolphin import cli
from subdolphin.recherche import ordonner


@pytest.fixture
def config(tmp_path: Path) -> Path:
    chemin = tmp_path / 'subliminal.toml'
    chemin.write_text('[download]\nlanguage = ["fr"]\nname = ["s|^.*/||"]\n')
    return chemin


@pytest.fixture
def sans_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remplace la recherche réseau : deux candidats."""
    monkeypatch.setattr(cli, 'affiner', lambda video, config: None)
    monkeypatch.setattr(
        cli,
        'lister',
        lambda video, config: ordonner(
            [FauxSousTitre({'title'}, identifiant='b', malentendants=True), FauxSousTitre({'hash'}, identifiant='a')],
            video,
        ),
    )


@pytest.fixture(autouse=True)
def journal_propre():
    """`main` règle le journal de subliminal : le remettre en état après chaque test."""
    journal = logging.getLogger('subliminal')
    handlers, niveau = list(journal.handlers), journal.level
    yield
    journal.handlers[:] = handlers
    journal.setLevel(niveau)


def test_liste_titre_introuvable(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str]) -> None:
    video = tmp_path / '2006.mkv'
    video.touch()
    assert cli.main(['--config', str(config), 'liste', str(video), '--json']) == 3
    assert json.loads(capsys.readouterr().out)['reconnu'] is None


def test_liste_texte(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], sans_sources: None) -> None:
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    (tmp_path / 'The Fall (2006).fr.hi.srt').touch()
    assert cli.main(['--config', str(config), 'liste', str(video)]) == 0
    sortie = capsys.readouterr().out
    assert 'Reconnu : film « The Fall (2006) »' in sortie
    assert 'The Fall (2006).fr.hi.srt (fr, malentendants)' in sortie
    assert '  1   100,0 %  ★  faux' in sortie
    assert '2 candidat(s) trouvé(s), 2 affiché(s).' in sortie


def test_liste_json(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], sans_sources: None) -> None:
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    assert cli.main(['--config', str(config), 'liste', str(video), '--json', '-n', '1']) == 0
    resultat = json.loads(capsys.readouterr().out)
    assert resultat['reconnu'] == {'type': 'film', 'titre': 'The Fall (2006)'}
    assert resultat['nombre_candidats'] == 2
    assert [(c['id'], c['empreinte']) for c in resultat['candidats']] == [('a', True)]


def test_debug_affiche_le_journal_de_subliminal(
    tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], sans_sources: None
) -> None:
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    assert cli.main(['--config', str(config), '--debug', 'liste', str(video)]) == 0
    assert 'DEBUG:subliminal' in capsys.readouterr().err


def test_aide_documente_la_commande_subliminal(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(['liste', '--help'])
    assert 'subliminal --debug download -l fr --force -d /tmp/essai' in capsys.readouterr().out


def test_config_inutilisable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    chemin = tmp_path / 'subliminal.toml'
    chemin.write_text('[download]\n')
    assert cli.main(['--config', str(chemin), 'liste', str(tmp_path / 'x.mkv')]) == 2
    assert 'Aucune langue' in capsys.readouterr().err


def test_video_absente(config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(['--config', str(config), 'liste', str(tmp_path / 'absente.mkv')]) == 2
    assert 'Vidéo inutilisable' in capsys.readouterr().err


def test_liste_seuil_min_score(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], sans_sources: None
) -> None:
    chemin = tmp_path / 'subliminal.toml'
    chemin.write_text('[download]\nlanguage = ["fr"]\nname = ["s|^.*/||"]\nmin_score = 60\n')
    video = tmp_path / 'The Fall (2006).mkv'
    video.touch()
    assert cli.main(['--config', str(chemin), 'liste', str(video)]) == 0
    sortie = capsys.readouterr().out
    assert '2 candidat(s) trouvé(s), dont 1 à 60 % ou plus ; 1 affiché(s).' in sortie


def test_auto_texte(tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    from subdolphin import auto

    monkeypatch.setattr(auto, 'configurer_cache', lambda config: None)
    (tmp_path / '2006.mkv').touch()
    assert cli.main(['--config', str(config), 'auto', '--texte', str(tmp_path)]) == 0
    sortie = capsys.readouterr().out
    assert 'Vidéo 1 / 1 : 2006.mkv' in sortie
    assert 'Titre non reconnu (utiliser « Choisir… ») : 1\n    2006.mkv' in sortie


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(['--version'])
    assert capsys.readouterr().out.startswith('subdolphin 0.1.0')
