import os
from pathlib import Path

import pytest
from babelfish import Language
from helpers import SRT, FakeSubtitle
from subliminal.core import search_external_subtitles
from subliminal.video import Video

from subdolphin import saving
from subdolphin.analysis import Analysis
from subdolphin.config import parse
from subdolphin.saving import find_duplicate, is_writable_dir, name_endings, normalize, reserve, save

FR = Language('fra')
CONFIG = parse({'download': {'language': ['fr']}}, Path('/tmp/subliminal.toml'))


def first_endings(n: int, **options) -> list[str]:
    options = {'hearing_impaired': False, 'extension': '.srt', 'already_present': False} | options
    endings = name_endings(FR, 'opensubtitlescom', **options)
    return [next(endings) for _ in range(n)]


def test_endings_without_existing_subtitle() -> None:
    assert first_endings(3) == ['.fr.srt', '.opensubtitlescom.fr.srt', '.opensubtitlescom-2.fr.srt']


def test_endings_hearing_impaired() -> None:
    assert first_endings(2, hearing_impaired=True) == ['.fr.hi.srt', '.opensubtitlescom.fr.hi.srt']


def test_endings_with_existing_subtitle() -> None:
    assert first_endings(3, already_present=True) == [
        '.opensubtitlescom.fr.srt',
        '.opensubtitlescom-2.fr.srt',
        '.opensubtitlescom-3.fr.srt',
    ]
    endings = first_endings(1, already_present=True, hearing_impaired=True, extension='.ass')
    assert endings == ['.opensubtitlescom.fr.hi.ass']


def test_endings_language_format() -> None:
    assert first_endings(1, language_format='alpha3') == ['.fra.srt']


def test_reserve(tmp_path: Path) -> None:
    path = tmp_path / 'Film.fr.srt'
    assert reserve(path)
    path.write_text('content')
    assert not reserve(path)
    assert path.read_text() == 'content'


def test_normalize() -> None:
    spaces = SRT.replace('\n', '\r\n').replace('Au revoir', 'Au revoir   ') + '\n\n\n'
    assert normalize(spaces) == normalize(SRT)
    assert normalize(SRT) != normalize(SRT.replace('Au revoir', 'À bientôt'))


def analysis_of(tmp_path: Path) -> Analysis:
    video = tmp_path / 'Film.mkv'
    video.touch()
    external = {tmp_path / f: st for f, st in search_external_subtitles(video).items()}
    return Analysis(path=video, guessit_name=video.name, video=Video(str(video)), external=external, embedded=[])


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-8-sig', 'cp1252', 'utf-16'])
def test_duplicate_whatever_the_encoding(tmp_path: Path, encoding: str) -> None:
    (tmp_path / 'Film.fr.srt').write_bytes(SRT.replace('Bonjour', 'Salut').encode('utf-8'))
    assert find_duplicate(SRT, analysis_of(tmp_path).external) is None
    (tmp_path / 'Film.2.fr.srt').write_bytes(SRT.replace('\n', '\r\n').encode(encoding))
    assert find_duplicate(SRT, analysis_of(tmp_path).external) == tmp_path / 'Film.2.fr.srt'


def test_duplicate_with_bom_imposed_by_the_provider(tmp_path: Path) -> None:
    """Real case: the provider imposes `utf-8`, so the BOM stays in the downloaded text, while the same file
    on disk is decoded as `utf-8-sig`, without BOM."""
    with_bom = ('﻿' + SRT).encode('utf-8')
    (tmp_path / 'Film.fr.srt').write_bytes(with_bom)
    downloaded = FakeSubtitle()  # imposed encoding: utf-8
    downloaded.content = with_bom
    assert downloaded.text.startswith('﻿')
    assert find_duplicate(downloaded.text, analysis_of(tmp_path).external) == tmp_path / 'Film.fr.srt'


def test_save_first_subtitle(tmp_path: Path) -> None:
    result = save(FakeSubtitle(text=SRT), analysis_of(tmp_path), CONFIG)
    assert result.path == tmp_path / 'Film.fr.srt'
    assert result.path.read_text(encoding='utf-8') == SRT


def test_save_next_to_an_existing_one(tmp_path: Path) -> None:
    (tmp_path / 'Film.fr.srt').write_text('something else')
    result = save(FakeSubtitle(text=SRT, hearing_impaired=True), analysis_of(tmp_path), CONFIG)
    assert result.path == tmp_path / 'Film.fake.fr.hi.srt'
    assert (tmp_path / 'Film.fr.srt').read_text() == 'something else'


def test_save_names_taken(tmp_path: Path) -> None:
    analysis = analysis_of(tmp_path)
    (tmp_path / 'Film.fake.fr.srt').write_text('taken')
    (tmp_path / 'Film.fake-2.fr.srt').write_text('taken')
    # Film.fr.srt appears after the analysis (another run): it is not overwritten.
    (tmp_path / 'Film.fr.srt').write_text('another run')
    result = save(FakeSubtitle(text=SRT), analysis, CONFIG)
    assert result.path == tmp_path / 'Film.fake-3.fr.srt'
    assert [(tmp_path / n).read_text() for n in ('Film.fr.srt', 'Film.fake.fr.srt')] == ['another run', 'taken']


def test_save_with_configured_encoding(tmp_path: Path) -> None:
    config = parse({'download': {'language': ['fr'], 'encoding': 'cp1252'}}, Path('/tmp/subliminal.toml'))
    result = save(FakeSubtitle(text=SRT), analysis_of(tmp_path), config)
    assert result.path.read_bytes() == SRT.encode('cp1252')


def test_save_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failure(*args: object, **kwargs: object) -> None:
        raise OSError('disk full')

    monkeypatch.setattr(saving, 'save_subtitles', failure)
    analysis = analysis_of(tmp_path)
    with pytest.raises(OSError, match='disk full'):
        save(FakeSubtitle(text=SRT), analysis, CONFIG)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Film.mkv']


def test_save_empty_subtitle(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='empty'):
        save(FakeSubtitle(), analysis_of(tmp_path), CONFIG)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Film.mkv']


def test_save_duplicate_even_badly_named(tmp_path: Path) -> None:
    """The duplicate is found even when subliminal does not recognise the existing file's language."""
    (tmp_path / 'Film.addic7ed.fr.srt').write_text(SRT.replace('\n', '\r\n'), encoding='utf-8')
    result = save(FakeSubtitle(text=SRT), analysis_of(tmp_path), CONFIG)
    assert (result.path, result.duplicate_of) == (None, tmp_path / 'Film.addic7ed.fr.srt')
    assert sorted(p.name for p in tmp_path.iterdir()) == ['Film.addic7ed.fr.srt', 'Film.mkv']


def test_save_ignores_other_languages(tmp_path: Path) -> None:
    (tmp_path / 'Film.en.srt').write_text('something else')
    result = save(FakeSubtitle(text=SRT), analysis_of(tmp_path), CONFIG)
    assert result.path == tmp_path / 'Film.fr.srt'


@pytest.mark.skipif(os.geteuid() == 0, reason='root can write anywhere')
def test_is_writable_dir(tmp_path: Path) -> None:
    video = tmp_path / 'read-only' / 'Film.mkv'
    video.parent.mkdir()
    assert is_writable_dir(video)
    video.parent.chmod(0o555)
    try:
        assert not is_writable_dir(video)
    finally:
        video.parent.chmod(0o755)
