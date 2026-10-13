"""Menus de service Dolphin : sous-menu « Sous-titres » (PLAN.md 4.5).

Deux fichiers, car `MimeType` et le nombre de fichiers sélectionnés se règlent pour tout le fichier : KIO
réunit leurs actions dans le même sous-menu (même `X-KDE-Submenu`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ICONE = 'media-view-subtitles-symbolic'
#: Clé propre à subdolphin (ignorée par KDE) : seuls les fichiers qui la portent sont remplacés ou retirés.
MARQUE = 'X-Subdolphin=true'

ENTETE = '''[Desktop Entry]
Type=Service
X-KDE-ServiceTypes=KonqPopupMenu/Plugin
X-KDE-Protocols=file
X-KDE-Submenu=Subtitles
X-KDE-Submenu[fr]=Sous-titres
{marque}
'''

FICHIERS = {
    # « Choisir… » : exactement une vidéo.
    'subdolphin-choisir.desktop': ENTETE + '''MimeType=video/*;
X-KDE-RequiredNumberOfUrls=1
Actions=choisir

[Desktop Action choisir]
Name=Choose a subtitle…
Name[fr]=Choisir un sous-titre…
Icon={icone}
Exec={commande} choisir %f
''',
    # « Meilleur sous-titre automatique » : vidéos et dossiers, en nombre quelconque.
    'subdolphin-auto.desktop': ENTETE + '''MimeType=video/*;inode/directory;
Actions=auto

[Desktop Action auto]
Name=Best subtitle automatically
Name[fr]=Meilleur sous-titre automatique
Icon={icone}
Exec={commande} auto %F
''',
}


def dossier_menus() -> Path:
    """Dossier des menus de service de l'utilisateur (`$XDG_DATA_HOME/kio/servicemenus`)."""
    base = os.environ.get('XDG_DATA_HOME') or os.path.join(Path.home(), '.local', 'share')
    return Path(base) / 'kio' / 'servicemenus'


def commande_courante() -> str:
    """Chemin absolu de la commande `subdolphin` en cours (celle de `uv tool install`, ou de la venv)."""
    return os.path.abspath(sys.argv[0])


def entre_guillemets(commande: str) -> str:
    """Chemin pour la clé `Exec` (spécification Desktop Entry), entre guillemets pour les espaces."""
    if any(c in commande for c in '"`$\\'):
        raise ValueError(f'caractère non pris en charge dans le chemin de la commande : {commande}')
    return f'"{commande}"'


def est_a_nous(chemin: Path) -> bool:
    try:
        return MARQUE in chemin.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return False


def installer(commande: str, dossier: Path | None = None) -> list[Path]:
    """Écrit (ou met à jour) les deux menus, exécutables comme KDE l'exige. Ne remplace jamais un
    fichier qui n'est pas de subdolphin."""
    dossier = dossier or dossier_menus()
    dossier.mkdir(parents=True, exist_ok=True)
    chemins = []
    for nom, modele in FICHIERS.items():
        chemin = dossier / nom
        if chemin.exists() and not est_a_nous(chemin):
            raise FileExistsError(f'{chemin} existe et n\'est pas de subdolphin : rien n\'a été remplacé')
        chemin.write_text(
            modele.format(marque=MARQUE, icone=ICONE, commande=entre_guillemets(commande)), encoding='utf-8'
        )
        chemin.chmod(0o755)
        chemins.append(chemin)
    return chemins


def retirer(dossier: Path | None = None) -> list[Path]:
    """Supprime les menus de subdolphin (et seulement eux) ; renvoie ceux qui ont été supprimés."""
    dossier = dossier or dossier_menus()
    retires = []
    for nom in FICHIERS:
        chemin = dossier / nom
        if est_a_nous(chemin):
            chemin.unlink()
            retires.append(chemin)
    return retires
