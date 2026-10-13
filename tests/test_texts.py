import string

import pytest

from subdolphin import texts


def fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_same_keys_and_fields_in_each_language() -> None:
    assert texts.TEXTS['fr'].keys() == texts.TEXTS['en'].keys()
    for key, template in texts.TEXTS['fr'].items():
        assert fields(template) == fields(texts.TEXTS['en'][key]), key


@pytest.mark.parametrize(
    ('variables', 'expected'),
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
def test_ui_language(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], expected: str) -> None:
    monkeypatch.delenv('LANG', raising=False)
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    assert texts.ui_language() == expected


def test_percent(monkeypatch: pytest.MonkeyPatch) -> None:
    assert texts.percent(271 / 323 * 100) == '83,9 %'
    monkeypatch.setenv('LANG', 'en_US.UTF-8')
    assert texts.percent(271 / 323 * 100) == '83.9%'
