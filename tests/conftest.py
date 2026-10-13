import socket

import pytest


@pytest.fixture(autouse=True)
def french_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic texts: French interface, whatever the machine's language (French covers both the
    translated texts and the French number format)."""
    for variable in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv('LANG', 'fr_FR.UTF-8')


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests must never use the network (download quota, secrets, changing results)."""

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError('network access is forbidden during tests')

    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
