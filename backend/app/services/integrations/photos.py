"""Real destination photography from Wikimedia, used for AI-discovered places
that have no image in the local catalog.

Keyless and free-tier like the rest of the integrations here. The guiding rule
is the same one the planner follows: never show something fabricated. If no
genuine photo of the place can be found, this returns None and the UI renders a
plain placeholder — it never substitutes a stored stock image of a *different*
destination, which would misrepresent the suggestion.
"""
import asyncio
import logging
import re
from time import monotonic

import httpx

from app.services.integrations.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

photos_breaker = CircuitBreaker()

# Wikimedia's robot policy rejects generic clients with HTTP 403, so identify
# the project properly rather than relying on the HTTP library's default.
_USER_AGENT = "ATLAS-Travel-Planner/1.0 (https://github.com/Adityadoijad/ATLAS; student project) python-httpx"

# Lead images on country/region articles are very often a flag, crest or
# locator map rather than a photograph of the place. Those are recognisable
# from the file name, and are skipped in favour of a real photo further down
# the same article.
_NON_PHOTO_RE = re.compile(
    r"flag|coat[_ -]of[_ -]arms|seal|emblem|logo|locator|location[_ ]map|map[_ ]of|_map_|blank|icon|signature",
    re.I,
)

_CACHE_TTL_SECONDS = 24 * 60 * 60
_cache: dict[str, tuple[float, str | None]] = {}


def _is_photo(url: str | None) -> bool:
    """Accept only raster photographs. SVG is always a diagram/flag here, and
    PNG is nearly always a map or logo on these articles."""
    if not url:
        return False
    path = url.split("?")[0].lower()
    return path.endswith((".jpg", ".jpeg")) and not _NON_PHOTO_RE.search(path)


def _clean(url: str) -> str:
    # Drop Wikimedia's analytics query string; the bare file URL is stable.
    return url.split("?")[0]


async def _top_article(client: httpx.AsyncClient, query: str) -> tuple[str | None, str | None]:
    """Return (article title, lead image URL) for the best search match."""
    response = await client.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 800,
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": 1,
        },
    )
    response.raise_for_status()
    pages = (response.json().get("query") or {}).get("pages") or []
    if not pages:
        return None, None
    page = pages[0]
    return page.get("title"), (page.get("thumbnail") or {}).get("source")


async def _first_photo_in_article(client: httpx.AsyncClient, title: str) -> str | None:
    """Fall back to the first real photograph *within the matched article*.

    Deliberately scoped to the one article the search resolved to: walking
    down to the next search result instead would happily return a portrait of
    a head of state for "Bhutan", which is worse than showing no image.
    """
    response = await client.get(
        f"https://en.wikipedia.org/api/rest_v1/page/media-list/{title.replace(' ', '_')}"
    )
    if response.status_code != 200:
        return None
    for item in response.json().get("items", []):
        if item.get("type") != "image":
            continue
        srcset = item.get("srcset") or []
        if not srcset:
            continue
        source = srcset[-1].get("src") or srcset[0].get("src")  # last entry is the highest resolution
        if source and source.startswith("//"):
            source = f"https:{source}"
        if _is_photo(source):
            return _clean(source)
    return None


async def get_destination_photo(name: str, country: str | None = None) -> str | None:
    """Best-effort real photo URL for a destination, or None if none is found.

    Never raises: a missing photo must not fail the suggestion it belongs to.
    """
    query = f"{name} {country}".strip() if country else name.strip()
    if not query:
        return None

    cached = _cache.get(query.lower())
    if cached and monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    async def request() -> str | None:
        async with httpx.AsyncClient(
            timeout=8.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
        ) as client:
            title, lead_image = await _top_article(client, query)
            if _is_photo(lead_image):
                return _clean(str(lead_image))
            if title:
                return await _first_photo_in_article(client, title)
            return None

    try:
        url = await photos_breaker.call(request)
    except Exception as exc:
        # Photos are decorative; degrade quietly rather than breaking discovery.
        logger.warning("Destination photo lookup failed for %r: %s", query, type(exc).__name__)
        return None

    _cache[query.lower()] = (monotonic(), url)
    return url


