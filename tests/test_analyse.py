import shutil
import subprocess
from pathlib import Path

import pytest
from babelfish import Language
from subliminal.subtitle import EmbeddedSubtitle
from subliminal.video import Episode, Movie

from subdolphin.analyse import analyser, nature, titre_lisible
from subdolphin.config import lire

# Seul le nom de fichier est analysé : le dossier temporaire de pytest ne doit pas guider guessit.
CONFIG = lire({'download': {'language': ['fr'], 'name': ['s|^.*/||']}}, Path('/tmp/subliminal.toml'))
FR = Language('fra')


@pytest.mark.parametrize(
    ('format_', 'attendue'),
    [('vobsub', 'image'), ('pgs', 'image'), ('dvbsub', 'image'), ('srt', 'texte'), ('ass', 'texte'), ('bizarre', 'inconnue')],
)
def test_nature(format_: str, attendue: str) -> None:
    assert nature(EmbeddedSubtitle.from_video_path(FR, video_path='/v/Film.mkv', subtitle_format=format_)) == attendue


def test_titre_lisible() -> None:
    assert titre_lisible(Movie('x.mkv', 'The Fall', year=2006)) == 'The Fall (2006)'
    assert titre_lisible(Movie('x.mkv', 'The Fall')) == 'The Fall'
    assert titre_lisible(Episode('x.mkv', 'Doctor Who', 1, [2], year=2005)) == 'Doctor Who (2005) S01E02'
    assert titre_lisible(Episode('x.mkv', 'Lost', 2, [3, 4])) == 'Lost S02E03E04'


def test_analyser(tmp_path: Path) -> None:
    video = tmp_path / 'The Fall (2006) (1080p BluRay x265 10bit Tigole).mkv'
    video.touch()
    for nom in ('The Fall (2006) (1080p BluRay x265 10bit Tigole).fr.srt', 'Autre.fr.srt'):
        (tmp_path / nom).touch()
    analyse = analyser(video, CONFIG)
    assert isinstance(analyse.video, Movie)
    assert (analyse.video.title, analyse.video.year) == ('The Fall', 2006)
    assert [(c.name, s.language) for c, s in analyse.externes.items()] == [
        ('The Fall (2006) (1080p BluRay x265 10bit Tigole).fr.srt', FR)
    ]
    assert analyse.pistes == []


def test_analyser_titre_introuvable_puis_saisi(tmp_path: Path) -> None:
    video = tmp_path / '2006.mkv'
    video.touch()
    assert analyser(video, CONFIG).video is None
    analyse = analyser(video, CONFIG, titre='The Fall (2006)')
    assert analyse.nom_guessit == 'The Fall (2006).mkv'
    assert (analyse.video.title, analyse.video.year) == ('The Fall', 2006)
    assert analyse.video.name == str(video)


def test_analyser_episode_saisi(tmp_path: Path) -> None:
    video = tmp_path / 'inconnu.mkv'
    video.touch()
    analyse = analyser(video, CONFIG, titre='Doctor Who (2005) S01E02')
    assert isinstance(analyse.video, Episode)
    assert titre_lisible(analyse.video) == 'Doctor Who (2005) S01E02'


@pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg absent (sert à fabriquer la vidéo)')
@pytest.mark.parametrize('nom', ['The Fall (2006).mkv', '2006.mkv'], ids=['reconnu', 'non-reconnu'])
def test_analyser_pistes_integrees(tmp_path: Path, nom: str) -> None:
    srt = tmp_path / 'a.srt'
    srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nBonjour\n')
    video = tmp_path / nom
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=size=64x64:duration=1', '-i', srt,
         '-map', '0', '-map', '1', '-c:v', 'libx264', '-c:s', 'srt', '-metadata:s:s:0', 'language=fre',
         '-disposition:s:0', 'forced', video],
        check=True,
    )  # fmt: skip
    (piste,) = analyser(video, CONFIG).pistes
    assert (piste.language, nature(piste), piste.foreign_only) == (FR, 'texte', True)


def test_analyser_pas_une_video(tmp_path: Path) -> None:
    fichier = tmp_path / 'notes.txt'
    fichier.touch()
    with pytest.raises(ValueError):
        analyser(fichier, CONFIG)
