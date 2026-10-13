"""Analyse d'une vidéo : scan (nom substitué), pistes intégrées, sous-titres externes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from subliminal import refine, scan_video
from subliminal.core import search_external_subtitles
from subliminal.exceptions import GuessingError
from subliminal.subtitle import EmbeddedSubtitle, ExternalSubtitle
from subliminal.video import Episode, Movie, Video

from .config import Config

#: Formats de piste intégrée, tels que les donne le refiner `metadata` (noms knowit en minuscules).
FORMATS_IMAGE = {'pgs', 'vobsub', 'dvbsub'}
FORMATS_TEXTE = {'srt', 'ass', 'ssa', 'tx3g', 'mov text', 'webvtt', 'vtt'}


@dataclass
class Analyse:
    chemin: Path
    nom_guessit: str
    video: Video | None  # None : guessit n'a pas reconnu le titre
    externes: dict[Path, ExternalSubtitle]  # trouvés par `search_external_subtitles`
    pistes: list[EmbeddedSubtitle]  # trouvées par le refiner `metadata`


def nature(piste: EmbeddedSubtitle) -> str:
    """'image', 'texte' ou 'inconnue'."""
    if piste.subtitle_format in FORMATS_IMAGE:
        return 'image'
    if piste.subtitle_format in FORMATS_TEXTE:
        return 'texte'
    return 'inconnue'


def titre_lisible(video: Video) -> str:
    """« The Fall (2006) » ou « Doctor Who (2005) S01E02 » : sert aussi à pré-remplir la saisie du titre."""
    if isinstance(video, Episode):
        serie = f'{video.series} ({video.year})' if video.year else video.series
        episodes = ''.join(f'E{e:02d}' for e in video.episodes)
        return f'{serie} S{video.season:02d}{episodes}'
    if isinstance(video, Movie):
        return f'{video.title} ({video.year})' if video.year else video.title
    return os.path.basename(video.name)


def analyser(chemin: str | os.PathLike[str], config: Config, titre: str | None = None) -> Analyse:
    """Analyse une vidéo ; `titre` (saisi à la main) remplace le nom de fichier pour guessit.

    Le refiner `metadata` est appliqué ici (pistes intégrées, fps, résolution…), même si le titre n'est pas
    reconnu. Lève `ValueError` si le fichier n'existe pas ou n'a pas une extension de vidéo.
    """
    chemin = Path(chemin)
    nom = titre.strip() + chemin.suffix if titre else config.nom_pour_guessit(chemin)
    try:
        video = scan_video(chemin, name=nom)
    except GuessingError:
        video = None
    lue = video if video is not None else Video(os.fspath(chemin))
    refine(lue, refiners=['metadata'], embedded_subtitles=True)
    return Analyse(
        chemin=chemin,
        nom_guessit=nom,
        video=video,
        externes={chemin.parent / f: st for f, st in sorted(search_external_subtitles(chemin).items())},
        pistes=[s for s in lue.subtitles if isinstance(s, EmbeddedSubtitle)],
    )
