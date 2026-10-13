import shutil
import subprocess
from pathlib import Path

import pytest
from babelfish import Language
from subliminal.subtitle import EmbeddedSubtitle
from subliminal.video import Episode, Movie

from subdolphin.analysis import analyze, kind, readable_title
from subdolphin.config import parse

# Only the file name is analysed: pytest's temporary folder must not guide guessit.
CONFIG = parse({'download': {'language': ['fr'], 'name': ['s|^.*/||']}}, Path('/tmp/subliminal.toml'))
FR = Language('fra')


@pytest.mark.parametrize(
    ('subtitle_format', 'expected'),
    [('vobsub', 'image'), ('pgs', 'image'), ('dvbsub', 'image'), ('srt', 'text'), ('ass', 'text'), ('odd', 'unknown')],
)
def test_kind(subtitle_format: str, expected: str) -> None:
    track = EmbeddedSubtitle.from_video_path(FR, video_path='/v/Film.mkv', subtitle_format=subtitle_format)
    assert kind(track) == expected


def test_readable_title() -> None:
    assert readable_title(Movie('x.mkv', 'The Fall', year=2006)) == 'The Fall (2006)'
    assert readable_title(Movie('x.mkv', 'The Fall')) == 'The Fall'
    assert readable_title(Episode('x.mkv', 'Doctor Who', 1, [2], year=2005)) == 'Doctor Who (2005) S01E02'
    assert readable_title(Episode('x.mkv', 'Lost', 2, [3, 4])) == 'Lost S02E03E04'


def test_analyze(tmp_path: Path) -> None:
    video = tmp_path / 'The Fall (2006) (1080p BluRay x265 10bit Tigole).mkv'
    video.touch()
    for name in ('The Fall (2006) (1080p BluRay x265 10bit Tigole).fr.srt', 'Other.fr.srt'):
        (tmp_path / name).touch()
    analysis = analyze(video, CONFIG)
    assert isinstance(analysis.video, Movie)
    assert (analysis.video.title, analysis.video.year) == ('The Fall', 2006)
    assert [(p.name, s.language) for p, s in analysis.external.items()] == [
        ('The Fall (2006) (1080p BluRay x265 10bit Tigole).fr.srt', FR)
    ]
    assert analysis.embedded == []


def test_analyze_unrecognised_then_typed_title(tmp_path: Path) -> None:
    video = tmp_path / '2006.mkv'
    video.touch()
    assert analyze(video, CONFIG).video is None
    analysis = analyze(video, CONFIG, title='The Fall (2006)')
    assert analysis.guessit_name == 'The Fall (2006).mkv'
    assert (analysis.video.title, analysis.video.year) == ('The Fall', 2006)
    assert analysis.video.name == str(video)


def test_analyze_typed_episode(tmp_path: Path) -> None:
    video = tmp_path / 'unknown.mkv'
    video.touch()
    analysis = analyze(video, CONFIG, title='Doctor Who (2005) S01E02')
    assert isinstance(analysis.video, Episode)
    assert readable_title(analysis.video) == 'Doctor Who (2005) S01E02'


@pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg missing (used to build the video)')
@pytest.mark.parametrize('name', ['The Fall (2006).mkv', '2006.mkv'], ids=['recognised', 'unrecognised'])
def test_analyze_embedded_tracks(tmp_path: Path, name: str) -> None:
    srt = tmp_path / 'a.srt'
    srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nBonjour\n')
    video = tmp_path / name
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=size=64x64:duration=1', '-i', srt,
         '-map', '0', '-map', '1', '-c:v', 'libx264', '-c:s', 'srt', '-metadata:s:s:0', 'language=fre',
         '-disposition:s:0', 'forced', video],
        check=True,
    )  # fmt: skip
    (track,) = analyze(video, CONFIG).embedded
    assert (track.language, kind(track), track.foreign_only) == (FR, 'text', True)


def test_analyze_not_a_video(tmp_path: Path) -> None:
    path = tmp_path / 'notes.txt'
    path.touch()
    with pytest.raises(ValueError):
        analyze(path, CONFIG)
