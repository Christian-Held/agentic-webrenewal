"""Tests for :mod:`webrenewal.http`."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from webrenewal.http import get


class DummyResponse:
    """Small response stub used to simulate :mod:`requests`."""

    def __init__(self, url: str, status_code: int, headers: dict, text: str) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.text = text
        self.elapsed = SimpleNamespace(total_seconds=lambda: 0.05)


@pytest.fixture(autouse=True)
def patch_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub ``requests.get`` so tests do not perform network I/O."""

    def fake_get(url: str, timeout: int, headers: dict | None = None) -> DummyResponse:  # noqa: D401 - fixture stub
        return DummyResponse(url, 200, {"Content-Type": "text/html"}, "<html></html>")

    monkeypatch.setattr("requests.get", fake_get)


def test_get_returns_http_response() -> None:
    """Given an URL When get is invoked Then an HttpResponse with details is returned."""

    response = get("https://example.com")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html"
    assert response.url == "https://example.com"

