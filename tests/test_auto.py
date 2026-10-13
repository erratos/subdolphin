from contextlib import contextmanager
from pathlib import Path

import pytest
from babelfish import Language
from helpers import SRT, FakeSubtitle
from subliminal.subtitle import EmbeddedSubtitle, ExternalSubtitle
from subliminal.video import Video

from subdolphin import auto
from subdolphin.analysis import Analysis
from subdolphin.auto import collect, languages_to_search, run
from subdolphin.config import parse

FR = Language('fra')


def config(**download):
    # Only the file name is analysed: pytest's temporary folder must not guide guessit.
    return parse({'download': {'language': ['fr'], 'name': ['s|^.*/||'], **download}}, Path('/tmp/subliminal.toml'))


def test_collect(tmp_path: Path) -> None:
    for name in ('a.mkv', 'b.avi', 'notes.txt', '.hidden.mkv', 'sample.mkv', 'S/c.mkv', '.cache/d.mkv', 'Sample/e.mkv'):
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).touch()
    (tmp_path / 'link.mkv').symlink_to(tmp_path / 'a.mkv')
    single = tmp_path / 'S' / 'c.mkv'
    found = collect([tmp_path, single, tmp_path / 'notes.txt', tmp_path / 'link.mkv'])
    assert [p.relative_to(tmp_path).as_posix() for p in found] == ['a.mkv', 'b.avi', 'S/c.mkv', 'link.mkv']


def analysis_with(external=(), embedded=()) -> Analysis:
    return Analysis(
        path=Path('/v/Film.mkv'),
        guessit_name='Film.mkv',
        video=Video('/v/Film.mkv'),
        external={Path(f'/v/Film.{lg}.srt'): ExternalSubtitle(Language.fromietf(lg), 'x') for lg in external},
        embedded=[EmbeddedSubtitle.from_video_path(Language.fromietf(lg), video_path='/v/Film.mkv') for lg in embedded],
    )


@pytest.mark.parametrize(
    ('external', 'embedded', 'settings', 'expected'),
    [
        ((), (), {}, {FR}),
        (('fr',), (), {}, set()),
        ((), ('fr',), {}, set()),
        (('en',), ('en',), {}, {FR}),
        (('fr',), ('fr',), {'force': True}, {FR}),
        (('fr',), (), {'force_external_subtitles': True}, {FR}),
        (('fr',), (), {'force_embedded_subtitles': True}, set()),
        ((), ('fr',), {'force_embedded_subtitles': True}, {FR}),
    ],
)
def test_languages_to_search_as_the_command_line(external, embedded, settings, expected) -> None:
    assert languages_to_search(analysis_with(external, embedded), config(**settings)) == expected


class FakePool:
    """Fake subliminal pool: "The Fall" has a subtitle, "Failure" crashes, the others have nothing."""

    options: list[dict] = []

    def __init__(self, **options) -> None:
        FakePool.options = []

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        pass

    def list_subtitles(self, video, languages):
        if video.title == 'Failure':
            raise RuntimeError('failure')
        return [FakeSubtitle({'title', 'year'}, text=SRT)] if video.title == 'The Fall' else []

    def download_best_subtitles(self, subtitles, video, languages, **options):
        FakePool.options.append(options)
        return subtitles


class FakeUI:
    def __init__(self, cancel_after: int | None = None) -> None:
        self.cancel_after = cancel_after
        self.advances: list[str] = []
        self.summary = ''

    @contextmanager
    def progress(self, text, total):
        yield self

    def advance(self, index, text):
        self.advances.append(text)

    def cancelled(self):
        return self.cancel_after is not None and len(self.advances) >= self.cancel_after

    def inform(self, text):
        self.summary = text


@pytest.fixture(autouse=True)
def no_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auto, 'AsyncProviderPool', FakePool)
    monkeypatch.setattr(auto, 'refine_video', lambda video, config: None)
    monkeypatch.setattr(auto, 'configure_cache', lambda config: None)


def videos(folder: Path, *names: str) -> list[Path]:
    for name in names:
        (folder / name).touch()
    return [folder / name for name in names]


def test_full_summary(tmp_path: Path) -> None:
    videos(tmp_path, 'The Fall (2006).mkv', 'Provided (2001).mkv', '2006.mkv', 'Nothing (1999).mkv', 'Failure (2000).mkv')
    (tmp_path / 'Provided (2001).fr.srt').write_text('already there')
    ui = FakeUI()
    summary = run([tmp_path], config(min_score=50), ui)
    assert [p.name for p in summary.saved] == ['The Fall (2006).fr.srt']
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text(encoding='utf-8') == SRT
    assert [p.name for p in summary.already_have] == ['Provided (2001).mkv']
    assert [p.name for p in summary.unrecognized] == ['2006.mkv']
    assert [p.name for p in summary.nothing_found] == ['Nothing (1999).mkv']
    assert summary.errors == [(tmp_path / 'Failure (2000).mkv', 'RuntimeError')]
    assert (summary.processed, summary.cancelled) == (5, False)
    # Configuration settings passed to download_best_subtitles, as the command line (323 × 50 // 100).
    assert FakePool.options[0] == {'min_score': 161, 'subtitle_categories': '', 'skip_wrong_fps': False}
    assert ui.advances[0] == 'Vidéo 1 / 5 : 2006.mkv'
    assert 'Enregistrés : 1\n    The Fall (2006).fr.srt' in ui.summary
    assert 'Rien trouvé à 50 % ou plus : 1\n    Nothing (1999).mkv' in ui.summary
    assert 'Erreurs : 1\n    Failure (2000).mkv : RuntimeError' in ui.summary
    assert 'subdolphin --debug auto --text' in ui.summary


def test_force_and_duplicate(tmp_path: Path) -> None:
    (path,) = videos(tmp_path, 'The Fall (2006).mkv')
    (tmp_path / 'The Fall (2006).fr.srt').write_text(SRT, encoding='utf-8')
    summary = run([path], config(force=True), FakeUI())
    assert (summary.saved, summary.duplicates) == ([], [path])
    assert sorted(p.name for p in tmp_path.iterdir()) == ['The Fall (2006).fr.srt', 'The Fall (2006).mkv']


def test_force_without_duplicate_replaces_nothing(tmp_path: Path) -> None:
    (path,) = videos(tmp_path, 'The Fall (2006).mkv')
    (tmp_path / 'The Fall (2006).fr.srt').write_text('something else')
    summary = run([path], config(force=True), FakeUI())
    assert [p.name for p in summary.saved] == ['The Fall (2006).fake.fr.srt']
    assert (tmp_path / 'The Fall (2006).fr.srt').read_text() == 'something else'


def test_cancel(tmp_path: Path) -> None:
    videos(tmp_path, 'A (2001).mkv', 'B (2002).mkv', 'C (2003).mkv')
    ui = FakeUI(cancel_after=1)
    summary = run([tmp_path], config(), ui)
    assert (summary.processed, summary.total, summary.cancelled) == (1, 3, True)
    assert 'Annulé après 1 vidéo(s) sur 3.' in ui.summary


def test_no_video(tmp_path: Path) -> None:
    ui = FakeUI()
    assert run([tmp_path], config(), ui).total == 0
    assert ui.summary.startswith('Aucune vidéo trouvée.')
