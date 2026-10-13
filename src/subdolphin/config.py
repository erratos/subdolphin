"""Lecture du TOML de subliminal : sources, refiners, substitution de nom."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import babelfish
from babelfish import Language
from platformdirs import PlatformDirs
from subliminal.extensions import get_default_providers, get_default_refiners
from subliminal.utils import NameResolver, merge_extend_and_ignore_unions

from .textes import t

DOSSIERS = PlatformDirs('subliminal')
CHEMIN_PAR_DEFAUT = DOSSIERS.user_config_path / 'subliminal.toml'

#: Règle intégrée, appliquée après celle de la config : retirer le point de montage, que guessit
#: prendrait pour un titre (PLAN.md 4.3, point 1).
NOM_PAR_DEFAUT = ('s|^/run/media/[^/]+/[^/]+/||', 's|^/media/[^/]+/[^/]+/||')


class ErreurConfig(Exception):
    """Configuration de subliminal inutilisable (message prêt à afficher)."""


@dataclass
class Config:
    """Réglages de subliminal utiles à subdolphin.

    `configs_sources` et `configs_refiners` contiennent des secrets : ils sont exclus du `repr` et ne
    doivent jamais être affichés ni journalisés.
    """

    chemin: Path
    langues: frozenset[Language]
    sources: tuple[str, ...]
    refiners: tuple[str, ...]
    configs_sources: dict[str, dict[str, Any]] = field(repr=False)
    configs_refiners: dict[str, dict[str, Any]] = field(repr=False)
    resolveurs_nom: tuple[NameResolver, ...] = field(repr=False)
    dossier_cache: Path
    max_workers: int | None = None
    #: Réglages `[download]` transmis tels quels à subliminal (mêmes valeurs par défaut que sa CLI).
    encodage: str | None = 'utf-8'  # None : garder l'encodage d'origine (`encoding = ""`)
    format_sous_titres: str | None = None  # `subtitle_format`, None : garder le format d'origine
    format_langue: str = 'alpha2'  # `language_format`
    categories: str = ''  # `subtitle_categories`, ex. "n,hi" ou "fo" (forcés seulement)
    min_score: int = 0  # `min_score`, en % du score maximum (comme la CLI)
    skip_wrong_fps: bool = False  # `skip_wrong_fps`
    #: Mode automatique : télécharger même si la langue est déjà là (`force`), en ne comptant pas les
    #: fichiers externes (`force_external_subtitles`) ou les pistes intégrées (`force_embedded_subtitles`).
    force: bool = False
    force_externes: bool = False
    force_integres: bool = False

    def nom_pour_guessit(self, chemin: str | os.PathLike[str]) -> str:
        """Nom passé à guessit : motifs de la config, puis règle intégrée."""
        nom = os.fspath(chemin)
        for resolveur in self.resolveurs_nom:
            nom = resolveur(nom) or nom
        return nom


def _listes(section: dict[str, Any], cle: str) -> dict[str, list[str]]:
    return {
        'select': list(section.get(cle, [])),
        'extend': list(section.get(f'extend_{cle}', [])),
        'ignore': list(section.get(f'ignore_{cle}', [])),
    }


def lire(donnees: dict[str, Any], chemin: Path) -> Config:
    """Construit la `Config` à partir du TOML déjà lu, avec les règles de la CLI de subliminal."""
    telechargement = donnees.get('download', {})
    vides = {'select': [], 'extend': [], 'ignore': []}

    codes = telechargement.get('language', [])
    if isinstance(codes, str):
        codes = [codes]
    try:
        langues = frozenset(Language.fromietf(code) for code in codes)
    except (ValueError, babelfish.Error) as e:
        raise ErreurConfig(t('err.config_toml', chemin=chemin, erreur=e)) from e
    if not langues:
        raise ErreurConfig(t('err.config_langue', chemin=chemin))

    resolveurs = []
    nom = telechargement.get('name')
    try:
        if nom:
            resolveurs.append(NameResolver.from_name(nom))
        resolveurs.append(NameResolver.from_name(NOM_PAR_DEFAUT))
    except ValueError as e:
        raise ErreurConfig(t('err.config_nom', chemin=chemin, erreur=e)) from e

    sources = merge_extend_and_ignore_unions(vides, _listes(telechargement, 'provider'), get_default_providers())
    refiners = merge_extend_and_ignore_unions(vides, _listes(telechargement, 'refiner'), get_default_refiners())

    defaut = donnees.get('default', {})
    dossier_cache = Path(defaut.get('cache_dir', DOSSIERS.user_cache_dir)).expanduser()

    return Config(
        chemin=chemin,
        langues=langues,
        sources=tuple(sorted(sources)),
        refiners=tuple(r for r in get_default_refiners() if r in refiners),
        configs_sources={k: dict(v) for k, v in donnees.get('provider', {}).items()},
        configs_refiners={k: dict(v) for k, v in donnees.get('refiner', {}).items()},
        resolveurs_nom=tuple(resolveurs),
        dossier_cache=dossier_cache,
        max_workers=telechargement.get('max_workers'),
        encodage=telechargement.get('encoding', 'utf-8') or None,
        format_sous_titres=telechargement.get('subtitle_format') or None,
        format_langue=telechargement.get('language_format', 'alpha2'),
        categories=telechargement.get('subtitle_categories', ''),
        min_score=int(telechargement.get('min_score', 0)),
        skip_wrong_fps=bool(telechargement.get('skip_wrong_fps', False)),
        force=bool(telechargement.get('force', False)),
        force_externes=bool(telechargement.get('force_external_subtitles', False)),
        force_integres=bool(telechargement.get('force_embedded_subtitles', False)),
    )


def charger(chemin: str | os.PathLike[str] | None = None) -> Config:
    """Lit le fichier de configuration de subliminal (absent : réglages par défaut)."""
    chemin = Path(chemin).expanduser() if chemin else CHEMIN_PAR_DEFAUT
    donnees: dict[str, Any] = {}
    if chemin.is_file():
        try:
            with chemin.open('rb') as f:
                donnees = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            raise ErreurConfig(t('err.config_toml', chemin=chemin, erreur=e)) from e
    return lire(donnees, chemin)
