from contextlib import contextmanager
from pathlib import Path

import pytest
from aides import SRT, FauxSousTitre
from babelfish import Language
from subliminal.subtitle import EmbeddedSubtitle, ExternalSubtitle
from subliminal.video import Video

from subdolphin import auto
from subdolphin.analyse import Analyse
from subdolphin.auto import automatique, collecter, langues_a_chercher
from subdolphin.config import lire

FR = Language('fra')


def config(**download):
    # Seul le nom de fichier est analysé : le dossier temporaire de pytest ne doit pas guider guessit.
    return lire({'download': {'language': ['fr'], 'name': ['s|^.*/||'], **download}}, Path('/tmp/subliminal.toml'))


def test_collecter(tmp_path: Path) -> None:
    for nom in ('a.mkv', 'b.avi', 'notes.txt', '.cachee.mkv', 'sample.mkv', 'S/c.mkv', '.cache/d.mkv', 'Sample/e.mkv'):
        (tmp_path / nom).parent.mkdir(exist_ok=True)
        (tmp_path / nom).touch()
    (tmp_path / 'lien.mkv').symlink_to(tmp_path / 'a.mkv')
    seule = tmp_path / 'S' / 'c.mkv'
    trouvees = collecter([tmp_path, seule, tmp_path / 'notes.txt', tmp_path / 'lien.mkv'])
    assert [p.relative_to(tmp_path).as_posix() for p in trouvees] == ['a.mkv', 'b.avi', 'S/c.mkv', 'lien.mkv']


def analyse_avec(externes=(), pistes=()) -> Analyse:
    return Analyse(
        chemin=Path('/v/Film.mkv'),
        nom_guessit='Film.mkv',
        video=Video('/v/Film.mkv'),
        externes={Path(f'/v/Film.{lg}.srt'): ExternalSubtitle(Language.fromietf(lg), 'x') for lg in externes},
        pistes=[EmbeddedSubtitle.from_video_path(Language.fromietf(lg), video_path='/v/Film.mkv') for lg in pistes],
    )


@pytest.mark.parametrize(
    ('externes', 'pistes', 'reglages', 'attendues'),
    [
        ((), (), {}, {FR}),
        (('fr',), (), {}, set()),
        ((), ('fr',), {}, set()),
        (('en',), ('en',), {}, {FR}),
        (('fr',), ('fr',), {'force': True}, {FR}),
        (('fr',), (), {'force_external_subtitles': True}, {FR}),
        (('fr',), (), {'force_embedded_subtitles': True}, set()),
        ((), ('fr',), {'force_embedded_subtitles': True}, {FR}),
    ],
)
def test_langues_a_chercher_comme_la_cli(externes, pistes, reglages, attendues) -> None:
    assert langues_a_chercher(analyse_avec(externes, pistes), config(**reglages)) == attendues


class FauxPool:
    """Pool de subliminal factice : « The Fall » a un sous-titre, « Panne » plante, le reste n'a rien."""

    reglages: list[dict] = []

    def __init__(self, **options) -> None:
        FauxPool.reglages = []

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        pass

    def list_subtitles(self, video, langues):
        if video.title == 'Panne':
            raise RuntimeError('panne')
        return [FauxSousTitre({'title', 'year'}, texte=SRT)] if video.title == 'The Fall' else []

    def download_best_subtitles(self, sous_titres, video, langues, **options):
        FauxPool.reglages.append(options)
        return sous_titres


class FausseUI:
    def __init__(self, annuler_apres: int | None = None) -> None:
        self.annuler_apres = annuler_apres
        self.avancees: list[str] = []
        self.bilan = ''

    @contextmanager
    def progression(self, texte, total):
        yield self

    def avancer(self, rang, texte):
        self.avancees.append(texte)

    def annule(self):
        return self.annuler_apres is not None and len(self.avancees) >= self.annuler_apres

    def informer(self, texte):
        self.bilan = texte


@pytest.fixture(autouse=True)
def sans_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auto, 'AsyncProviderPool', FauxPool)
    monkeypatch.setattr(auto, 'affiner', lambda video, config: None)
    monkeypatch.setattr(auto, 'configurer_cache', lambda config: None)


def videos(dossier: Path, *noms: str) -> list[Path]:
    for nom in noms:
        (dossier / nom).touch()
    return [dossier / nom for nom in noms]


def test_bilan_complet(tmp_path: Path) -> None:
    videos(tmp_path, 'The Fall (2006).mkv', 'Pourvu (2001).mkv', '2006.mkv', 'Rien (1999).mkv', 'Panne (2000).mkv')
    (tmp_path / 'Pourvu (2001).fr.srt').write_text('déjà là')
    ui = FausseUI()
    bilan = automatique([tmp_path], config(min_score=50), ui)
    assert [c.name for c in bilan.enregistres] == ['The Fall (2006).fr.srt']
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text(encoding='utf-8') == SRT
    assert [c.name for c in bilan.deja_pourvues] == ['Pourvu (2001).mkv']
    assert [c.name for c in bilan.non_reconnues] == ['2006.mkv']
    assert [c.name for c in bilan.rien_trouve] == ['Rien (1999).mkv']
    assert bilan.erreurs == [(tmp_path / 'Panne (2000).mkv', 'RuntimeError')]
    assert (bilan.traitees, bilan.annule) == (5, False)
    # Réglages de la config passés à download_best_subtitles, comme la CLI (323 × 50 // 100).
    assert FauxPool.reglages[0] == {'min_score': 161, 'subtitle_categories': '', 'skip_wrong_fps': False}
    assert ui.avancees[0] == 'Vidéo 1 / 5 : 2006.mkv'
    assert 'Enregistrés : 1\n    The Fall (2006).fr.srt' in ui.bilan
    assert 'Rien trouvé à 50 % ou plus : 1\n    Rien (1999).mkv' in ui.bilan
    assert 'Erreurs : 1\n    Panne (2000).mkv : RuntimeError' in ui.bilan
    assert 'subdolphin --debug auto --texte' in ui.bilan


def test_force_et_doublon(tmp_path: Path) -> None:
    (chemin,) = videos(tmp_path, 'The Fall (2006).mkv')
    (tmp_path / 'The Fall (2006).fr.srt').write_text(SRT, encoding='utf-8')
    bilan = automatique([chemin], config(force=True), FausseUI())
    assert (bilan.enregistres, bilan.doublons) == ([], [chemin])
    assert sorted(p.name for p in tmp_path.iterdir()) == ['The Fall (2006).fr.srt', 'The Fall (2006).mkv']


def test_force_sans_doublon_ne_remplace_rien(tmp_path: Path) -> None:
    (chemin,) = videos(tmp_path, 'The Fall (2006).mkv')
    (tmp_path / 'The Fall (2006).fr.srt').write_text('autre chose')
    bilan = automatique([chemin], config(force=True), FausseUI())
    assert [c.name for c in bilan.enregistres] == ['The Fall (2006).faux.fr.srt']
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text() == 'autre chose'


def test_annulation(tmp_path: Path) -> None:
    videos(tmp_path, 'A (2001).mkv', 'B (2002).mkv', 'C (2003).mkv')
    ui = FausseUI(annuler_apres=1)
    bilan = automatique([tmp_path], config(), ui)
    assert (bilan.traitees, bilan.total, bilan.annule) == (1, 3, True)
    assert 'Annulé après 1 vidéo(s) sur 3.' in ui.bilan


def test_aucune_video(tmp_path: Path) -> None:
    ui = FausseUI()
    assert automatique([tmp_path], config(), ui).total == 0
    assert ui.bilan.startswith('Aucune vidéo trouvée.')
