"""Affichage dans le terminal (`--texte`), pour essayer ou diagnostiquer sans fenêtre."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager


class Terminal:
    @contextmanager
    def progression(self, texte: str, total: int) -> Iterator[Ligne]:
        print(texte, flush=True)
        yield Ligne()

    def informer(self, texte: str) -> None:
        print(texte)

    def erreur(self, texte: str) -> None:
        print(texte, file=sys.stderr)


class Ligne:
    """Progression : une ligne par vidéo ; on annule avec Ctrl+C."""

    def avancer(self, rang: int, texte: str) -> None:
        print(texte, flush=True)

    def annule(self) -> bool:
        return False
