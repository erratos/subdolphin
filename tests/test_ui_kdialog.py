import subprocess

import pytest

from subdolphin import ui_kdialog
from subdolphin.ui_kdialog import Kdialog


class FauxProcessus:
    """Remplace subprocess.run / Popen : note les commandes, renvoie des réponses préparées."""

    def __init__(self, *reponses: tuple[int, str]) -> None:
        self.reponses = list(reponses)
        self.commandes: list[list[str]] = []

    def run(self, commande, **options):
        self.commandes.append(list(commande))
        code, sortie = self.reponses.pop(0) if self.reponses else (0, '')
        return subprocess.CompletedProcess(commande, code, sortie, '')

    def popen(self, commande, **options):
        self.commandes.append(list(commande))


@pytest.fixture
def processus(monkeypatch: pytest.MonkeyPatch):
    def installer(*reponses: tuple[int, str]) -> FauxProcessus:
        faux = FauxProcessus(*reponses)
        monkeypatch.setattr(ui_kdialog.subprocess, 'run', faux.run)
        monkeypatch.setattr(ui_kdialog.subprocess, 'Popen', faux.popen)
        monkeypatch.setattr(ui_kdialog.shutil, 'which', lambda nom: f'/usr/bin/{nom}')
        return faux

    return installer


def test_choisir(processus) -> None:
    faux = processus((0, '1\n'))
    assert Kdialog('Sous-titres').choisir('Texte', [('0', 'premier'), ('1', 'second')]) == '1'
    assert faux.commandes == [
        ['kdialog', '--title', 'Sous-titres', '--geometry', ui_kdialog.TAILLE_LISTE, '--menu', 'Texte',
         '0', 'premier', '1', 'second'],
    ]  # fmt: skip


def test_choisir_annule(processus) -> None:
    processus((1, ''))
    assert Kdialog('T').choisir('Texte', [('0', 'premier')]) is None


def test_cocher(processus) -> None:
    faux = processus((0, 'fr\nhi\n'), (1, ''))
    ui = Kdialog('T')
    assert ui.cocher('Options', [('fr', 'Français', True), ('en', 'Anglais', False), ('hi', 'HI', True)]) == ['fr', 'hi']
    assert faux.commandes[0][3:] == [
        '--separate-output', '--checklist', 'Options', 'fr', 'Français', 'on', 'en', 'Anglais', 'off', 'hi', 'HI', 'on',
    ]
    assert ui.cocher('Options', [('fr', 'Français', True)]) is None


def test_saisir(processus) -> None:
    faux = processus((0, 'The Fall (2006)\n'), (1, ''))
    ui = Kdialog('T')
    assert ui.saisir('Titre ?', 'The Fall') == 'The Fall (2006)'
    assert faux.commandes[0][-3:] == ['--inputbox', 'Titre ?', 'The Fall']
    assert ui.saisir('Titre ?', 'The Fall') is None


def test_messages_et_notification(processus) -> None:
    faux = processus()
    ui = Kdialog('T')
    ui.informer('info')
    ui.erreur('erreur')
    ui.notifier('Enregistré : Film.fr.srt')
    assert [c[3:] for c in faux.commandes] == [
        ['--msgbox', 'info'],
        ['--error', 'erreur'],
        ['--passivepopup', 'Enregistré : Film.fr.srt', '5'],
    ]


def test_attente_ferme_la_fenetre_meme_en_cas_d_erreur(processus) -> None:
    faux = processus((0, 'org.kde.kdialog-42 /ProgressDialog\n'))
    with pytest.raises(RuntimeError), Kdialog('T').attente('Recherche…'):
        raise RuntimeError('panne')
    assert faux.commandes == [
        ['kdialog', '--title', 'T', '--progressbar', 'Recherche…', '0'],
        ['/usr/bin/qdbus6', 'org.kde.kdialog-42', '/ProgressDialog', 'close'],
    ]


def test_attente_sans_fenetre(processus) -> None:
    faux = processus((1, ''))
    with Kdialog('T').attente('Recherche…'):
        pass
    assert len(faux.commandes) == 1  # pas de fenêtre ouverte : rien à fermer


def test_progression_annulable(processus) -> None:
    faux = processus((0, 'org.kde.kdialog-7 /ProgressDialog\n'), (0, ''), (0, ''), (0, ''), (0, 'true\n'), (0, ''))
    with Kdialog('T').progression('Sous-titres automatiques', 3) as barre:
        barre.avancer(1, 'Vidéo 2 / 3 : Film.mkv')
        assert barre.annule()
    qdbus = ['/usr/bin/qdbus6', 'org.kde.kdialog-7', '/ProgressDialog']
    assert faux.commandes == [
        ['kdialog', '--title', 'T', '--progressbar', 'Sous-titres automatiques', '3'],
        [*qdbus, 'showCancelButton', 'true'],
        [*qdbus, 'Set', '', 'value', '1'],
        [*qdbus, 'setLabelText', 'Vidéo 2 / 3 : Film.mkv'],
        [*qdbus, 'wasCancelled'],
        [*qdbus, 'close'],
    ]
