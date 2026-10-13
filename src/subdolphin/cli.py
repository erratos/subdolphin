"""Point d'entrée : subdolphin liste / choisir / auto / menu."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Any

from subliminal.video import Episode

from . import config as configuration
from . import menu, ui_kdialog, ui_terminal
from .analyse import Analyse, analyser, nature, titre_lisible
from .auto import automatique
from .parcours import choisir, decrire
from .recherche import NOMBRE_CANDIDATS, Candidat, affiner, au_dessus, lister
from .textes import pourcentage, t


def ligne_candidat(rang: int, c: Candidat) -> str:
    fps = f'{c.fps:g}' if c.fps else ''
    return (
        f'{rang:3d}  {pourcentage(c.pourcentage):>8}  {"★" if c.empreinte else " "}  {c.source:<16}  '
        f'{"HI" if c.malentendants else "  "}  {"TA" if c.traduction_auto else "  "}  {fps:<6}  {c.version}'
    )


def afficher_analyse(analyse: Analyse) -> None:
    print(t('liste.video', nom=analyse.chemin.name))
    print(t('liste.nom_analyse', nom=analyse.nom_guessit))
    if analyse.video is None:
        print(t('liste.non_reconnu'))
    else:
        cle = 'liste.episode' if isinstance(analyse.video, Episode) else 'liste.film'
        print(t(cle, titre=titre_lisible(analyse.video)))
    if analyse.pistes:
        print(t('liste.pistes'))
        for piste in analyse.pistes:
            print(f'  {decrire(piste)}, {t(f"nature.{nature(piste)}")} ({piste.subtitle_format})')
    else:
        print(t('liste.pistes_aucune'))
    if analyse.externes:
        print(t('liste.externes'))
        for chemin, externe in analyse.externes.items():
            print(f'  {chemin.name} ({decrire(externe)})')
    else:
        print(t('liste.externes_aucun'))


def afficher_candidats(candidats: list[Candidat], min_score: int, nombre: int) -> None:
    """Candidats au-dessus de `min_score` (réglage de la config, comme la CLI de subliminal)."""
    retenus = au_dessus(candidats, min_score)
    print()
    if not retenus:
        print(t('liste.aucun'))
    else:
        print(t('liste.entete'))
        for rang, candidat in enumerate(retenus[:nombre], 1):
            print(ligne_candidat(rang, candidat))
        print()
    affiches = min(nombre, len(retenus))
    if min_score:
        print(t('liste.total_seuil', n=len(candidats), retenus=len(retenus), seuil=min_score, affiches=affiches))
    else:
        print(t('liste.total', n=len(candidats), affiches=affiches))
    if retenus:
        print(t('liste.legende'))


def en_json(analyse: Analyse, candidats: list[Candidat], min_score: int, nombre: int) -> dict[str, Any]:
    """Résultat structuré (aucun secret : ni identifiant, ni clé, ni jeton)."""
    video = analyse.video
    return {
        'chemin': str(analyse.chemin),
        'nom_guessit': analyse.nom_guessit,
        'reconnu': None if video is None else {
            'type': 'episode' if isinstance(video, Episode) else 'film',
            'titre': titre_lisible(video),
        },
        'pistes': [
            {
                'langue': str(p.language) if p.language else None, 'format': p.subtitle_format,
                'nature': nature(p), 'forcee': bool(p.foreign_only), 'malentendants': bool(p.hearing_impaired),
            }
            for p in analyse.pistes
        ],
        'externes': [
            {
                'fichier': chemin.name, 'langue': str(e.language) if e.language else None,
                'malentendants': bool(e.hearing_impaired), 'force': bool(e.foreign_only),
            }
            for chemin, e in analyse.externes.items()
        ],
        'nombre_candidats': len(candidats),
        'min_score': min_score,
        'nombre_retenus': len(au_dessus(candidats, min_score)),
        'candidats': [
            {
                'source': c.source, 'id': c.sous_titre.id, 'score': c.score, 'score_max': c.score_max,
                'pourcentage': round(c.pourcentage, 1), 'empreinte': c.empreinte, 'version': c.version,
                'langue': str(c.sous_titre.language), 'malentendants': c.malentendants,
                'traduction_auto': c.traduction_auto, 'fps': c.fps,
            }
            for c in au_dessus(candidats, min_score)[:nombre]
        ],
    }  # fmt: skip


def commande_liste(args: argparse.Namespace, config: configuration.Config) -> int:
    try:
        analyse = analyser(args.fichier, config, titre=args.titre)
    except (ValueError, OSError) as e:
        print(t('err.video', erreur=e), file=sys.stderr)
        return 2
    candidats: list[Candidat] = []
    if analyse.video is not None:
        affiner(analyse.video, config)
        candidats = lister(analyse.video, config)
    if args.json:
        print(json.dumps(en_json(analyse, candidats, config.min_score, args.nombre), ensure_ascii=False, indent=2))
    else:
        afficher_analyse(analyse)
        if analyse.video is not None:
            afficher_candidats(candidats, config.min_score, args.nombre)
    return 0 if analyse.video is not None else 3


def analyseur() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='subdolphin', description=t('cli.description'))
    parser.add_argument('--config', type=Path, help=t('cli.config', chemin=configuration.CHEMIN_PAR_DEFAUT))
    parser.add_argument('--debug', action='store_true', help=t('cli.debug'))
    parser.add_argument('--version', action='version', version=f'%(prog)s {version("subdolphin")}')
    commandes = parser.add_subparsers(dest='commande', required=True)
    liste = commandes.add_parser(
        'liste',
        help=t('cli.liste'),
        description=t('cli.liste'),
        epilog=t('cli.liste_epilogue'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    liste.add_argument('fichier', type=Path, help=t('cli.fichier'))
    liste.add_argument('--titre', help=t('cli.titre'))
    liste.add_argument('-n', '--nombre', type=int, default=NOMBRE_CANDIDATS, help=t('cli.nombre', n=NOMBRE_CANDIDATS))
    liste.add_argument('--json', action='store_true', help=t('cli.json'))
    choix = commandes.add_parser(
        'choisir',
        help=t('cli.choisir'),
        description=t('cli.choisir'),
        epilog=t('cli.choisir_epilogue'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    choix.add_argument('fichier', type=Path, help=t('cli.fichier'))
    choix.add_argument('-n', '--nombre', type=int, default=None, help=t('cli.nombre_tous'))
    auto = commandes.add_parser(
        'auto',
        help=t('cli.auto'),
        description=t('cli.auto'),
        epilog=t('cli.auto_epilogue'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    auto.add_argument('chemins', type=Path, nargs='+', help=t('cli.chemins'))
    auto.add_argument('--texte', action='store_true', help=t('cli.texte'))
    menus = commandes.add_parser(
        'menu',
        help=t('cli.menu'),
        description=t('cli.menu'),
        epilog=t('cli.menu_epilogue'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    menus.add_argument('action', choices=['installer', 'retirer'], help=t('cli.menu_action'))
    return parser


def journal(debug: bool) -> None:
    """Journal de subliminal sur la sortie d'erreur avec `--debug` (réglé comme sa CLI), sinon rien."""
    journal_subliminal = logging.getLogger('subliminal')
    if debug:
        sortie = logging.StreamHandler()
        sortie.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        journal_subliminal.addHandler(sortie)
        journal_subliminal.setLevel(logging.DEBUG)
    else:
        journal_subliminal.addHandler(logging.NullHandler())


