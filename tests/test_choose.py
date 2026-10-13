import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from helpers import SRT, FakeSubtitle

from subdolphin import choose as choose_module
from subdolphin.choose import CORRECT, OPTIONS, ask_options, choose
from subdolphin.config import parse
from subdolphin.search import sort_candidates

# Only the file name is analysed: pytest's temporary folder must not guide guessit.
CONFIG = parse({'download': {'language': ['fr'], 'name': ['s|^.*/||']}}, Path('/tmp/subliminal.toml'))


class FakeUI:
    """Plays the user's answers in order and records every window."""

    def __init__(self, *answers: str | list[str] | None) -> None:
        self.answers = list(answers)
        self.windows: list[tuple[str, str]] = []
        self.lists: list[list[tuple[str, str]]] = []
        self.boxes: list[tuple[str, str, bool]] = []

    def choose(self, text, lines):
        self.windows.append(('choose', text))
        self.lists.append(lines)
        return self.answers.pop(0)

    def ask(self, text, default):
        self.windows.append(('ask', text))
        return self.answers.pop(0)

    def check(self, text, boxes):
        self.windows.append(('check', text))
        self.boxes = boxes
        return self.answers.pop(0)

    def inform(self, text):
        self.windows.append(('inform', text))

    def error(self, text):
        self.windows.append(('error', text))

    def notify(self, text):
        self.windows.append(('notify', text))

    @contextmanager
    def waiting(self, text):
        self.windows.append(('waiting', text))
        yield

    def kinds(self) -> list[str]:
        return [kind for kind, _ in self.windows]


