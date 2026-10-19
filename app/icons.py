"""Iconen ophalen en lokaal cachen in /config/icons.

Het veld 'icoon' van een link kan zijn:
  (leeg)          favicon van de site zelf (werkt ook voor diensten in je thuisnetwerk)
  sonarr          naam uit dashboard-icons, anders selfh.st/icons
  di:sonarr       alleen dashboard-icons
  sh:sonarr       alleen selfh.st/icons
  https://…       een eigen afbeelding
  upload:abc.png  een zelf geüpload icoon (staat in /config/uploads)
  🎬              een emoji of kort tekstje (wordt in de browser getekend, niet opgehaald)
"""
import hashlib
import logging
import os
import re
import time
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from . import db

log = logging.getLogger("linker.icons")
ICON_DIR = os.path.join(db.DATA_DIR, "icons")
MAX_BYTES = 1024 * 1024
MISS_TTL = 3600   # een mislukte poging pas na een uur opnieuw
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
DASHBOARD_ICONS = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons@main/{fmt}/{name}.{fmt}"
SELFHST_ICONS = "https://cdn.jsdelivr.net/gh/selfhst/icons@main/{fmt}/{name}.{fmt}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Linker)"}

TYPES = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "ico": "image/x-icon",
         "svg": "image/svg+xml", "webp": "image/webp"}


def is_text_icon(spec: str) -> bool:
    spec = (spec or "").strip()
    return bool(spec) and not spec.startswith(("http://", "https://", "di:", "sh:", "upload:")) and not SLUG.match(spec)


def sniff(data: bytes):
    head = data[:512].lstrip()
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8"):
        return "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data.startswith(b"\x00\x00\x01\x00"):
        return "ico"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if b"<svg" in head.lower() or (head.startswith(b"<?xml") and b"<svg" in data[:2048].lower()):
        return "svg"
    return None


class _IconLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []   # (prioriteit, href)

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        rel = a.get("rel", "").lower()
        href = a.get("href")
        if not href or "icon" not in rel:
            return
        if "apple-touch-icon" in rel:
            prio = 0
        elif "svg" in a.get("type", "") or href.lower().endswith(".svg"):
            prio = 1
        elif "mask-icon" in rel:
            return   # eenkleurig silhouet, ziet er slecht uit
        else:
            prio = 2
        self.found.append((prio, href))


async def _get_image(client, url):
    try:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        data = r.content[:MAX_BYTES + 1]
        if len(data) > MAX_BYTES:
            return None
        kind = sniff(data)
        return (data, kind) if kind else None
    except (httpx.HTTPError, ValueError) as e:
        log.debug("icoon %s: %s", url, e)
        return None


def _candidates_for_name(spec):
    if spec.startswith("di:"):
        sources, name = [DASHBOARD_ICONS], spec[3:]
    elif spec.startswith("sh:"):
        sources, name = [SELFHST_ICONS], spec[3:]
    else:
        sources, name = [DASHBOARD_ICONS, SELFHST_ICONS], spec
    name = name.strip().lower()
    return [src.format(fmt=fmt, name=name) for src in sources for fmt in ("svg", "png")]


async def _fetch(spec, page_url):
    async with httpx.AsyncClient(timeout=6, follow_redirects=True, verify=False, headers=HEADERS) as client:
        if spec.startswith(("http://", "https://")):
            return await _get_image(client, spec)
        if spec:
            for url in _candidates_for_name(spec):
                if got := await _get_image(client, url):
                    return got
            return None
        # Favicon van de pagina zelf
        candidates = []
        try:
            r = await client.get(page_url)
            parser = _IconLinks()
            parser.feed(r.text[:200_000])
            base = str(r.url)
            candidates = [urljoin(base, href) for _, href in sorted(parser.found, key=lambda x: x[0])]
            candidates.append(urljoin(base, "/favicon.ico"))
        except (httpx.HTTPError, ValueError) as e:
            log.debug("pagina %s: %s", page_url, e)
            candidates.append(urljoin(page_url, "/favicon.ico"))
        for url in dict.fromkeys(candidates):
            if got := await _get_image(client, url):
                return got
    return None


def _key(spec, page_url):
    return hashlib.sha1(f"{spec}|{'' if spec else page_url}".encode()).hexdigest()


def cached(spec, page_url):
    key = _key(spec, page_url)
    for ext in TYPES:
        path = os.path.join(ICON_DIR, f"{key}.{ext}")
        if os.path.exists(path):
            return path, TYPES[ext]
    return None


async def resolve(spec, page_url, force=False):
    """Geeft (pad, mediatype) of None."""
    spec = (spec or "").strip()
    if is_text_icon(spec):
        return None
    if spec.startswith("upload:"):
        name = os.path.basename(spec[7:])
        path = os.path.join(db.UPLOAD_DIR, name)
        ext = name.rsplit(".", 1)[-1].lower()
        return (path, TYPES[ext]) if os.path.exists(path) and ext in TYPES else None
    os.makedirs(ICON_DIR, exist_ok=True)
    key = _key(spec, page_url)
    miss = os.path.join(ICON_DIR, f"{key}.miss")
    if force:
        clear(spec, page_url)
    elif hit := cached(spec, page_url):
        return hit
    elif os.path.exists(miss) and time.time() - os.path.getmtime(miss) < MISS_TTL:
        return None
    got = await _fetch(spec, page_url)
    if not got:
        open(miss, "w").close()
        return None
    data, ext = got
    path = os.path.join(ICON_DIR, f"{key}.{ext}")
    with open(path, "wb") as f:
        f.write(data)
    if os.path.exists(miss):
        os.remove(miss)
    return path, TYPES[ext]


def clear(spec, page_url):
    key = _key((spec or "").strip(), page_url)
    for ext in [*TYPES, "miss"]:
        path = os.path.join(ICON_DIR, f"{key}.{ext}")
        if os.path.exists(path):
            os.remove(path)