def commande_choisir(args: argparse.Namespace) -> int:
    """Lancée depuis Dolphin : toutes les erreurs s'affichent dans une fenêtre."""
    if not ui_kdialog.disponible():
        print(t('err.kdialog'), file=sys.stderr)
        return 2
    ui = ui_kdialog.Kdialog(t('ui.titre'))
    try:
        config = configuration.charger(args.config)
    except configuration.ErreurConfig as e:
        ui.erreur(str(e))
        return 2
    return choisir(args.fichier, config, ui, args.nombre)


def commande_auto(args: argparse.Namespace) -> int:
    """Lancée depuis Dolphin (fenêtres) ou dans un terminal (`--texte`)."""
    if args.texte:
        ui: ui_kdialog.Kdialog | ui_terminal.Terminal = ui_terminal.Terminal()
    elif ui_kdialog.disponible():
        ui = ui_kdialog.Kdialog(t('ui.titre'))
    else:
        print(t('err.kdialog'), file=sys.stderr)
        return 2
    try:
        config = configuration.charger(args.config)
    except configuration.ErreurConfig as e:
        ui.erreur(str(e))
        return 2
    bilan = automatique(args.chemins, config, ui)
    return 1 if bilan.erreurs else 0


def commande_menu(args: argparse.Namespace) -> int:
    if args.action == 'retirer':
        retires = menu.retirer()
        print(t('menu.retire') if retires else t('menu.absent'))
        for chemin in retires:
            print(f'  {chemin}')
        return 0
    commande = menu.commande_courante()
    try:
        chemins = menu.installer(commande)
    except (OSError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    print(t('menu.installe', commande=commande))
    for chemin in chemins:
        print(f'  {chemin}')
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = analyseur().parse_args(argv)
    journal(args.debug)
    if args.commande == 'menu':
        return commande_menu(args)
    if args.commande == 'choisir':
        return commande_choisir(args)
    if args.commande == 'auto':
        return commande_auto(args)
    try:
        config = configuration.charger(args.config)
    except configuration.ErreurConfig as e:
        print(e, file=sys.stderr)
        return 2
    return commande_liste(args, config)


if __name__ == '__main__':
    sys.exit(main())
