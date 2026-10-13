from pathlib import Path

import pytest
from babelfish import Language

from subdolphin.config import ErreurConfig, charger, lire

CHEMIN = Path('/tmp/subliminal.toml')

# Même structure que la vraie config (PLAN.md section 2), avec des secrets factices.
DONNEES = {
    'download': {
        'language': ['fr'],
        'name': ['s|^/run/media/[^/]+/[^/]+/||'],
        'ignore_refiner': ['omdb'],
        'ignore_provider': ['podnapisi'],
    },
    'provider': {
        'opensubtitlescom': {'username': 'pseudo-factice', 'password': 'mot-de-passe-factice', 'max_result_pages': 10},
        'addic7ed': {'username': 'pseudo-factice', 'password': 'mot-de-passe-factice'},
    },
    'refiner': {'tmdb': {'apikey': 'cle-factice'}},
}


def test_lecture_comme_la_cli() -> None:
    config = lire(DONNEES, CHEMIN)
    assert config.langues == {Language('fra')}
    assert 'podnapisi' not in config.sources
    assert {'opensubtitlescom', 'addic7ed', 'gestdown', 'opensubtitles'} <= set(config.sources)
    assert config.refiners == ('hash', 'metadata', 'tmdb', 'tvdb')
    assert config.configs_sources['opensubtitlescom']['max_result_pages'] == 10
    assert config.configs_refiners == {'tmdb': {'apikey': 'cle-factice'}}


def test_secrets_absents_du_repr() -> None:
    texte = repr(lire(DONNEES, CHEMIN))
    assert 'factice' not in texte


def test_liste_de_sources_imposee() -> None:
    config = lire({'download': {'language': 'fr', 'provider': ['addic7ed'], 'extend_provider': ['gestdown']}}, CHEMIN)
    assert config.sources == ('addic7ed', 'gestdown')


def test_ignorer_tout() -> None:
    assert lire({'download': {'language': ['fr'], 'ignore_provider': ['ALL']}}, CHEMIN).sources == ()


@pytest.mark.parametrize(
    'donnees',
    [
        {},
        {'download': {'language': []}},
        {'download': {'language': ['pas-une-langue']}},
        {'download': {'language': ['fr'], 'name': ['s|(|x|']}},
    ],
)
def test_config_inutilisable(donnees: dict) -> None:
    with pytest.raises(ErreurConfig):
        lire(donnees, CHEMIN)


@pytest.mark.parametrize(
    ('chemin', 'attendu'),
    [
        ('/run/media/user/External Disk/[Movies]/Film (2006).mkv', '[Movies]/Film (2006).mkv'),
        ('/media/user/Disk/Series/S1/Serie S01E02.mkv', 'Series/S1/Serie S01E02.mkv'),
        ('/home/user/Videos/Film.mkv', '/home/user/Videos/Film.mkv'),
    ],
)
def test_nom_pour_guessit(chemin: str, attendu: str) -> None:
    assert lire(DONNEES, CHEMIN).nom_pour_guessit(chemin) == attendu
    # Sans motif dans la config, la règle intégrée donne le même résultat.
    assert lire({'download': {'language': ['fr']}}, CHEMIN).nom_pour_guessit(chemin) == attendu


def test_motif_de_la_config_avant_la_regle_integree() -> None:
    donnees = {'download': {'language': ['fr'], 'name': ['s|^/home/[^/]+/||']}}
    assert lire(donnees, CHEMIN).nom_pour_guessit('/home/user/Videos/Film.mkv') == 'Videos/Film.mkv'


def test_nom_fixe() -> None:
    donnees = {'download': {'language': ['fr'], 'name': 'Fixe.mkv'}}
    assert lire(donnees, CHEMIN).nom_pour_guessit('/run/media/u/D/Film.mkv') == 'Fixe.mkv'


def test_reglages_download() -> None:
    donnees = {'download': {'language': ['fr'], 'min_score': 50, 'subtitle_categories': 'n,hi', 'encoding': ''}}
    config = lire(donnees, CHEMIN)
    assert (config.min_score, config.categories, config.encodage) == (50, 'n,hi', None)
    assert lire({'download': {'language': ['fr']}}, CHEMIN).min_score == 0


def test_dossier_de_cache() -> None:
    assert lire({'download': {'language': ['fr']}}, CHEMIN).dossier_cache.name == 'subliminal'
    donnees = {'default': {'cache_dir': '/tmp/cache-subliminal'}, 'download': {'language': ['fr']}}
    assert lire(donnees, CHEMIN).dossier_cache == Path('/tmp/cache-subliminal')


def test_charger_un_fichier(tmp_path: Path) -> None:
    fichier = tmp_path / 'subliminal.toml'
    fichier.write_text('[download]\nlanguage = ["fr", "en"]\n')
    assert charger(fichier).langues == {Language('fra'), Language('eng')}


def test_charger_un_fichier_invalide(tmp_path: Path) -> None:
    fichier = tmp_path / 'subliminal.toml'
    fichier.write_text('[download\n')
    with pytest.raises(ErreurConfig):
        charger(fichier)


def test_charger_sans_fichier(tmp_path: Path) -> None:
    with pytest.raises(ErreurConfig, match='Aucune langue'):
        charger(tmp_path / 'absent.toml')
