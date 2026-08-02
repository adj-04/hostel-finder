"""
Real address geocoding via OpenStreetMap's Nominatim API (free, no API key
required). Used when an owner adds a hostel without supplying lat/lng
directly — instead of guessing coordinates, we ask a real geocoding service
for the real location of the address they typed.

Nominatim's usage policy (https://operations.osmfoundation.org/policies/nominatim/)
requires:
  - A descriptive User-Agent identifying the app (not a browser UA)
  - No more than ~1 request/second, and no bulk/heavy usage without your own
    self-hosted instance
  - Results cached rather than re-requested for the same input where possible

NOTE: this sandbox's network egress is locked to a handful of dev domains
and does not include nominatim.openstreetmap.org, so this specific call
could not be executed/tested from inside this build environment. The code
below follows Nominatim's documented request/response contract closely and
fails safe (returns None, None on any error or timeout) so a flaky network
call never breaks hostel creation — but please do a live smoke test once
you deploy this somewhere with normal internet access.
"""
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ChennaiHostelFinder/1.0 (contact: owner-of-this-repo@example.com)"

# Very small in-process cache so repeated identical addresses (e.g. two
# owners typing "Velachery, Chennai") don't re-hit the API every time.
_geocode_cache = {}


def geocode_address(address, city_hint="Chennai, India", timeout=5):
    """Return (lat, lng) as floats, or (None, None) if geocoding fails.

    `address` should be a human-typed address string, e.g.
    "12 Kamaraj Salai, Velachery, Chennai".
    """
    if not address or not address.strip():
        return None, None

    query = address.strip()
    if city_hint.lower() not in query.lower():
        query = f"{query}, {city_hint}"

    cache_key = query.lower()
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            _geocode_cache[cache_key] = (None, None)
            return None, None
        lat = float(results[0]["lat"])
        lng = float(results[0]["lon"])
        _geocode_cache[cache_key] = (lat, lng)
        return lat, lng
    except Exception:
        # Network error, timeout, bad response shape, etc. — fail safe.
        return None, None
