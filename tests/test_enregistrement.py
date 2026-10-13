import os
from pathlib import Path

import pytest
from aides import SRT, FauxSousTitre
from babelfish import Language
from subliminal.core import search_external_subtitles
from subliminal.video import Video

from subdolphin import enregistrement
from subdolphin.analyse import Analyse
from subdolphin.config import lire
from subdolphin.enregistrement import (
    doublon,
    dossier_inscriptible,
    enregistrer,
    fins_possibles,
    normaliser,
    reserver,
)

FR = Language('fra')
CONFIG = lire({'download': {'language': ['fr']}}, Path('/tmp/subliminal.toml'))


def premieres(n: int, **options) -> list[str]:
    options = {'malentendants': False, 'extension': '.srt', 'deja_present': False} | options
    fins = fins_possibles(FR, 'opensubtitlescom', **options)
    return [next(fins) for _ in range(n)]


def test_fins_sans_sous_titre_existant() -> None:
    assert premieres(3) == ['.fr.srt', '.opensubtitlescom.fr.srt', '.opensubtitlescom-2.fr.srt']


def test_fins_malentendants() -> None:
    assert premieres(2, malentendants=True) == ['.fr.hi.srt', '.opensubtitlescom.fr.hi.srt']


def test_fins_avec_sous_titre_existant() -> None:
    assert premieres(3, deja_present=True) == [
        '.opensubtitlescom.fr.srt',
        '.opensubtitlescom-2.fr.srt',
        '.opensubtitlescom-3.fr.srt',
    ]
    assert premieres(1, deja_present=True, malentendants=True, extension='.ass') == ['.opensubtitlescom.fr.hi.ass']


def test_fins_format_de_langue() -> None:
    assert premieres(1, format_langue='alpha3') == ['.fra.srt']


def test_reserver(tmp_path: Path) -> None:
    chemin = tmp_path / 'Film.fr.srt'
    assert reserver(chemin)
    chemin.write_text('contenu')
    assert not reserver(chemin)
    assert chemin.read_text() == 'contenu'


def test_normaliser() -> None:
    espaces = SRT.replace('\n', '\r\n').replace('Au revoir', 'Au revoir   ') + '\n\n\n'
    assert normaliser(espaces) == normaliser(SRT)
    assert normaliser(SRT) != normaliser(SRT.replace('Au revoir', 'À bientôt'))


def analyse_de(tmp_path: Path) -> Analyse:
    video = tmp_path / 'Film.mkv'
    video.touch()
    externes = {tmp_path / f: st for f, st in search_external_subtitles(video).items()}
    return Analyse(chemin=video, nom_guessit=video.name, video=Video(str(video)), externes=externes, pistes=[])


@pytest.mark.parametrize('encodage', ['utf-8', 'utf-8-sig', 'cp1252', 'utf-16'])
def test_doublon_quel_que_soit_l_encodage(tmp_path: Path, encodage: str) -> None:
    (tmp_path / 'Film.fr.srt').write_bytes(SRT.replace('Bonjour', 'Salut').encode('utf-8'))
    assert doublon(SRT, analyse_de(tmp_path).externes) is None
    (tmp_path / 'Film.2.fr.srt').write_bytes(SRT.replace('\n', '\r\n').encode(encodage))
    assert doublon(SRT, analyse_de(tmp_path).externes) == tmp_path / 'Film.2.fr.srt'


def test_enregistrer_premier_sous_titre(tmp_path: Path) -> None:
    resultat = enregistrer(FauxSousTitre(texte=SRT), analyse_de(tmp_path), CONFIG)
    assert resultat.chemin == tmp_path / 'Film.fr.srt'
    assert resultat.chemin.read_text(encoding='utf-8') == SRT


def test_enregistrer_a_cote_d_un_existant(tmp_path: Path) -> None:
    (tmp_path / 'Film.fr.srt').write_text('autre chose')
    resultat = enregistrer(FauxSousTitre(texte=SRT, malentendants=True), analyse_de(tmp_path), CONFIG)
    assert resultat.chemin == tmp_path / 'Film.faux.fr.hi.srt'
    assert (tmp_path / 'Film.fr.srt').read_text() == 'autre chose'


