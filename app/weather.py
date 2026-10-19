"""Het weer voor de zijbalk via Open-Meteo (gratis, geen account of sleutel).

Alleen de server praat met Open-Meteo; de pagina zelf laadt niets van buitenaf.
"""
import logging
import time

import httpx

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 15 * 60

_cache = {"key": None, "at": 0.0, "data": None}


class PlaceNotFound(Exception):
    pass


def geocode(place: str):
    """Plaatsnaam -> (naam, breedtegraad, lengtegraad). Synchroon: wordt alleen bij het opslaan gebruikt."""
    try:
        r = httpx.get(GEOCODE_URL, params={"name": place, "count": 1, "language": "nl", "format": "json"}, timeout=6)
        r.raise_for_status()
        results = r.json().get("results") or []
    except (httpx.HTTPError, ValueError) as e:
        logging.info("Plaats opzoeken mislukt: %s", e)
        raise PlaceNotFound("De plaats kon niet worden opgezocht. Heeft de server internet?")
    if not results:
        raise PlaceNotFound(f"Plaats '{place}' niet gevonden. Probeer een grotere plaats in de buurt.")
    hit = results[0]
    return str(hit.get("name") or place)[:80], f"{float(hit['latitude']):.4f}", f"{float(hit['longitude']):.4f}"


async def current(place: str, lat: str, lon: str):
    """Actuele temperatuur en weertype. Bij een storing: het laatst bekende weer, anders een foutmelding."""
    key = f"{lat},{lon}"
    now = time.time()
    if _cache["key"] == key and _cache["data"] and now - _cache["at"] < CACHE_SECONDS:
        return _cache["data"]
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(FORECAST_URL, params={
                "latitude": lat, "longitude": lon, "timezone": "auto",
                "current": "temperature_2m,weather_code,is_day"})
            r.raise_for_status()
            cur = r.json()["current"]
        data = {"enabled": True, "place": place, "temp": round(float(cur["temperature_2m"])),
                "code": int(cur["weather_code"]), "is_day": bool(cur.get("is_day", 1))}
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
        logging.info("Weer ophalen mislukt: %s", e)
        if _cache["key"] == key and _cache["data"]:
            return _cache["data"]
        return {"enabled": True, "place": place, "error": True}
    _cache.update(key=key, at=now, data=data)
    return data
