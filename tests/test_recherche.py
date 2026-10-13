from pathlib import Path

from aides import FauxSousTitre
from subliminal.video import Movie

from subdolphin import recherche
from subdolphin.config import lire
from subdolphin.recherche import Candidat, au_dessus, lister, ordonner, telecharger

FILM = Movie('/v/The Fall (2006).mkv', 'The Fall', year=2006)


def test_candidat_evaluer() -> None:
    candidat = Candidat.evaluer(FauxSousTitre({'title', 'year', 'country'}, malentendants=True), FILM)
    assert (candidat.score, candidat.score_max, candidat.empreinte) == (270, 323, False)
    assert round(candidat.pourcentage, 1) == 83.6
    assert (candidat.source, candidat.malentendants, candidat.version) == ('faux', True, 'Faux.Release.id')
    assert Candidat.evaluer(FauxSousTitre({'hash'}), FILM).empreinte


SOUS_TITRES = [
    FauxSousTitre({'title'}, identifiant='titre'),
    FauxSousTitre({'title', 'year'}, identifiant='titre-annee-hi', malentendants=True),
    FauxSousTitre({'title', 'year'}, identifiant='titre-annee'),
    FauxSousTitre({'hash'}, identifiant='empreinte'),
]


def ids(candidats: list[Candidat]) -> list[str]:
    return [c.sous_titre.id for c in candidats]


def test_ordonner_par_score_ordre_des_sources_garde() -> None:
    assert ids(ordonner(SOUS_TITRES, FILM)) == ['empreinte', 'titre-annee-hi', 'titre-annee', 'titre']


def test_ordonner_selon_les_categories_de_la_config() -> None:
    # « n,hi » : à score égal, les non-malentendants d'abord (ordre de download_best_subtitles).
    assert ids(ordonner(SOUS_TITRES, FILM, 'n,hi')) == ['empreinte', 'titre-annee', 'titre-annee-hi', 'titre']
    # « hi » seul : les autres sont écartés.
    assert ids(ordonner(SOUS_TITRES, FILM, 'hi')) == ['titre-annee-hi']


class FauxPool:
    """Remplace le pool de subliminal : aucune source réelle."""

    reglages: dict = {}

    def __init__(self, **reglages) -> None:
        FauxPool.reglages = reglages

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        pass

    def list_subtitles(self, video, langues):
        return list(SOUS_TITRES)


def test_lister(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(recherche, 'AsyncProviderPool', FauxPool)
    monkeypatch.setattr(recherche, 'configurer_cache', lambda config: None)
    config = lire({'download': {'language': ['fr'], 'subtitle_categories': 'n,hi', 'provider': ['addic7ed']}}, Path('x'))
    assert ids(lister(FILM, config))[:2] == ['empreinte', 'titre-annee']
    assert FauxPool.reglages['providers'] == ['addic7ed']


def test_telecharger(monkeypatch) -> None:
    appels = []

    def faux_download_subtitles(sous_titres, **reglages):
        appels.append(reglages['providers'])
        sous_titres[0].content = b'1\n00:00:01,000 --> 00:00:02,000\nBonjour\n'

    monkeypatch.setattr(recherche, 'download_subtitles', faux_download_subtitles)
    config = lire({'download': {'language': ['fr']}}, Path('x'))
    assert telecharger(Candidat.evaluer(FauxSousTitre(), FILM), config)
    assert appels == [['faux']]


def test_telecharger_echec(monkeypatch) -> None:
    monkeypatch.setattr(recherche, 'download_subtitles', lambda sous_titres, **reglages: None)
    config = lire({'download': {'language': ['fr']}}, Path('x'))
    assert not telecharger(Candidat.evaluer(FauxSousTitre(), FILM), config)


def test_au_dessus_comme_la_cli() -> None:
    candidats = ordonner(SOUS_TITRES, FILM)  # scores 323, 216, 216, 162 sur 323
    assert ids(au_dessus(candidats, 0)) == ['empreinte', 'titre-annee-hi', 'titre-annee', 'titre']
    assert ids(au_dessus(candidats, 50)) == ['empreinte', 'titre-annee-hi', 'titre-annee', 'titre']  # seuil 161
    assert ids(au_dessus(candidats, 51)) == ['empreinte', 'titre-annee-hi', 'titre-annee']
    assert ids(au_dessus(candidats, 100)) == ['empreinte']
