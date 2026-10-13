import configparser
from pathlib import Path

import pytest

from subdolphin import cli, menu
from subdolphin.menu import FICHIERS, entre_guillemets, installer, retirer


def lire(chemin: Path) -> configparser.ConfigParser:
    lecteur = configparser.ConfigParser(interpolation=None, strict=True)
    lecteur.optionxform = str  # garder la casse des clés (MimeType, Name[fr]…)
    lecteur.read(chemin, encoding='utf-8')
    return lecteur


def test_installer(tmp_path: Path) -> None:
    chemins = installer('/home/user/.local/bin/subdolphin', tmp_path)
    assert sorted(c.name for c in chemins) == sorted(FICHIERS)
    assert all(c.stat().st_mode & 0o111 for c in chemins)  # exécutables : KDE l'exige

    choisir = lire(tmp_path / 'subdolphin-choisir.desktop')
    assert choisir['Desktop Entry']['MimeType'] == 'video/*;'
    assert choisir['Desktop Entry']['X-KDE-RequiredNumberOfUrls'] == '1'
    assert choisir['Desktop Action choisir']['Exec'] == '"/home/user/.local/bin/subdolphin" choisir %f'
    assert choisir['Desktop Action choisir']['Name[fr]'] == 'Choisir un sous-titre…'

    auto = lire(tmp_path / 'subdolphin-auto.desktop')
    assert auto['Desktop Entry']['MimeType'] == 'video/*;inode/directory;'
    assert 'X-KDE-RequiredNumberOfUrls' not in auto['Desktop Entry']
    assert auto['Desktop Action auto']['Exec'] == '"/home/user/.local/bin/subdolphin" auto %F'

    # Même sous-menu pour les deux fichiers : KIO réunit leurs actions.
    assert {lire(c)['Desktop Entry']['X-KDE-Submenu[fr]'] for c in chemins} == {'Sous-titres'}


def test_mise_a_jour(tmp_path: Path) -> None:
    installer('/ancien/subdolphin', tmp_path)
    installer('/nouveau/subdolphin', tmp_path)
    assert '"/nouveau/subdolphin"' in (tmp_path / 'subdolphin-auto.desktop').read_text()


def test_ne_remplace_pas_un_fichier_etranger(tmp_path: Path) -> None:
    etranger = tmp_path / 'subdolphin-auto.desktop'
    etranger.write_text('[Desktop Entry]\nType=Service\n')
    with pytest.raises(FileExistsError):
        installer('/x/subdolphin', tmp_path)
    assert etranger.read_text() == '[Desktop Entry]\nType=Service\n'


def test_retirer(tmp_path: Path) -> None:
    installer('/x/subdolphin', tmp_path)
    (tmp_path / 'autre.desktop').write_text('[Desktop Entry]\n')
    assert sorted(c.name for c in retirer(tmp_path)) == sorted(FICHIERS)
    assert [c.name for c in tmp_path.iterdir()] == ['autre.desktop']
    assert retirer(tmp_path) == []


def test_retirer_ignore_un_fichier_etranger(tmp_path: Path) -> None:
    etranger = tmp_path / 'subdolphin-choisir.desktop'
    etranger.write_text('[Desktop Entry]\n')
    assert retirer(tmp_path) == []
    assert etranger.exists()


def test_guillemets() -> None:
    assert entre_guillemets('/chemin avec espace/subdolphin') == '"/chemin avec espace/subdolphin"'
    with pytest.raises(ValueError):
        entre_guillemets('/chemin/$bizarre/subdolphin')


def test_dossier_menus(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    assert menu.dossier_menus() == tmp_path / 'kio' / 'servicemenus'
    monkeypatch.delenv('XDG_DATA_HOME')
    assert menu.dossier_menus() == Path.home() / '.local' / 'share' / 'kio' / 'servicemenus'


def test_commande_menu(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    monkeypatch.setattr(menu, 'commande_courante', lambda: '/opt/subdolphin')
    assert cli.main(['menu', 'installer']) == 0
    assert 'il lance : /opt/subdolphin' in capsys.readouterr().out
    assert len(list((tmp_path / 'kio' / 'servicemenus').iterdir())) == 2
    assert cli.main(['menu', 'retirer']) == 0
    assert 'Menu « Sous-titres » retiré.' in capsys.readouterr().out
