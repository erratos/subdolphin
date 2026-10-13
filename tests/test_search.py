from pathlib import Path

from helpers import FakeSubtitle
from subliminal.video import Movie

from subdolphin import search
from subdolphin.config import parse
from subdolphin.search import Candidate, above_threshold, download, list_candidates, sort_candidates

FILM = Movie('/v/The Fall (2006).mkv', 'The Fall', year=2006)


def test_evaluate_candidate() -> None:
    candidate = Candidate.evaluate(FakeSubtitle({'title', 'year', 'country'}, hearing_impaired=True), FILM)
    assert (candidate.score, candidate.max_score, candidate.hash_match) == (270, 323, False)
    assert round(candidate.percent, 1) == 83.6
    assert (candidate.provider, candidate.hearing_impaired, candidate.release) == ('fake', True, 'Fake.Release.id')
    assert Candidate.evaluate(FakeSubtitle({'hash'}), FILM).hash_match


SUBTITLES = [
    FakeSubtitle({'title'}, subtitle_id='title'),
    FakeSubtitle({'title', 'year'}, subtitle_id='title-year-hi', hearing_impaired=True),
    FakeSubtitle({'title', 'year'}, subtitle_id='title-year'),
    FakeSubtitle({'hash'}, subtitle_id='hash'),
]


def ids(candidates: list[Candidate]) -> list[str]:
    return [c.subtitle.id for c in candidates]


def test_sort_by_score_keeping_provider_order() -> None:
    assert ids(sort_candidates(SUBTITLES, FILM)) == ['hash', 'title-year-hi', 'title-year', 'title']


def test_sort_by_configured_categories() -> None:
    # "n,hi": with equal scores, regular before hearing impaired (download_best_subtitles order).
    assert ids(sort_candidates(SUBTITLES, FILM, 'n,hi')) == ['hash', 'title-year', 'title-year-hi', 'title']
    # "hi" alone: the others are filtered out.
    assert ids(sort_candidates(SUBTITLES, FILM, 'hi')) == ['title-year-hi']


class FakePool:
    """Replaces subliminal's provider pool: no real provider."""

    options: dict = {}

    def __init__(self, **options) -> None:
        FakePool.options = options

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        pass

    def list_subtitles(self, video, languages):
        return list(SUBTITLES)


def test_list_candidates(monkeypatch) -> None:
    monkeypatch.setattr(search, 'AsyncProviderPool', FakePool)
    monkeypatch.setattr(search, 'configure_cache', lambda config: None)
    config = parse({'download': {'language': ['fr'], 'subtitle_categories': 'n,hi', 'provider': ['addic7ed']}}, Path('x'))
    assert ids(list_candidates(FILM, config))[:2] == ['hash', 'title-year']
    assert FakePool.options['providers'] == ['addic7ed']


def test_download(monkeypatch) -> None:
    calls = []

    def fake_download_subtitles(subtitles, **options):
        calls.append(options['providers'])
        subtitles[0].content = b'1\n00:00:01,000 --> 00:00:02,000\nBonjour\n'

    monkeypatch.setattr(search, 'download_subtitles', fake_download_subtitles)
    config = parse({'download': {'language': ['fr']}}, Path('x'))
    assert download(Candidate.evaluate(FakeSubtitle(), FILM), config)
    assert calls == [['fake']]


def test_download_failure(monkeypatch) -> None:
    monkeypatch.setattr(search, 'download_subtitles', lambda subtitles, **options: None)
    config = parse({'download': {'language': ['fr']}}, Path('x'))
    assert not download(Candidate.evaluate(FakeSubtitle(), FILM), config)


def test_above_threshold_as_the_command_line() -> None:
    candidates = sort_candidates(SUBTITLES, FILM)  # scores 323, 216, 216, 162 out of 323
    assert ids(above_threshold(candidates, 0)) == ['hash', 'title-year-hi', 'title-year', 'title']
    assert ids(above_threshold(candidates, 50)) == ['hash', 'title-year-hi', 'title-year', 'title']  # threshold 161
    assert ids(above_threshold(candidates, 51)) == ['hash', 'title-year-hi', 'title-year']
    assert ids(above_threshold(candidates, 100)) == ['hash']
