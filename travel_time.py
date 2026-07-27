"""
Travel time lookup using the Google Maps Distance Matrix API.

Requires:
    - pip install requests
    - Environment variable GOOGLE_MAPS_API_KEY set to a valid API key
      with the Distance Matrix API enabled.

Caches results in a local JSON file (travel_cache.json) so repeat runs
(and the many lookups needed for round-building) don't re-query the API
for the same postcode pair.
"""

import os
import json
import requests

_API_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
_CACHE_FILE = "travel_cache.json"

_cache = {}
_cache_loaded = False


class TravelTimeError(Exception):
    pass


def _load_cache():
    global _cache, _cache_loaded
    if _cache_loaded:
        return
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            _cache = {}
    _cache_loaded = True


def _save_cache():
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=2, sort_keys=True)
    except OSError:
        pass  # non-fatal — worst case we just re-query next run


def _cache_key(postcode_a: str, postcode_b: str) -> str:
    return f"{postcode_a.upper()}|{postcode_b.upper()}"

def get_travel_time_minutes(postcode_a: str, postcode_b: str) -> int:
    minutes, _was_cached = get_travel_time_minutes_with_source(postcode_a, postcode_b)
    return minutes


def get_travel_time_minutes_with_source(postcode_a: str, postcode_b: str) -> tuple:
    """Same as get_travel_time_minutes, but also returns whether it was a cache hit."""
    postcode_a = postcode_a.strip()
    postcode_b = postcode_b.strip()

    if not postcode_a or not postcode_b:
        raise TravelTimeError("Both postcodes must be non-empty")

    if postcode_a.upper() == postcode_b.upper():
        return 0, True

    _load_cache()
    key = _cache_key(postcode_a, postcode_b)
    if key in _cache:
        return _cache[key], True

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise TravelTimeError(
            "GOOGLE_MAPS_API_KEY environment variable is not set. "
            "Set it and restart your terminal."
        )

    params = {
        "origins": postcode_a,
        "destinations": postcode_b,
        "mode": "driving",
        "key": api_key,
    }

    response = requests.get(_API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK":
        raise TravelTimeError(f"Distance Matrix API error: {data.get('status')}")

    element = data["rows"][0]["elements"][0]
    if element.get("status") != "OK":
        raise TravelTimeError(
            f"No route found between {postcode_a} and {postcode_b}: {element.get('status')}"
        )

    duration_seconds = element["duration"]["value"]
    minutes = round(duration_seconds / 60)

    _cache[key] = minutes
    reverse_key = _cache_key(postcode_b, postcode_a)
    if reverse_key not in _cache:
        _cache[reverse_key] = minutes

    _save_cache()
    return minutes, False
