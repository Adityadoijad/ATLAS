"""Tests for the Wikimedia destination photo lookup used by AI discovery.

The contract that matters: a real photo when one exists, None when there is
none, and never an exception that could take down the suggestion it belongs to.
"""
import asyncio

import httpx
import pytest

from app.services.integrations import photos


@pytest.fixture(autouse=True)
def _clear_state():
    photos._cache.clear()
    photos.photos_breaker.failures = 0
    photos.photos_breaker.opened_at = None
    yield
    photos._cache.clear()


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://upload.wikimedia.org/a/Raipur_temple.jpg", True),
        ("https://upload.wikimedia.org/a/Ha_Long_Bay.jpeg", True),
        # Flags, crests and locator maps are the usual lead image on country
        # and region articles, and are not photographs of the place.
        ("https://upload.wikimedia.org/a/Flag_of_Zanzibar.svg.png", False),
        ("https://upload.wikimedia.org/a/Coat_of_arms_of_Nepal.jpg", False),
        ("https://upload.wikimedia.org/a/India_location_map.jpg", False),
        ("https://upload.wikimedia.org/a/Bhutan_map_of_districts.jpg", False),
        ("https://upload.wikimedia.org/a/Company_logo.jpg", False),
        # Non-raster/diagram formats never carry a usable photo here.
        ("https://upload.wikimedia.org/a/Something.svg", False),
        ("https://upload.wikimedia.org/a/Something.png", False),
        (None, False),
    ],
)
def test_is_photo_filters_non_photographs(url, expected) -> None:
    assert photos._is_photo(url) is expected


def _client_returning(handler):
    """Point the module's HTTP client at a mock transport."""
    real_client = httpx.AsyncClient

    def factory(*_args, **kwargs):
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    return factory


def test_lead_image_is_used_when_it_is_a_photo(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.php" in str(request.url)
        return httpx.Response(200, json={"query": {"pages": [
            {"title": "Raipur", "thumbnail": {"source": "https://up.wikimedia.org/Sri_Ram_Mandir.jpg?utm_source=x"}},
        ]}})

    monkeypatch.setattr(photos.httpx, "AsyncClient", _client_returning(handler))
    result = asyncio.run(photos.get_destination_photo("Raipur", "India"))
    # The analytics query string is stripped; the bare file URL is stable.
    assert result == "https://up.wikimedia.org/Sri_Ram_Mandir.jpg"


def test_falls_back_to_a_photo_inside_the_same_article(monkeypatch) -> None:
    """A flag lead image must fall back within the matched article, not to the
    next search result, which would return an unrelated subject."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "api.php" in str(request.url):
            return httpx.Response(200, json={"query": {"pages": [
                {"title": "Zanzibar", "thumbnail": {"source": "https://up.wikimedia.org/Flag_of_Zanzibar.svg.png"}},
            ]}})
        assert "media-list/Zanzibar" in str(request.url)
        return httpx.Response(200, json={"items": [
            {"type": "image", "srcset": [{"src": "//up.wikimedia.org/Coat_of_arms.jpg"}]},
            {"type": "video", "srcset": [{"src": "//up.wikimedia.org/clip.jpg"}]},
            {"type": "image", "srcset": [
                {"src": "//up.wikimedia.org/500px-Old_castle.jpg"},
                {"src": "//up.wikimedia.org/960px-Old_castle.jpg"},
            ]},
        ]})

    monkeypatch.setattr(photos.httpx, "AsyncClient", _client_returning(handler))
    # Protocol-relative URLs are normalised, and the largest srcset entry wins.
    assert asyncio.run(photos.get_destination_photo("Zanzibar", "Tanzania")) == \
        "https://up.wikimedia.org/960px-Old_castle.jpg"


def test_returns_none_when_no_photo_exists(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "api.php" in str(request.url):
            return httpx.Response(200, json={"query": {"pages": [
                {"title": "Nowhere", "thumbnail": {"source": "https://up.wikimedia.org/Flag.svg"}},
            ]}})
        return httpx.Response(404)

    monkeypatch.setattr(photos.httpx, "AsyncClient", _client_returning(handler))
    assert asyncio.run(photos.get_destination_photo("Nowhere", "Atlantis")) is None


def test_no_search_match_returns_none(monkeypatch) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"query": {"pages": []}})

    monkeypatch.setattr(photos.httpx, "AsyncClient", _client_returning(handler))
    assert asyncio.run(photos.get_destination_photo("Qzxqzx", "Nowhere")) is None


def test_provider_failure_degrades_to_none_instead_of_raising(monkeypatch) -> None:
    """Wikimedia 403s clients it does not like. A photo is decorative, so that
    must never propagate and fail the discovery response."""
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Please respect our robot policy")

    monkeypatch.setattr(photos.httpx, "AsyncClient", _client_returning(handler))
    assert asyncio.run(photos.get_destination_photo("Raipur", "India")) is None


def test_results_are_cached_so_repeat_lookups_do_not_refetch(monkeypatch) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"query": {"pages": [
            {"title": "Hampi", "thumbnail": {"source": "https://up.wikimedia.org/Hampi.jpg"}},
        ]}})

    monkeypatch.setattr(photos.httpx, "AsyncClient", _client_returning(handler))
    assert asyncio.run(photos.get_destination_photo("Hampi", "India")) == "https://up.wikimedia.org/Hampi.jpg"
    assert asyncio.run(photos.get_destination_photo("hampi", "India")) == "https://up.wikimedia.org/Hampi.jpg"
    assert calls["n"] == 1


def test_attach_photos_preserves_input_order(monkeypatch) -> None:
    """Photos resolve concurrently, so mapping them back onto destinations must
    not depend on which request finishes first."""
    async def fake(name: str, country: str | None = None) -> str | None:
        if name == "Slow":
            await asyncio.sleep(0.05)
        return None if name == "Missing" else f"https://photo/{name}"

    monkeypatch.setattr(photos, "get_destination_photo", fake)
    result = asyncio.run(photos.attach_photos([("Slow", "X"), ("Missing", "Y"), ("Fast", "Z")]))
    assert result == ["https://photo/Slow", None, "https://photo/Fast"]


def test_discovery_attaches_photos_to_each_suggestion(monkeypatch) -> None:
    """Through the discovery service: every suggestion carries its own photo,
    and a miss leaves image_url null rather than borrowing another one."""
    from app.schemas.recommendations import DiscoveredDestinationSchema
    from app.services import discover_service

    suggestions = [
        DiscoveredDestinationSchema(
            name=name, country="India", description="A place.", categories=["Nature"],
            estimated_budget_inr=40000, best_season="Oct - Mar", duration_days=4,
        )
        for name in ("Hampi", "Missing", "Ziro")
    ]

    async def fake_attach(pairs):
        assert pairs == [("Hampi", "India"), ("Missing", "India"), ("Ziro", "India")]
        return ["https://photo/Hampi", None, "https://photo/Ziro"]

    monkeypatch.setattr(discover_service, "attach_photos", fake_attach)
    result = asyncio.run(discover_service._with_photos(suggestions))

    assert [item.image_url for item in result] == ["https://photo/Hampi", None, "https://photo/Ziro"]
