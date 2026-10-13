"""Parcours « Meilleur sous-titre automatique » (PLAN.md 5.3) : ce que fait `subliminal download`."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from babelfish import Language
from subliminal.core import AsyncProviderPool, collect_video_filepaths
from subliminal.score import get_scores
from subliminal.video import VIDEO_EXTENSIONS

from .analyse import Analyse, analyser
from .config import Config
from .enregistrement import dossier_inscriptible, enregistrer
from .recherche import affiner, configurer_cache
from .textes import t

#: Noms montrés par rubrique du bilan (au-delà : « … et N autre(s) »).
NOMS_MAX = 10


class Progression(Protocol):
    def avancer(self, rang: int, texte: str) -> None: ...
    def annule(self) -> bool: ...


class Interface(Protocol):
    """Fenêtres du mode automatique (`ui_kdialog.Kdialog`, `ui_terminal.Terminal`, ou un faux)."""

    def progression(self, texte: str, total: int) -> AbstractContextManager[Progression]: ...
    def informer(self, texte: str) -> None: ...


@dataclass
class Bilan:
    total: int = 0
    traitees: int = 0
    enregistres: list[Path] = field(default_factory=list)  # sous-titres écrits
    deja_pourvues: list[Path] = field(default_factory=list)
    rien_trouve: list[Path] = field(default_factory=list)
    non_reconnues: list[Path] = field(default_factory=list)
    doublons: list[Path] = field(default_factory=list)
    erreurs: list[tuple[Path, str]] = field(default_factory=list)
    annule: bool = False


def collecter(chemins: Iterable[Path]) -> list[Path]:
    """Vidéos à traiter : les fichiers donnés, et celles des dossiers (`collect_video_filepaths`, comme la
    CLI : dossiers cachés, « sample » et liens symboliques ignorés ; pas d'archives)."""
    videos: list[Path] = []
    for chemin in chemins:
        if chemin.is_dir():
            videos += [Path(p) for p in collect_video_filepaths(chemin, archives=False)]
        elif chemin.name.lower().endswith(VIDEO_EXTENSIONS):
            videos.append(chemin)
    return list(dict.fromkeys(videos))


def langues_a_chercher(analyse: Analyse, config: Config) -> set[Language]:
    """Comme la CLI : langues de la config moins celles déjà présentes, sauf réglages `force*`."""
    presentes: set[Language] = set()
    if not (config.force or config.force_externes):
        presentes |= {s.language for s in analyse.externes.values()}
    if not (config.force or config.force_integres):
        presentes |= {p.language for p in analyse.pistes}
    return set(config.langues) - presentes


def traiter(chemin: Path, config: Config, pool: AsyncProviderPool, bilan: Bilan) -> None:
    """Une vidéo : analyse, choix et téléchargement par subliminal, enregistrement sans écraser."""
    analyse = analyser(chemin, config)
    if analyse.video is None:
        bilan.non_reconnues.append(chemin)
        return
    langues = langues_a_chercher(analyse, config)
    if not langues:
        bilan.deja_pourvues.append(chemin)
        return
    if not dossier_inscriptible(chemin):
        bilan.erreurs.append((chemin, t('auto.lecture_seule')))
        return
    video = analyse.video
    affiner(video, config)
    telecharges = pool.download_best_subtitles(
        pool.list_subtitles(video, langues),
        video,
        langues,
        min_score=get_scores(video)['hash'] * config.min_score // 100,
        subtitle_categories=config.categories,
        skip_wrong_fps=config.skip_wrong_fps,
    )
    if not telecharges:
        bilan.rien_trouve.append(chemin)
        return
    for sous_titre in telecharges:
        resultat = enregistrer(sous_titre, analyse, config)
        if resultat.chemin is None:
            bilan.doublons.append(chemin)
        else:
            bilan.enregistres.append(resultat.chemin)


def automatique(chemins: Iterable[Path], config: Config, ui: Interface) -> Bilan:
    """Traite toutes les vidéos (annulable entre deux vidéos), puis affiche le bilan."""
    videos = collecter(chemins)
    bilan = Bilan(total=len(videos))
    if videos:
        configurer_cache(config)
        with (
            ui.progression(t('auto.debut', n=len(videos)), len(videos)) as progression,
            AsyncProviderPool(
                max_workers=config.max_workers,
                providers=list(config.sources),
                provider_configs=config.configs_sources,
            ) as pool,
        ):
            for rang, chemin in enumerate(videos):
                if progression.annule():
                    bilan.annule = True
                    break
                progression.avancer(rang, t('auto.video', rang=rang + 1, total=len(videos), nom=chemin.name))
                try:
                    traiter(chemin, config, pool, bilan)
                except Exception as e:  # noqa: BLE001  # une vidéo en échec n'arrête pas les autres
                    # Message seulement pour les erreurs système : les autres peuvent citer une URL avec clé.
                    erreur = f'{type(e).__name__} : {e}' if isinstance(e, OSError) else type(e).__name__
                    bilan.erreurs.append((chemin, erreur))
                bilan.traitees += 1
    ui.informer(texte_bilan(bilan, config))
    return bilan


def texte_bilan(bilan: Bilan, config: Config) -> str:
    if not bilan.total:
        return t('auto.aucune_video')

    def noms(chemins: list[Path]) -> list[str]:
        lignes = [f'    {c.name}' for c in chemins[:NOMS_MAX]]
        if len(chemins) > NOMS_MAX:
            lignes.append('    ' + t('auto.autres', n=len(chemins) - NOMS_MAX))
        return lignes

    rien = (
        t('auto.rien_trouve', seuil=config.min_score, n=len(bilan.rien_trouve))
        if config.min_score
        else t('auto.rien_trouve_sans_seuil', n=len(bilan.rien_trouve))
    )
    lignes = [t('auto.bilan_titre', n=bilan.total), '']
    lignes += [t('auto.enregistres', n=len(bilan.enregistres)), *noms(bilan.enregistres)]
    lignes += [t('auto.deja_pourvues', n=len(bilan.deja_pourvues))]
    lignes += [rien, *noms(bilan.rien_trouve)]
    lignes += [t('auto.non_reconnues', n=len(bilan.non_reconnues)), *noms(bilan.non_reconnues)]
    if bilan.doublons:
        lignes += [t('auto.doublons', n=len(bilan.doublons)), *noms(bilan.doublons)]
    if bilan.erreurs:
        lignes += [t('auto.erreurs', n=len(bilan.erreurs))]
        lignes += [f'    {c.name} : {erreur}' for c, erreur in bilan.erreurs[:NOMS_MAX]]
    if bilan.annule:
        lignes += ['', t('auto.annule', fait=bilan.traitees, total=bilan.total)]
    if bilan.erreurs or bilan.rien_trouve:
        lignes += ['', t('auto.aide')]
    return '\n'.join(lignes)
