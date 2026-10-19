"""Controleert periodiek of de links bereikbaar zijn (groen/rood bolletje)."""
import asyncio
import logging
import time

import httpx

from . import db

log = logging.getLogger("linker.status")
RESULTS = {}          # link_id -> {"up": bool, "code": int|None, "ms": int, "at": float, "error": str}
_wake = asyncio.Event()
_task = None
_loop_ref = None


async def _check_one(client, link):
    url = link["check_url"] or link["url"]
    started = time.monotonic()
    try:
        r = await client.head(url)
        if r.status_code in (405, 501):          # HEAD niet ondersteund
            r = await client.get(url)
        # 401/403 = de dienst draait, je bent alleen niet ingelogd
        up = r.status_code < 500
        res = {"up": up, "code": r.status_code, "error": ""}
    except httpx.TimeoutException:
        res = {"up": False, "code": None, "error": "Geen antwoord binnen 6 seconden"}
    except httpx.ConnectError:
        res = {"up": False, "code": None, "error": "Geen verbinding (dienst uit of adres onbekend)"}
    except httpx.HTTPError as e:
        res = {"up": False, "code": None, "error": type(e).__name__}
    res["ms"] = int((time.monotonic() - started) * 1000)
    res["at"] = time.time()
    RESULTS[link["id"]] = res


async def check_all():
    links = db.all_rows("SELECT id, url, check_url FROM links WHERE check_enabled = 1")
    wanted = {link["id"] for link in links}
    for lid in list(RESULTS):
        if lid not in wanted:
            RESULTS.pop(lid, None)
    if not links:
        return
    limits = httpx.Limits(max_connections=20)
    async with httpx.AsyncClient(timeout=6, follow_redirects=True, verify=False, limits=limits,
                                 headers={"User-Agent": "Linker status check"}) as client:
        await asyncio.gather(*(_check_one(client, link) for link in links))


async def _loop():
    while True:
        try:
            interval = int(db.settings().get("check_interval") or 0)
        except ValueError:
            interval = 0
        _wake.clear()   # vóór de controle, zodat een trigger tijdens de controle niet verloren gaat
        if interval > 0:
            try:
                await check_all()
            except Exception:  # noqa: BLE001 - de lus mag nooit stoppen
                log.exception("Statuscontrole mislukt")
        else:
            RESULTS.clear()
        try:
            await asyncio.wait_for(_wake.wait(), timeout=max(interval, 15) if interval > 0 else 60)
        except asyncio.TimeoutError:
            pass


def trigger():
    """Direct opnieuw controleren, bv. na het toevoegen van een link (thread-safe)."""
    if _loop_ref:
        _loop_ref.call_soon_threadsafe(_wake.set)


def start():
    global _task, _loop_ref
    _loop_ref = asyncio.get_running_loop()
    _task = _loop_ref.create_task(_loop())


async def stop():
    if _task:
        _task.cancel()