def test_enregistrer_noms_pris(tmp_path: Path) -> None:
    analyse = analyse_de(tmp_path)
    (tmp_path / 'Film.faux.fr.srt').write_text('pris')
    (tmp_path / 'Film.faux-2.fr.srt').write_text('pris')
    # Film.fr.srt apparaît après l'analyse (autre lancement) : il n'est pas écrasé.
    (tmp_path / 'Film.fr.srt').write_text('autre lancement')
    resultat = enregistrer(FauxSousTitre(texte=SRT), analyse, CONFIG)
    assert resultat.chemin == tmp_path / 'Film.faux-3.fr.srt'
    assert [(tmp_path / n).read_text() for n in ('Film.fr.srt', 'Film.faux.fr.srt')] == ['autre lancement', 'pris']


def test_enregistrer_encodage_de_la_config(tmp_path: Path) -> None:
    config = lire({'download': {'language': ['fr'], 'encoding': 'cp1252'}}, Path('/tmp/subliminal.toml'))
    resultat = enregistrer(FauxSousTitre(texte=SRT), analyse_de(tmp_path), config)
    assert resultat.chemin.read_bytes() == SRT.encode('cp1252')


def test_enregistrer_echec_d_ecriture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def panne(*args: object, **kwargs: object) -> None:
        raise OSError('disque plein')

    monkeypatch.setattr(enregistrement, 'save_subtitles', panne)
    analyse = analyse_de(tmp_path)
    with pytest.raises(OSError, match='disque plein'):
        enregistrer(FauxSousTitre(texte=SRT), analyse, CONFIG)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Film.mkv']


def test_enregistrer_sous_titre_vide(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='vide'):
        enregistrer(FauxSousTitre(), analyse_de(tmp_path), CONFIG)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Film.mkv']


def test_doublon_avec_bom_impose_par_la_source(tmp_path: Path) -> None:
    """Cas réel (essai du 13/10/2026) : la source impose `utf-8`, le BOM reste dans le texte téléchargé ;
    le même fichier déjà présent est décodé en `utf-8-sig`, sans BOM."""
    avec_bom = ('\ufeff' + SRT).encode('utf-8')
    (tmp_path / 'Film.fr.srt').write_bytes(avec_bom)
    telecharge = FauxSousTitre()  # encodage imposé : utf-8
    telecharge.content = avec_bom
    assert telecharge.text.startswith('\ufeff')
    assert doublon(telecharge.text, analyse_de(tmp_path).externes) == tmp_path / 'Film.fr.srt'


def test_enregistrer_doublon_meme_mal_nomme(tmp_path: Path) -> None:
    """Le doublon est trouvé même si subliminal ne reconnaît pas la langue du fichier existant."""
    (tmp_path / 'Film.addic7ed.fr.srt').write_text(SRT.replace('\n', '\r\n'), encoding='utf-8')
    resultat = enregistrer(FauxSousTitre(texte=SRT), analyse_de(tmp_path), CONFIG)
    assert (resultat.chemin, resultat.doublon_de) == (None, tmp_path / 'Film.addic7ed.fr.srt')
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Film.addic7ed.fr.srt', 'Film.mkv']


def test_enregistrer_ignore_les_autres_langues(tmp_path: Path) -> None:
    (tmp_path / 'Film.en.srt').write_text('autre chose')
    resultat = enregistrer(FauxSousTitre(texte=SRT), analyse_de(tmp_path), CONFIG)
    assert resultat.chemin == tmp_path / 'Film.fr.srt'


@pytest.mark.skipif(os.geteuid() == 0, reason='root écrit partout')
def test_dossier_inscriptible(tmp_path: Path) -> None:
    video = tmp_path / 'lecture-seule' / 'Film.mkv'
    video.parent.mkdir()
    assert dossier_inscriptible(video)
    video.parent.chmod(0o555)
    try:
        assert not dossier_inscriptible(video)
    finally:
        video.parent.chmod(0o755)
