"""Objets factices partagés par les tests (aucun réseau)."""

from __future__ import annotations

from collections.abc import Iterable

from babelfish import Language
from subliminal.subtitle import Subtitle
from subliminal.video import Video



class FauxSousTitre(Subtitle):
    provider_name = 'faux'

    def __init__(
        self,
        correspondances: Iterable[str] = (),
        *,
        langue: str = 'fr',
        malentendants: bool = False,
        telechargements: int = 0,
        texte: str | None = None,
        identifiant: str = 'id',
    ) -> None:
        super().__init__(Language.fromietf(langue), identifiant, hearing_impaired=malentendants, encoding='utf-8')
        self._correspondances = set(correspondances)
        self.download_count = telechargements
        if texte is not None:
            self.content = texte.encode('utf-8')

    def get_matches(self, video: Video) -> set[str]:
        return set(self._correspondances)

    @property
    def info(self) -> str:
        return f'Faux.Release.{self.id}'


SRT = '1\n00:00:01,000 --> 00:00:02,000\nBonjour, cœur’\n\n2\n00:00:03,000 --> 00:00:04,000\nAu revoir\n'
