import subprocess

import pytest

from subdolphin import ui_kdialog
from subdolphin.ui_kdialog import Kdialog


class FakeProcesses:
    """Replaces subprocess.run / Popen: records the commands, returns prepared answers."""

    def __init__(self, *answers: tuple[int, str]) -> None:
        self.answers = list(answers)
        self.commands: list[list[str]] = []

    def run(self, command, **options):
        self.commands.append(list(command))
        code, output = self.answers.pop(0) if self.answers else (0, '')
        return subprocess.CompletedProcess(command, code, output, '')

    def popen(self, command, **options):
        self.commands.append(list(command))


@pytest.fixture
def processes(monkeypatch: pytest.MonkeyPatch):
    def install(*answers: tuple[int, str]) -> FakeProcesses:
        fake = FakeProcesses(*answers)
        monkeypatch.setattr(ui_kdialog.subprocess, 'run', fake.run)
        monkeypatch.setattr(ui_kdialog.subprocess, 'Popen', fake.popen)
        monkeypatch.setattr(ui_kdialog.shutil, 'which', lambda name: f'/usr/bin/{name}')
        return fake

    return install


def test_choose(processes) -> None:
    fake = processes((0, '1\n'))
    assert Kdialog('Subtitles').choose('Text', [('0', 'first'), ('1', 'second')]) == '1'
    assert fake.commands == [
        ['kdialog', '--title', 'Subtitles', '--geometry', ui_kdialog.LIST_SIZE, '--menu', 'Text',
         '0', 'first', '1', 'second'],
    ]  # fmt: skip


def test_choose_cancelled(processes) -> None:
    processes((1, ''))
    assert Kdialog('T').choose('Text', [('0', 'first')]) is None


def test_check(processes) -> None:
    fake = processes((0, 'fr\nhi\n'), (1, ''))
    ui = Kdialog('T')
    assert ui.check('Options', [('fr', 'French', True), ('en', 'English', False), ('hi', 'HI', True)]) == ['fr', 'hi']
    assert fake.commands[0][3:] == [
        '--separate-output', '--checklist', 'Options', 'fr', 'French', 'on', 'en', 'English', 'off', 'hi', 'HI', 'on',
    ]
    assert ui.check('Options', [('fr', 'French', True)]) is None


def test_ask(processes) -> None:
    fake = processes((0, 'The Fall (2006)\n'), (1, ''))
    ui = Kdialog('T')
    assert ui.ask('Title?', 'The Fall') == 'The Fall (2006)'
    assert fake.commands[0][-3:] == ['--inputbox', 'Title?', 'The Fall']
    assert ui.ask('Title?', 'The Fall') is None


def test_messages_and_notification(processes) -> None:
    fake = processes()
    ui = Kdialog('T')
    ui.inform('info')
    ui.error('error')
    ui.notify('Saved: Film.fr.srt')
    assert [c[3:] for c in fake.commands] == [
        ['--msgbox', 'info'],
        ['--error', 'error'],
        ['--passivepopup', 'Saved: Film.fr.srt', '5'],
    ]


def test_waiting_closes_the_window_even_on_error(processes) -> None:
    fake = processes((0, 'org.kde.kdialog-42 /ProgressDialog\n'))
    with pytest.raises(RuntimeError), Kdialog('T').waiting('Searching…'):
        raise RuntimeError('failure')
    assert fake.commands == [
        ['kdialog', '--title', 'T', '--progressbar', 'Searching…', '0'],
        ['/usr/bin/qdbus6', 'org.kde.kdialog-42', '/ProgressDialog', 'close'],
    ]


def test_waiting_without_window(processes) -> None:
    fake = processes((1, ''))
    with Kdialog('T').waiting('Searching…'):
        pass
    assert len(fake.commands) == 1  # no window opened: nothing to close


def test_cancellable_progress(processes) -> None:
    fake = processes((0, 'org.kde.kdialog-7 /ProgressDialog\n'), (0, ''), (0, ''), (0, ''), (0, 'true\n'), (0, ''))
    with Kdialog('T').progress('Automatic subtitles', 3) as bar:
        bar.advance(1, 'Video 2 / 3: Film.mkv')
        assert bar.cancelled()
    qdbus = ['/usr/bin/qdbus6', 'org.kde.kdialog-7', '/ProgressDialog']
    assert fake.commands == [
        ['kdialog', '--title', 'T', '--progressbar', 'Automatic subtitles', '3'],
        [*qdbus, 'showCancelButton', 'true'],
        [*qdbus, 'Set', '', 'value', '1'],
        [*qdbus, 'setLabelText', 'Video 2 / 3: Film.mkv'],
        [*qdbus, 'wasCancelled'],
        [*qdbus, 'close'],
    ]
