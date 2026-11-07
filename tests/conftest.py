"""A fake HTTP session so tests never touch the network."""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    @property
    def text(self):
        return self._payload if isinstance(self._payload, str) else json.dumps(self._payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Routes URLs to fixture payloads. Unknown URLs return 404."""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.headers = {}
        self.calls = []

    def _lookup(self, method, url, **kw):
        self.calls.append((method, url, kw))
        for prefix, payload in self.routes.items():
            if url.startswith(prefix):
                return payload(kw) if callable(payload) else FakeResponse(payload)
        return FakeResponse({}, status=404)

    def get(self, url, **kw):
        return self._lookup("GET", url, **kw)

    def post(self, url, **kw):
        return self._lookup("POST", url, **kw)


def load(name):
    return json.loads((FIXTURES / name).read_text())


def load_text(name):
    return (FIXTURES / name).read_text()


@pytest.fixture
def fake_session():
    return FakeSession