async def attach_photos(destinations: list[tuple[str, str]]) -> list[str | None]:
    """Resolve photos for several destinations concurrently."""
    return list(
        await asyncio.gather(*(get_destination_photo(name, country) for name, country in destinations))
    )


async def _get_image_attribution(client: httpx.AsyncClient, image_url: str) -> dict[str, str | None]:
    """Fetch Wikimedia Commons attribution metadata for a known image URL.

    Uses the MediaWiki imageinfo API with extmetadata to pull the artist
    and license fields. Returns all fields as None on any failure — attribution
    is best-effort and must never abort the recommendation response.
    """
    empty: dict[str, str | None] = {"author": None, "license": None, "source_url": None}
    try:
        # Derive the filename from the URL.  Wikimedia URLs look like:
        # https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Foo.jpg/800px-Foo.jpg
        # The canonical file title is the last segment before the resolution suffix.
        parts = image_url.rstrip("/").split("/")
        # Walk backwards to find the first segment that looks like a real
        # filename (contains a dot that isn't just "." or "..").
        filename: str | None = None
        for part in reversed(parts):
            if "." in part and not part.startswith("px-"):
                # Strip resolution prefix that appears in thumb URLs, e.g. "800px-Foo.jpg"
                filename = re.sub(r"^\d+px-", "", part)
                break
        if not filename:
            return empty

        response = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "iiextmetadatafilter": "Artist|LicenseShortName|DescriptionUrl",
                "titles": f"File:{filename}",
            },
        )
        if response.status_code != 200:
            return empty
        pages = (response.json().get("query") or {}).get("pages") or []
        if not pages:
            return empty
        imageinfo_list = pages[0].get("imageinfo") or []
        if not imageinfo_list:
            return empty
        imageinfo = imageinfo_list[0]
        meta = imageinfo.get("extmetadata") or {}

        def _extract(key: str) -> str | None:
            entry = meta.get(key) or {}
            raw = entry.get("value")
            if not raw:
                return None
            # Strip HTML tags that Wikimedia sometimes embeds (e.g. <a href=…>)
            clean = re.sub(r"<[^>]+>", "", str(raw)).strip()
            return clean or None

        return {
            "author": _extract("Artist"),
            "license": _extract("LicenseShortName"),
            "source_url": imageinfo.get("descriptionurl") or _extract("DescriptionUrl"),
        }
    except Exception:
        return empty


async def get_destination_photo_with_metadata(
    name: str, state: str
) -> dict[str, str | None]:
    """Return image URL plus Wikimedia attribution for a named Indian destination.

    Uses the destination's name + state as the search query so results are
    geographically specific (e.g. "Majuli Assam" rather than just "Majuli").

    Never raises. Returns a dict with all fields set to None when no suitable
    image is found or any service call fails.
    """
    empty_result: dict[str, str | None] = {
        "url": None,
        "source": None,
        "source_url": None,
        "author": None,
        "license": None,
    }
    query = f"{name} {state} India".strip()
    cache_key = f"meta:{query.lower()}"

    cached = _cache.get(cache_key)
    if cached and monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        # Cache stores the full metadata dict serialised as a single value
        return cached[1]  # type: ignore[return-value]

    async def _request() -> dict[str, str | None]:
        async with httpx.AsyncClient(
            timeout=10.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
        ) as client:
            title, lead_image = await _top_article(client, query)
            photo_url: str | None = None
            if _is_photo(lead_image):
                photo_url = _clean(str(lead_image))
            elif title:
                photo_url = await _first_photo_in_article(client, title)

            if not photo_url:
                return empty_result

            attribution = await _get_image_attribution(client, photo_url)
            return {
                "url": photo_url,
                "source": "Wikimedia Commons",
                "source_url": attribution.get("source_url"),
                "author": attribution.get("author"),
                "license": attribution.get("license"),
            }

    try:
        result = await photos_breaker.call(_request)
    except Exception as exc:
        logger.warning(
            "Destination photo+metadata lookup failed for %r: %s", query, type(exc).__name__
        )
        result = empty_result

    _cache[cache_key] = (monotonic(), result)  # type: ignore[assignment]
    return result

