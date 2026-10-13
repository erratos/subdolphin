import socket

import pytest


@pytest.fixture(autouse=True)
def interface_en_francais(monkeypatch: pytest.MonkeyPatch) -> None:
    """Textes déterministes : interface en français, quelle que soit la langue de la machine."""
    for variable in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv('LANG', 'fr_FR.UTF-8')


@pytest.fixture(autouse=True)
def sans_reseau(monkeypatch: pytest.MonkeyPatch) -> None:
    """Les tests unitaires ne doivent jamais toucher au réseau (quota, secrets, résultats changeants)."""

    def interdit(*args: object, **kwargs: object) -> None:
        raise AssertionError('accès réseau interdit pendant les tests')

    monkeypatch.setattr(socket, 'getaddrinfo', interdit)
    monkeypatch.setattr(socket.socket, 'connect', interdit)
