"""Enregistrement : choix du nom, dédoublonnage, écriture sans écrasement (via `save_subtitles`)."""

from __future__ import annotations

import itertools
import os
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from babelfish import Language
from subliminal import save_subtitles
from subliminal.subtitle import FORMAT_TO_EXTENSION, ExternalSubtitle, Subtitle, get_subtitle_path, get_subtitle_suffix

from .analyse import Analyse
from .config import Config

#: Au-delà, on renonce (`Film.<source>-100.fr.srt` : quelque chose ne va pas).
ESSAIS_MAX = 100


def fins_possibles(
    langue: Language,
    source: str,
    *,
    malentendants: bool,
    extension: str,
    deja_present: bool,
    format_langue: str = 'alpha2',
) -> Iterator[str]:
    """Fins de nom à essayer dans l'ordre (PLAN.md 5.4) : `.fr.srt` s'il n'y a encore aucun sous-titre
    dans cette langue, puis `.<source>.fr.srt`, `.<source>-2.fr.srt`, etc.

    `.hi` est ajouté à la main : le suffixe `[hi]` de subliminal n'est pas compris par mpv (PLAN.md 4.4).
    """
    fin = f'{get_subtitle_suffix(langue, language_format=format_langue)}{".hi" if malentendants else ""}{extension}'
    if not deja_present:
        yield fin
    yield f'.{source}{fin}'
    for n in itertools.count(2):
        yield f'.{source}-{n}{fin}'


def reserver(chemin: Path) -> bool:
    """Crée `chemin` vide, seulement s'il n'existe pas (`O_EXCL`) : aucun fichier existant n'est jamais
    remplacé, même si un autre lancement écrit au même moment. False si le nom est déjà pris."""
    try:
        os.close(os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644))
    except FileExistsError:
        return False
    return True


def normaliser(texte: str) -> str:
    """Texte comparable : sans BOM, fins de ligne unifiées, espaces de fin de ligne et lignes vides en trop
    retirés.

    subliminal ne suffit pas : il retire le BOM seulement quand il devine l'encodage (`utf-8-sig`), pas
    quand la source l'impose (`utf-8`) ; et il unifie les fins de ligne sur les octets (pas en UTF-16).
    """
    texte = texte.lstrip('\ufeff').replace('\r\n', '\n')
    texte = '\n'.join(ligne.rstrip() for ligne in texte.split('\n'))
    return re.sub(r'\n{3,}', '\n\n', texte).strip()


def doublon(texte: str, externes: Mapping[Path, ExternalSubtitle]) -> Path | None:
    """Premier sous-titre déjà présent (toutes langues) identique à `texte`, ou None.

    Le texte existant est décodé par subliminal (encodage deviné, BOM, fins de ligne).
    """
    reference = normaliser(texte)
    for chemin, existant in externes.items():
        try:
            existant.content = chemin.read_bytes()
        except OSError:
            continue
        if normaliser(existant.text) == reference:
            return chemin
    return None


@dataclass
class Enregistrement:
    chemin: Path | None  # fichier écrit, ou None si doublon
    doublon_de: Path | None = None


def dossier_inscriptible(chemin_video: Path) -> bool:
    """À vérifier **avant** de télécharger, pour ne pas consommer de quota pour rien."""
    return os.access(chemin_video.parent, os.W_OK)


def enregistrer(sous_titre: Subtitle, analyse: Analyse, config: Config) -> Enregistrement:
    """Enregistre un sous-titre déjà téléchargé à côté de la vidéo, sans rien écraser.

    L'écriture est celle de subliminal (`save_subtitles`, avec l'encodage et le format de la config) ; le
    nom est d'abord réservé, car `save_subtitles` écrase un fichier existant.
    """
    video = analyse.video
    if video is None:
        raise ValueError('vidéo non reconnue')
    if identique := doublon(sous_titre.text, analyse.externes):
        return Enregistrement(chemin=None, doublon_de=identique)
    fins = fins_possibles(
        sous_titre.language,
        sous_titre.provider_name,
        malentendants=bool(sous_titre.hearing_impaired),
        extension=FORMAT_TO_EXTENSION.get(config.format_sous_titres or sous_titre.subtitle_format, '.srt'),
        deja_present=any(s.language == sous_titre.language for s in analyse.externes.values()),
        format_langue=config.format_langue,
    )
    for fin in itertools.islice(fins, ESSAIS_MAX):
        chemin = Path(get_subtitle_path(video.name, extension=fin))
        if not reserver(chemin):
            continue
        try:
            enregistres = save_subtitles(
                video,
                [sous_titre],
                single=True,
                extension=fin,
                encoding=config.encodage,
                subtitle_format=config.format_sous_titres,
            )
        except BaseException:
            chemin.unlink(missing_ok=True)
            raise
        if not enregistres:  # sous-titre sans contenu : save_subtitles l'ignore
            chemin.unlink(missing_ok=True)
            raise ValueError('sous-titre vide')
        return Enregistrement(chemin=chemin)
    raise FileExistsError(f'{ESSAIS_MAX} noms déjà pris')
