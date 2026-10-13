import configparser
from pathlib import Path

import pytest

from subdolphin import cli, menu
from subdolphin.menu import FILES, install, quote_exec, remove


def read(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str  # keep the keys' case (MimeType, Name[fr]…)
    parser.read(path, encoding='utf-8')
    return parser


def test_install(tmp_path: Path) -> None:
    paths = install('/home/user/.local/bin/subdolphin', tmp_path)
    assert sorted(p.name for p in paths) == sorted(FILES)
    assert all(p.stat().st_mode & 0o111 for p in paths)  # executable: KDE requires it

    choose = read(tmp_path / 'subdolphin-choose.desktop')
    assert choose['Desktop Entry']['MimeType'] == 'video/*;'
    assert choose['Desktop Entry']['X-KDE-RequiredNumberOfUrls'] == '1'
    assert choose['Desktop Action choose']['Exec'] == '"/home/user/.local/bin/subdolphin" choose %f'
    assert choose['Desktop Action choose']['Name'] == 'Choose a subtitle…'
    assert choose['Desktop Action choose']['Name[fr]'] == 'Choisir un sous-titre…'

    auto = read(tmp_path / 'subdolphin-auto.desktop')
    assert auto['Desktop Entry']['MimeType'] == 'video/*;inode/directory;'
    assert 'X-KDE-RequiredNumberOfUrls' not in auto['Desktop Entry']
    assert auto['Desktop Action auto']['Exec'] == '"/home/user/.local/bin/subdolphin" auto %F'

    # Same submenu for both files: KIO gathers their actions.
    assert {read(p)['Desktop Entry']['X-KDE-Submenu'] for p in paths} == {'Subtitles'}
    assert {read(p)['Desktop Entry']['X-KDE-Submenu[fr]'] for p in paths} == {'Sous-titres'}


def test_update(tmp_path: Path) -> None:
    install('/old/subdolphin', tmp_path)
    install('/new/subdolphin', tmp_path)
    assert '"/new/subdolphin"' in (tmp_path / 'subdolphin-auto.desktop').read_text()


def test_does_not_replace_a_foreign_file(tmp_path: Path) -> None:
    foreign = tmp_path / 'subdolphin-auto.desktop'
    foreign.write_text('[Desktop Entry]\nType=Service\n')
    with pytest.raises(FileExistsError):
        install('/x/subdolphin', tmp_path)
    assert foreign.read_text() == '[Desktop Entry]\nType=Service\n'


def test_remove(tmp_path: Path) -> None:
    install('/x/subdolphin', tmp_path)
    (tmp_path / 'other.desktop').write_text('[Desktop Entry]\n')
    assert sorted(p.name for p in remove(tmp_path)) == sorted(FILES)
    assert [p.name for p in tmp_path.iterdir()] == ['other.desktop']
    assert remove(tmp_path) == []


def test_remove_ignores_a_foreign_file(tmp_path: Path) -> None:
    foreign = tmp_path / 'subdolphin-choose.desktop'
    foreign.write_text('[Desktop Entry]\n')
    assert remove(tmp_path) == []
    assert foreign.exists()


def test_old_menu_from_0_1_0_removed(tmp_path: Path) -> None:
    old = tmp_path / 'subdolphin-choisir.desktop'
    old.write_text(f'[Desktop Entry]\n{menu.MARKER}\n')
    install('/x/subdolphin', tmp_path)
    assert not old.exists()
    old.write_text(f'[Desktop Entry]\n{menu.MARKER}\n')
    assert old in remove(tmp_path)


def test_quote_exec() -> None:
    assert quote_exec('/path with space/subdolphin') == '"/path with space/subdolphin"'
    with pytest.raises(ValueError):
        quote_exec('/path/$odd/subdolphin')


def test_menu_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    assert menu.menu_dir() == tmp_path / 'kio' / 'servicemenus'
    monkeypatch.delenv('XDG_DATA_HOME')
    assert menu.menu_dir() == Path.home() / '.local' / 'share' / 'kio' / 'servicemenus'


def test_menu_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    monkeypatch.setattr(menu, 'current_command', lambda: '/opt/subdolphin')
    assert cli.main(['menu', 'install']) == 0
    assert 'il lance : /opt/subdolphin' in capsys.readouterr().out
    assert len(list((tmp_path / 'kio' / 'servicemenus').iterdir())) == 2
    assert cli.main(['menu', 'remove']) == 0
    assert 'Menu « Sous-titres » retiré.' in capsys.readouterr().out
