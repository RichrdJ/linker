"""Herkent en vertaalt importbestanden naar collecties → secties → links.

Ondersteund: Linker-back-up, ctrlTAB-back-up, Linkwarden-export (JSON)
en browserbladwijzers (Netscape HTML uit Chrome, Firefox, Edge, Safari).
"""
import json
from html.parser import HTMLParser


class ImportError_(ValueError):
    pass


def detect(raw: bytes):
    """Geeft (soort, collecties, instellingen, vervangen)."""
    text = raw.decode("utf-8-sig", errors="replace").lstrip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except ValueError:
            raise ImportError_("Dit bestand is geen geldige JSON.")
        return _from_json(data)
    if "NETSCAPE-Bookmark-file" in text[:500] or "<DL>" in text.upper()[:5000]:
        return "bladwijzers", parse_bookmarks(text), None, False
    raise ImportError_("Onbekend bestand. Kies een Linker- of ctrlTAB-back-up, een Linkwarden-export "
                       "of een bladwijzerbestand (.html) uit je browser.")


def _from_json(data):
    if not isinstance(data, dict):
        raise ImportError_("Onbekend JSON-formaat.")
    # Linker
    if data.get("app") == "linker" and isinstance(data.get("collections"), list):
        return "linker", data["collections"], data.get("settings"), True
    cols = data.get("collections")
    if isinstance(cols, list):
        # ctrlTAB: collecties met secties, links met 'title'
        if any(isinstance(c, dict) and isinstance(c.get("sections"), list) for c in cols):
            out = [{"name": c.get("name"), "icon": "", "sections": [
                {"name": s.get("name"), "links": [
                    {"name": l.get("title") or l.get("url"), "url": l.get("url"),
                     "icon": l.get("favicon") if str(l.get("favicon") or "").startswith("http") else "",
                     "check_enabled": False}
                    for l in s.get("links") or [] if isinstance(l, dict)]}
                for s in c.get("sections") or [] if isinstance(s, dict)]}
                for c in cols if isinstance(c, dict)]
            return "ctrlTAB", out, None, False
        # Linkwarden: collecties met links
        if any(isinstance(c, dict) and isinstance(c.get("links"), list) for c in cols):
            out = [{"name": c.get("name"), "sections": [{"name": "Links", "links": [
                {"name": l.get("name") or l.get("url"), "url": l.get("url"),
                 "description": (l.get("description") or "")[:200], "check_enabled": False}
                for l in c.get("links") or [] if isinstance(l, dict)]}]}
                for c in cols if isinstance(c, dict)]
            return "Linkwarden", out, None, False
    raise ImportError_("Onbekend JSON-formaat. Kies een Linker- of ctrlTAB-back-up of een Linkwarden-export.")


class _Bookmarks(HTMLParser):
    """Netscape-bladwijzers: elke map wordt een sectie ('Map / Submap')."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.path = []          # mapnamen
        self.pending = None     # mapnaam van de laatste <H3>, wacht op <DL>
        self.in_h3 = False
        self.in_a = False
        self.href = None
        self.title = ""
        self.sections = {}      # pad -> [links]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h3":
            self.in_h3, self.pending = True, ""
        elif tag == "dl":
            self.path.append(self.pending)   # None voor het hoofdniveau
            self.pending = None
        elif tag == "a":
            self.in_a, self.href, self.title = True, a.get("href"), ""

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_h3 = False
        elif tag == "dl" and self.path:
            self.path.pop()
        elif tag == "a" and self.in_a:
            self.in_a = False
            if self.href and not self.href.lower().startswith(("javascript:", "place:", "data:")):
                key = " / ".join(p for p in self.path if p) or "Losse links"
                self.sections.setdefault(key, []).append(
                    {"name": self.title.strip() or self.href, "url": self.href, "check_enabled": False})

    def handle_data(self, data):
        if self.in_h3:
            self.pending += data
        elif self.in_a:
            self.title += data


def parse_bookmarks(text):
    p = _Bookmarks()
    p.feed(text)
    sections = [{"name": name[:80], "links": links} for name, links in p.sections.items() if links]
    if not sections:
        raise ImportError_("Geen bladwijzers gevonden in dit bestand.")
    return [{"name": "Bladwijzers", "sections": sections}]
