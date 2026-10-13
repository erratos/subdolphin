"""Recherche : refine, liste des candidats (pool de subliminal), score, tri, téléchargement."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta

from subliminal import compute_score, download_subtitles, refine
from subliminal.cache import region
from subliminal.cli.helpers import MutexLock
from subliminal.core import AsyncProviderPool
from subliminal.score import get_scores
from subliminal.subtitle import Subtitle, filter_and_sort_categories
from subliminal.video import Video

from .config import Config

NOMBRE_CANDIDATS = 10


def configurer_cache(config: Config) -> None:
    """Cache partagé avec la CLI de subliminal, réglé comme elle (`subliminal/cli/cli.py`)."""
    if region.is_configured:
        return
    config.dossier_cache.mkdir(parents=True, exist_ok=True)
    region.configure(
        'dogpile.cache.dbm',
        expiration_time=timedelta(days=30),
        arguments={'filename': os.fspath(config.dossier_cache / 'subliminal.dbm'), 'lock_factory': MutexLock},
    )


def affiner(video: Video, config: Config) -> None:
    """Complète la vidéo avec les refiners de la config (empreintes, TMDB…), comme la CLI.

    `metadata` est sauté : `analyse.analyser` l'a déjà appliqué.
    """
    configurer_cache(config)
    refine(
        video,
        refiners=[r for r in config.refiners if r != 'metadata'],
        refiner_configs=config.configs_refiners,
        providers=list(config.sources),
        languages=set(config.langues),
    )


@dataclass
class Candidat:
    sous_titre: Subtitle = field(repr=False)
    score: int
    score_max: int
    empreinte: bool  # correspondance d'empreinte : synchro assurée

    @classmethod
    def evaluer(cls, sous_titre: Subtitle, video: Video) -> Candidat:
        return cls(
            sous_titre=sous_titre,
            score=compute_score(sous_titre, video),
            score_max=get_scores(video)['hash'],
            empreinte='hash' in sous_titre.get_matches(video),
        )

    @property
    def pourcentage(self) -> float:
        return 100 * self.score / self.score_max

    @property
    def source(self) -> str:
        return self.sous_titre.provider_name

    @property
    def version(self) -> str:
        return str(self.sous_titre.info)

    @property
    def malentendants(self) -> bool:
        return bool(self.sous_titre.hearing_impaired)

    @property
    def traduction_auto(self) -> bool:
        return bool(getattr(self.sous_titre, 'machine_translated', False))

    @property
    def fps(self) -> float | None:
        return self.sous_titre.fps


def ordonner(sous_titres: Sequence[Subtitle], video: Video, categories: str = '') -> list[Candidat]:
    """Ordre de `download_best_subtitles` : catégories (réglage `subtitle_categories`, qui peut aussi en
    écarter), puis score ; à score égal, l'ordre des sources est gardé."""
    candidats = [Candidat.evaluer(s, video) for s in filter_and_sort_categories(sous_titres, categories)]
    return sorted(candidats, key=lambda c: c.score, reverse=True)


def au_dessus(candidats: Sequence[Candidat], min_score: int) -> list[Candidat]:
    """Candidats au moins à `min_score` % du score maximum, calcul de la CLI (`download_best_subtitles`)."""
    return [c for c in candidats if c.score >= c.score_max * min_score // 100]


def lister(video: Video, config: Config) -> list[Candidat]:
    """Tous les candidats, du meilleur au moins bon.

    Par le pool de sources, comme la CLI : `subliminal.list_subtitles` saute les vidéos qui ont déjà la
    langue (même en piste intégrée), alors qu'on veut pouvoir en télécharger un autre (R2).
    """
    configurer_cache(config)
    with AsyncProviderPool(
        max_workers=config.max_workers,
        providers=list(config.sources),
        provider_configs=config.configs_sources,
    ) as pool:
        sous_titres = pool.list_subtitles(video, set(config.langues))
    return ordonner(sous_titres, video, config.categories)


def telecharger(candidat: Candidat, config: Config) -> bool:
    """Télécharge le contenu du candidat ; False en cas d'échec (détails : `subdolphin --debug`)."""
    download_subtitles(
        [candidat.sous_titre],
        providers=[candidat.source],
        provider_configs=config.configs_sources,
    )
    return candidat.sous_titre.is_valid()
