import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from aides import SRT, FauxSousTitre

from subdolphin import parcours
from subdolphin.config import lire
from subdolphin.parcours import CORRIGER, OPTIONS, choisir, demander_options
from subdolphin.recherche import ordonner

# Seul le nom de fichier est analysé : le dossier temporaire de pytest ne doit pas guider guessit.
CONFIG = lire({'download': {'language': ['fr'], 'name': ['s|^.*/||']}}, Path('/tmp/subliminal.toml'))


class FausseUI:
    """Joue les réponses de l'utilisateur dans l'ordre et note chaque fenêtre."""

    def __init__(self, *reponses: str | None) -> None:
        self.reponses = list(reponses)
        self.fenetres: list[tuple[str, str]] = []
        self.listes: list[list[tuple[str, str]]] = []

    def choisir(self, texte, choix):
        self.fenetres.append(('choisir', texte))
        self.listes.append(choix)
        return self.reponses.pop(0)

    def saisir(self, texte, defaut):
        self.fenetres.append(('saisir', texte))
        return self.reponses.pop(0)

    def cocher(self, texte, cases):
        self.fenetres.append(('cocher', texte))
        self.cases = cases
        return self.reponses.pop(0)

    def informer(self, texte):
        self.fenetres.append(('informer', texte))

    def erreur(self, texte):
        self.fenetres.append(('erreur', texte))

    def notifier(self, texte):
        self.fenetres.append(('notifier', texte))

    @contextmanager
    def attente(self, texte):
        self.fenetres.append(('attente', texte))
        yield

    def genres(self) -> list[str]:
        return [genre for genre, _ in self.fenetres]


