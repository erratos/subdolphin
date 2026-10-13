"""Dolphin service menus: the "Subtitles" submenu.

Two files, because `MimeType` and the number of selected files apply to a whole file: KIO gathers their
actions in the same submenu (same `X-KDE-Submenu`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ICON = 'media-view-subtitles-symbolic'
#: subdolphin's own key (ignored by KDE): only files carrying it are replaced or removed.
MARKER = 'X-Subdolphin=true'

HEADER = '''[Desktop Entry]
Type=Service
X-KDE-ServiceTypes=KonqPopupMenu/Plugin
X-KDE-Protocols=file
X-KDE-Submenu=Subtitles
X-KDE-Submenu[fr]=Sous-titres
{marker}
'''

FILES = {
    # "Choose a subtitle…": exactly one video.
    'subdolphin-choose.desktop': HEADER + '''MimeType=video/*;
X-KDE-RequiredNumberOfUrls=1
Actions=choose

[Desktop Action choose]
Name=Choose a subtitle…
Name[fr]=Choisir un sous-titre…
Icon={icon}
Exec={command} choose %f
''',
    # "Best subtitle automatically": videos and folders, any number.
    'subdolphin-auto.desktop': HEADER + '''MimeType=video/*;inode/directory;
Actions=auto

[Desktop Action auto]
Name=Best subtitle automatically
Name[fr]=Meilleur sous-titre automatique
Icon={icon}
Exec={command} auto %F
''',
}

#: Files of previous versions, removed on install and on removal (0.1.0: French names).
OLD_FILES = ('subdolphin-choisir.desktop',)


def menu_dir() -> Path:
    """The user's service menu folder (`$XDG_DATA_HOME/kio/servicemenus`)."""
    base = os.environ.get('XDG_DATA_HOME') or os.path.join(Path.home(), '.local', 'share')
    return Path(base) / 'kio' / 'servicemenus'


def current_command() -> str:
    """Absolute path of the running `subdolphin` command (the one from `uv tool install`, or the venv)."""
    return os.path.abspath(sys.argv[0])


def quote_exec(command: str) -> str:
    """Path for the `Exec` key (Desktop Entry specification), quoted for spaces."""
    if any(c in command for c in '"`$\\'):
        raise ValueError(f'unsupported character in the command path: {command}')
    return f'"{command}"'


def is_ours(path: Path) -> bool:
    try:
        return MARKER in path.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return False


def install(command: str, folder: Path | None = None) -> list[Path]:
    """Writes (or updates) both menus, executable as KDE requires. Never replaces a file that is not
    subdolphin's."""
    folder = folder or menu_dir()
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, template in FILES.items():
        path = folder / name
        if path.exists() and not is_ours(path):
            raise FileExistsError(f'{path} exists and is not subdolphin\'s: nothing was replaced')
        path.write_text(template.format(marker=MARKER, icon=ICON, command=quote_exec(command)), encoding='utf-8')
        path.chmod(0o755)
        paths.append(path)
    for name in OLD_FILES:
        if is_ours(folder / name):
            (folder / name).unlink()
    return paths


def remove(folder: Path | None = None) -> list[Path]:
    """Deletes subdolphin's menus (and only them); returns the deleted files."""
    folder = folder or menu_dir()
    removed = []
    for name in (*FILES, *OLD_FILES):
        path = folder / name
        if is_ours(path):
            path.unlink()
            removed.append(path)
    return removed
