import string

import pytest

from subdolphin import textes


def champs(modele: str) -> set[str]:
    return {nom for _, nom, _, _ in string.Formatter().parse(modele) if nom}


def test_memes_cles_et_memes_champs_dans_chaque_langue() -> None:
    assert textes.TEXTES['fr'].keys() == textes.TEXTES['en'].keys()
    for cle, modele in textes.TEXTES['fr'].items():
        assert champs(modele) == champs(textes.TEXTES['en'][cle]), cle


@pytest.mark.parametrize(
    ('variables', 'attendue'),
    [
        ({'LANG': 'fr_FR.UTF-8'}, 'fr'),
        ({'LANG': 'fr_CA.UTF-8'}, 'fr'),
        ({'LANG': 'en_US.UTF-8'}, 'en'),
        ({'LANG': 'de_DE.UTF-8'}, 'en'),
        ({'LANG': 'C'}, 'en'),
        ({'LANG': 'fr_FR.UTF-8', 'LANGUAGE': 'en_US:fr'}, 'en'),
        ({'LANG': 'en_US.UTF-8', 'LC_MESSAGES': 'fr_FR.UTF-8'}, 'fr'),
        ({}, 'en'),
    ],
)
def test_langue_interface(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], attendue: str) -> None:
    monkeypatch.delenv('LANG', raising=False)
    for nom, valeur in variables.items():
        monkeypatch.setenv(nom, valeur)
    assert textes.langue_interface() == attendue


def test_pourcentage(monkeypatch: pytest.MonkeyPatch) -> None:
    assert textes.pourcentage(271 / 323 * 100) == '83,9 %'
    monkeypatch.setenv('LANG', 'en_US.UTF-8')
    assert textes.pourcentage(271 / 323 * 100) == '83.9%'
