"""Fenêtres kdialog (aucune logique métier)."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager

#: Taille de la liste des candidats : assez large pour les noms de version.
TAILLE_LISTE = '1100x560'


class Kdialog:
    """Fenêtres kdialog. Chaque question renvoie None si l'utilisateur annule."""

    def __init__(self, titre: str) -> None:
        self.titre = titre

    def _kdialog(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['kdialog', '--title', self.titre, *arguments], capture_output=True, text=True)

    def choisir(self, texte: str, choix: Sequence[tuple[str, str]]) -> str | None:
        """Liste de lignes `(étiquette, texte)` ; renvoie l'étiquette choisie."""
        lignes = [element for ligne in choix for element in ligne]
        resultat = self._kdialog('--geometry', TAILLE_LISTE, '--menu', texte, *lignes)
        etiquette = resultat.stdout.strip()
        return etiquette if resultat.returncode == 0 and etiquette else None

    def cocher(self, texte: str, cases: Sequence[tuple[str, str, bool]]) -> list[str] | None:
        """Cases `(étiquette, texte, cochée)` ; renvoie les étiquettes cochées."""
        lignes = [element for e, texte_case, cochee in cases for element in (e, texte_case, 'on' if cochee else 'off')]
        resultat = self._kdialog('--separate-output', '--checklist', texte, *lignes)
        return resultat.stdout.split() if resultat.returncode == 0 else None

    def saisir(self, texte: str, defaut: str) -> str | None:
        resultat = self._kdialog('--inputbox', texte, defaut)
        return resultat.stdout.rstrip('\n') if resultat.returncode == 0 else None

    def informer(self, texte: str) -> None:
        self._kdialog('--msgbox', texte)

    def erreur(self, texte: str) -> None:
        self._kdialog('--error', texte)

    def notifier(self, texte: str) -> None:
        """Notification passive, sans attendre qu'elle disparaisse."""
        subprocess.Popen(
            ['kdialog', '--title', self.titre, '--passivepopup', texte, '5'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @contextmanager
    def _barre(self, texte: str, maximum: int, annulable: bool) -> Iterator[Barre]:
        """Barre de progression kdialog, pilotée par D-Bus, fermée à la fin du bloc `with`."""
        resultat = self._kdialog('--progressbar', texte, str(maximum))
        reference = resultat.stdout.split()
        barre = Barre(reference if resultat.returncode == 0 and len(reference) == 2 else None)
        if annulable:
            barre.appel('showCancelButton', 'true')
        try:
            yield barre
        finally:
            barre.appel('close')

    @contextmanager
    def attente(self, texte: str) -> Iterator[None]:
        """Fenêtre d'attente (barre qui tourne) pendant le bloc `with`."""
        with self._barre(texte, 0, annulable=False):
            yield

    def progression(self, texte: str, total: int) -> AbstractContextManager[Barre]:
        """Barre « vidéo n / total » avec bouton Annuler."""
        return self._barre(texte, total, annulable=True)


class Barre:
    """Barre de progression ouverte (`reference` : service et objet D-Bus ; None : pas de fenêtre)."""

    def __init__(self, reference: list[str] | None) -> None:
        self.reference = reference
        self.qdbus = shutil.which('qdbus6') or shutil.which('qdbus')

    def appel(self, *arguments: str) -> str:
        if self.reference is None or self.qdbus is None:
            return ''
        resultat = subprocess.run([self.qdbus, *self.reference, *arguments], capture_output=True, text=True)
        return resultat.stdout.strip()

    def avancer(self, rang: int, texte: str) -> None:
        self.appel('Set', '', 'value', str(rang))
        self.appel('setLabelText', texte)

    def annule(self) -> bool:
        return self.appel('wasCancelled') == 'true'


def disponible() -> bool:
    return shutil.which('kdialog') is not None