@pytest.fixture
def sources(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Fausses sources : deux candidats pour « The Fall », rien pour les autres titres."""
    etat = {'telechargements': [], 'echecs': set(), 'recherches': [], 'configs': []}

    def lister(video, config):
        etat['recherches'].append(video.title)
        etat['configs'].append(config)
        if video.title != 'The Fall':
            return []
        return ordonner(
            [
                FauxSousTitre({'title', 'year'}, identifiant='a', texte=SRT),
                FauxSousTitre({'title'}, identifiant='b', texte=SRT.replace('Bonjour', 'Salut'), malentendants=True),
            ],
            video,
        )

    def telecharger(candidat, config):
        etat['telechargements'].append(candidat.sous_titre.id)
        return candidat.sous_titre.id not in etat['echecs']

    monkeypatch.setattr(parcours, 'affiner', lambda video, config: None)
    monkeypatch.setattr(parcours, 'lister', lister)
    monkeypatch.setattr(parcours, 'telecharger', telecharger)
    return etat


def video(tmp_path: Path, nom: str = 'The Fall (2006).mkv') -> Path:
    chemin = tmp_path / nom
    chemin.touch()
    return chemin


def test_choix_et_enregistrement(tmp_path: Path, sources: dict) -> None:
    ui = FausseUI('0')
    assert choisir(video(tmp_path), CONFIG, ui) == 0
    assert ui.genres() == ['attente', 'choisir', 'attente', 'notifier']
    assert ui.fenetres[-1] == ('notifier', 'Enregistré : The Fall (2006).fr.srt')
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text(encoding='utf-8') == SRT
    assert sources['telechargements'] == ['a']


def test_liste_et_entete(tmp_path: Path, sources: dict) -> None:
    chemin = video(tmp_path)
    (tmp_path / 'The Fall (2006).fr.srt').write_text('autre chose')
    ui = FausseUI(None)
    assert choisir(chemin, CONFIG, ui) == 1
    entete = ui.fenetres[1][1]
    assert entete.startswith('« <b>The Fall (2006)</b> » : 2 sous-titre(s) trouvé(s), du meilleur au moins bon.<br>')
    assert 'Déjà présents : The Fall (2006).fr.srt (fr)' in entete
    assert [e for e, _ in ui.listes[0]] == [CORRIGER, OPTIONS, '0', '1']
    assert ui.listes[0][1][1] == '⚙ Options de cette recherche : langues fr · toutes catégories…'
    assert ui.listes[0][2][1] == '66,9 %  faux — Faux.Release.a'
    assert ui.listes[0][3][1] == '50,2 %  faux — Faux.Release.b · HI'


def test_seuil_min_score_de_la_config(tmp_path: Path, sources: dict) -> None:
    config = lire({'download': {'language': ['fr'], 'name': ['s|^.*/||'], 'min_score': 60}}, Path('x'))
    ui = FausseUI(None)
    assert choisir(video(tmp_path), config, ui) == 1
    assert ui.fenetres[1][1].startswith(
        '« <b>The Fall (2006)</b> » : 2 sous-titre(s) trouvé(s), dont 1 à 60 % ou plus, du meilleur au moins bon.'
    )
    assert [e for e, _ in ui.listes[0]] == [CORRIGER, OPTIONS, '0']


def test_nombre_limite_et_entete_echappe(tmp_path: Path, sources: dict) -> None:
    chemin = video(tmp_path, 'The Fall (2006) <&>.mkv')
    (tmp_path / 'The Fall (2006) <&>.fr.srt').write_text('autre chose')
    ui = FausseUI(None)
    assert choisir(chemin, CONFIG, ui, nombre=1) == 1
    entete = ui.fenetres[1][1]
    assert entete.startswith('« <b>The Fall (2006)</b> » : 2 sous-titre(s) trouvé(s) ; voici les 1 meilleurs.<br>')
    assert 'The Fall (2006) &lt;&amp;&gt;.fr.srt' in entete
    assert [e for e, _ in ui.listes[0]] == [CORRIGER, OPTIONS, '0']


def test_a_cote_d_un_existant_sans_ecraser(tmp_path: Path, sources: dict) -> None:
    chemin = video(tmp_path)
    (tmp_path / 'The Fall (2006).fr.srt').write_text('autre chose')
    assert choisir(chemin, CONFIG, FausseUI('1')) == 0
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text() == 'autre chose'
    assert (tmp_path / 'The Fall (2006).faux.fr.hi.srt').exists()


def test_titre_introuvable_puis_saisi(tmp_path: Path, sources: dict) -> None:
    ui = FausseUI('2006', 'The Fall (2006)', '0')
    assert choisir(video(tmp_path, '2006.mkv'), CONFIG, ui) == 0
    assert ui.genres() == ['saisir', 'saisir', 'attente', 'choisir', 'attente', 'notifier']
    assert 'Titre non reconnu pour « 2006.mkv »' in ui.fenetres[0][1]
    assert '« 2006 » n\'est pas reconnu' in ui.fenetres[1][1]
    assert (tmp_path / '2006.fr.srt').exists()


def test_saisie_annulee(tmp_path: Path, sources: dict) -> None:
    assert choisir(video(tmp_path, '2006.mkv'), CONFIG, FausseUI(None)) == 1


def test_aucun_resultat_puis_titre_corrige(tmp_path: Path, sources: dict) -> None:
    """Sans résultat, la liste s'affiche quand même, avec ses deux lignes d'action."""
    ui = FausseUI(CORRIGER, 'The Fall (2006)', '0')
    assert choisir(video(tmp_path, 'Autre film (1999).mkv'), CONFIG, ui) == 0
    assert ui.fenetres[1][1].startswith('« <b>Autre film (1999)</b> » : aucun sous-titre trouvé.<br>')
    assert [e for e, _ in ui.listes[0]] == [CORRIGER, OPTIONS]
    assert sources['recherches'] == ['Autre film', 'The Fall']


def test_corriger_le_titre_depuis_la_liste(tmp_path: Path, sources: dict) -> None:
    ui = FausseUI(CORRIGER, None, CORRIGER, 'Autre film (1999)', None)
    assert choisir(video(tmp_path), CONFIG, ui) == 1
    # Saisie annulée : retour à la liste ; puis nouveau titre : nouvelle recherche, sans résultat.
    assert ui.genres() == ['attente', 'choisir', 'saisir', 'choisir', 'saisir', 'attente', 'choisir']
    assert sources['recherches'] == ['The Fall', 'Autre film']


def test_echec_de_telechargement_puis_autre_choix(tmp_path: Path, sources: dict) -> None:
    sources['echecs'].add('a')
    ui = FausseUI('0', '1')
    assert choisir(video(tmp_path), CONFIG, ui) == 0
    erreur = next(texte for genre, texte in ui.fenetres if genre == 'erreur')
    assert 'Le téléchargement depuis faux a échoué' in erreur
    assert 'subdolphin --debug choisir' in erreur
    assert sources['telechargements'] == ['a', 'b']


def test_doublon_puis_annulation(tmp_path: Path, sources: dict) -> None:
    chemin = video(tmp_path)
    (tmp_path / 'The Fall (2006).fr.srt').write_text(SRT, encoding='utf-8')
    ui = FausseUI('0', None)
    assert choisir(chemin, CONFIG, ui) == 1
    assert ('informer', 'Ce sous-titre est identique à « The Fall (2006).fr.srt », déjà présent : il n\'a pas été recréé.') in ui.fenetres
    assert sorted(p.name for p in tmp_path.iterdir()) == ['The Fall (2006).fr.srt', 'The Fall (2006).mkv']


def test_video_inutilisable(tmp_path: Path, sources: dict) -> None:
    ui = FausseUI()
    assert choisir(tmp_path / 'absente.mkv', CONFIG, ui) == 2
    assert ui.genres() == ['erreur']


@pytest.mark.skipif(os.geteuid() == 0, reason='root écrit partout')
def test_dossier_en_lecture_seule(tmp_path: Path, sources: dict) -> None:
    chemin = video(tmp_path)
    tmp_path.chmod(0o555)
    try:
        ui = FausseUI()
        assert choisir(chemin, CONFIG, ui) == 2
    finally:
        tmp_path.chmod(0o755)
    assert ui.genres() == ['erreur']
    assert sources['recherches'] == []


def test_options_de_cette_recherche(tmp_path: Path, sources: dict) -> None:
    ui = FausseUI(OPTIONS, ['langue:fr', 'langue:en', 'categorie:hi'], None)
    assert choisir(video(tmp_path), CONFIG, ui) == 1
    assert ui.genres() == ['attente', 'choisir', 'cocher', 'attente', 'choisir']
    assert [(e, coche) for e, _, coche in ui.cases] == [
        ('langue:en', False), ('langue:fr', True),
        ('categorie:n', True), ('categorie:hi', True), ('categorie:fo', True),
    ]  # fmt: skip
    nouvelle = sources['configs'][1]
    assert ({str(lg) for lg in nouvelle.langues}, nouvelle.categories) == ({'fr', 'en'}, 'hi')
    assert ui.listes[1][1][1] == '⚙ Options de cette recherche : langues en, fr · HI…'
    assert CONFIG.categories == ''  # la config de départ n'est pas modifiée


def test_options_incompletes(tmp_path: Path, sources: dict) -> None:
    ui = FausseUI(OPTIONS, ['categorie:n'], None)
    assert choisir(video(tmp_path), CONFIG, ui) == 1
    assert ui.genres() == ['attente', 'choisir', 'cocher', 'informer', 'choisir']
    assert len(sources['configs']) == 1


@pytest.mark.parametrize(
    ('depart', 'cochees', 'attendues'),
    [
        ('', ['n', 'hi', 'fo'], ''),
        ('', ['fo'], 'fo'),
        ('n,hi', ['n', 'hi', 'fo'], 'n,hi,fo'),
        ('hi,n', ['n', 'hi'], 'hi,n'),
    ],
)
def test_ordre_des_categories(depart: str, cochees: list[str], attendues: str) -> None:
    config = lire({'download': {'language': ['fr'], 'subtitle_categories': depart}}, Path('x'))
    ui = FausseUI(['langue:fr', *(f'categorie:{c}' for c in cochees)])
    assert demander_options(config, ui).categories == attendues