@pytest.fixture
def providers(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Fake providers: two candidates for "The Fall", nothing for other titles."""
    state = {'downloads': [], 'failures': set(), 'searches': [], 'configs': []}

    def list_candidates(video, config):
        state['searches'].append(video.title)
        state['configs'].append(config)
        if video.title != 'The Fall':
            return []
        return sort_candidates(
            [
                FakeSubtitle({'title', 'year'}, subtitle_id='a', text=SRT),
                FakeSubtitle({'title'}, subtitle_id='b', text=SRT.replace('Bonjour', 'Salut'), hearing_impaired=True),
            ],
            video,
        )

    def download(candidate, config):
        state['downloads'].append(candidate.subtitle.id)
        return candidate.subtitle.id not in state['failures']

    monkeypatch.setattr(choose_module, 'refine_video', lambda video, config: None)
    monkeypatch.setattr(choose_module, 'list_candidates', list_candidates)
    monkeypatch.setattr(choose_module, 'download', download)
    return state


def video(tmp_path: Path, name: str = 'The Fall (2006).mkv') -> Path:
    path = tmp_path / name
    path.touch()
    return path


def test_choose_and_save(tmp_path: Path, providers: dict) -> None:
    ui = FakeUI('0')
    assert choose(video(tmp_path), CONFIG, ui) == 0
    assert ui.kinds() == ['waiting', 'choose', 'waiting', 'notify']
    assert ui.windows[-1] == ('notify', 'Enregistré : The Fall (2006).fr.srt')
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text(encoding='utf-8') == SRT
    assert providers['downloads'] == ['a']


def test_list_and_header(tmp_path: Path, providers: dict) -> None:
    path = video(tmp_path)
    (tmp_path / 'The Fall (2006).fr.srt').write_text('something else')
    ui = FakeUI(None)
    assert choose(path, CONFIG, ui) == 1
    header = ui.windows[1][1]
    assert header.startswith('« <b>The Fall (2006)</b> » : 2 sous-titre(s) trouvé(s), du meilleur au moins bon.<br>')
    assert 'Déjà présents : The Fall (2006).fr.srt (fr)' in header
    assert [tag for tag, _ in ui.lists[0]] == [CORRECT, OPTIONS, '0', '1']
    assert ui.lists[0][1][1] == '⚙ Options de cette recherche : langues fr · toutes catégories…'
    assert ui.lists[0][2][1] == '66,9 %  fake — Fake.Release.a'
    assert ui.lists[0][3][1] == '50,2 %  fake — Fake.Release.b · HI'


def test_configured_min_score(tmp_path: Path, providers: dict) -> None:
    config = parse({'download': {'language': ['fr'], 'name': ['s|^.*/||'], 'min_score': 60}}, Path('x'))
    ui = FakeUI(None)
    assert choose(video(tmp_path), config, ui) == 1
    assert ui.windows[1][1].startswith(
        '« <b>The Fall (2006)</b> » : 2 sous-titre(s) trouvé(s), dont 1 à 60 % ou plus, du meilleur au moins bon.'
    )
    assert [tag for tag, _ in ui.lists[0]] == [CORRECT, OPTIONS, '0']


def test_limited_count_and_escaped_header(tmp_path: Path, providers: dict) -> None:
    path = video(tmp_path, 'The Fall (2006) <&>.mkv')
    (tmp_path / 'The Fall (2006) <&>.fr.srt').write_text('something else')
    ui = FakeUI(None)
    assert choose(path, CONFIG, ui, count=1) == 1
    header = ui.windows[1][1]
    assert header.startswith('« <b>The Fall (2006)</b> » : 2 sous-titre(s) trouvé(s) ; voici les 1 meilleurs.<br>')
    assert 'The Fall (2006) &lt;&amp;&gt;.fr.srt' in header
    assert [tag for tag, _ in ui.lists[0]] == [CORRECT, OPTIONS, '0']


def test_next_to_an_existing_one_without_overwriting(tmp_path: Path, providers: dict) -> None:
    path = video(tmp_path)
    (tmp_path / 'The Fall (2006).fr.srt').write_text('something else')
    assert choose(path, CONFIG, FakeUI('1')) == 0
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text() == 'something else'
    assert (tmp_path / 'The Fall (2006).fake.fr.hi.srt').exists()


def test_unrecognised_title_then_typed(tmp_path: Path, providers: dict) -> None:
    ui = FakeUI('2006', 'The Fall (2006)', '0')
    assert choose(video(tmp_path, '2006.mkv'), CONFIG, ui) == 0
    assert ui.kinds() == ['ask', 'ask', 'waiting', 'choose', 'waiting', 'notify']
    assert 'Titre non reconnu pour « 2006.mkv »' in ui.windows[0][1]
    assert '« 2006 » n\'est pas reconnu' in ui.windows[1][1]
    assert (tmp_path / '2006.fr.srt').exists()


def test_input_cancelled(tmp_path: Path, providers: dict) -> None:
    assert choose(video(tmp_path, '2006.mkv'), CONFIG, FakeUI(None)) == 1


def test_no_result_then_corrected_title(tmp_path: Path, providers: dict) -> None:
    """Without results, the list is shown anyway, with its two action lines."""
    ui = FakeUI(CORRECT, 'The Fall (2006)', '0')
    assert choose(video(tmp_path, 'Other film (1999).mkv'), CONFIG, ui) == 0
    assert ui.windows[1][1].startswith('« <b>Other film (1999)</b> » : aucun sous-titre trouvé.<br>')
    assert [tag for tag, _ in ui.lists[0]] == [CORRECT, OPTIONS]
    assert providers['searches'] == ['Other film', 'The Fall']


def test_correct_title_from_the_list(tmp_path: Path, providers: dict) -> None:
    ui = FakeUI(CORRECT, None, CORRECT, 'Other film (1999)', None)
    assert choose(video(tmp_path), CONFIG, ui) == 1
    # Input cancelled: back to the list; then a new title: new search, without results.
    assert ui.kinds() == ['waiting', 'choose', 'ask', 'choose', 'ask', 'waiting', 'choose']
    assert providers['searches'] == ['The Fall', 'Other film']


def test_download_failure_then_another_choice(tmp_path: Path, providers: dict) -> None:
    providers['failures'].add('a')
    ui = FakeUI('0', '1')
    assert choose(video(tmp_path), CONFIG, ui) == 0
    error = next(text for kind, text in ui.windows if kind == 'error')
    assert 'Le téléchargement depuis fake a échoué' in error
    assert 'subdolphin --debug choose' in error
    assert providers['downloads'] == ['a', 'b']


def test_duplicate_then_cancel(tmp_path: Path, providers: dict) -> None:
    path = video(tmp_path)
    (tmp_path / 'The Fall (2006).fr.srt').write_text(SRT, encoding='utf-8')
    ui = FakeUI('0', None)
    assert choose(path, CONFIG, ui) == 1
    message = 'Ce sous-titre est identique à « The Fall (2006).fr.srt », déjà présent : il n\'a pas été recréé.'
    assert ('inform', message) in ui.windows
    assert sorted(p.name for p in tmp_path.iterdir()) == ['The Fall (2006).fr.srt', 'The Fall (2006).mkv']


def test_unusable_video(tmp_path: Path, providers: dict) -> None:
    ui = FakeUI()
    assert choose(tmp_path / 'missing.mkv', CONFIG, ui) == 2
    assert ui.kinds() == ['error']


@pytest.mark.skipif(os.geteuid() == 0, reason='root can write anywhere')
def test_read_only_folder(tmp_path: Path, providers: dict) -> None:
    path = video(tmp_path)
    tmp_path.chmod(0o555)
    try:
        ui = FakeUI()
        assert choose(path, CONFIG, ui) == 2
    finally:
        tmp_path.chmod(0o755)
    assert ui.kinds() == ['error']
    assert providers['searches'] == []


def test_options_for_this_search(tmp_path: Path, providers: dict) -> None:
    ui = FakeUI(OPTIONS, ['language:fr', 'language:en', 'category:hi'], None)
    assert choose(video(tmp_path), CONFIG, ui) == 1
    assert ui.kinds() == ['waiting', 'choose', 'check', 'waiting', 'choose']
    assert [(tag, checked) for tag, _, checked in ui.boxes] == [
        ('language:en', False), ('language:fr', True),
        ('category:n', True), ('category:hi', True), ('category:fo', True),
    ]  # fmt: skip
    new_config = providers['configs'][1]
    assert ({str(lg) for lg in new_config.languages}, new_config.subtitle_categories) == ({'fr', 'en'}, 'hi')
    assert ui.lists[1][1][1] == '⚙ Options de cette recherche : langues en, fr · HI…'
    assert CONFIG.subtitle_categories == ''  # the starting configuration is not modified


def test_incomplete_options(tmp_path: Path, providers: dict) -> None:
    ui = FakeUI(OPTIONS, ['category:n'], None)
    assert choose(video(tmp_path), CONFIG, ui) == 1
    assert ui.kinds() == ['waiting', 'choose', 'check', 'inform', 'choose']
    assert len(providers['configs']) == 1


@pytest.mark.parametrize(
    ('start', 'checked', 'expected'),
    [
        ('', ['n', 'hi', 'fo'], ''),
        ('', ['fo'], 'fo'),
        ('n,hi', ['n', 'hi', 'fo'], 'n,hi,fo'),
        ('hi,n', ['n', 'hi'], 'hi,n'),
    ],
)
def test_category_order(start: str, checked: list[str], expected: str) -> None:
    config = parse({'download': {'language': ['fr'], 'subtitle_categories': start}}, Path('x'))
    ui = FakeUI(['language:fr', *(f'category:{c}' for c in checked)])
    assert ask_options(config, ui).subtitle_categories == expected
