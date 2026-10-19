import hashlib
import hmac
import ipaddress
import logging
import os
import math
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import date
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from . import appicon, auth, db, icons, importers, status

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "VERSION")) as _f:
    APP_VERSION = _f.read().strip()

SEARCH_ENGINES = {
    "duckduckgo": ("DuckDuckGo", "https://duckduckgo.com/?q={q}"),
    "google": ("Google", "https://www.google.com/search?q={q}"),
    "startpage": ("Startpage", "https://www.startpage.com/sp/search?query={q}"),
    "bing": ("Bing", "https://www.bing.com/search?q={q}"),
    "brave": ("Brave Search", "https://search.brave.com/search?q={q}"),
    "kagi": ("Kagi", "https://kagi.com/search?q={q}"),
    "ecosia": ("Ecosia", "https://www.ecosia.org/search?q={q}"),
    "custom": ("Eigen zoekmachine", ""),
}


def _secret_key():
    path = os.path.join(db.DATA_DIR, ".secret_key")
    os.makedirs(db.DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


@asynccontextmanager
async def lifespan(_app):
    db.init()
    if os.environ.get("RESET_PASSWORD") == "1":   # wachtwoord vergeten: eenmalig starten met RESET_PASSWORD=1
        db.set_settings({"password_hash": "", "require_login": "0"})
        logging.warning("RESET_PASSWORD=1: wachtwoord en verplicht inloggen zijn uitgezet. Haal de variabele weer weg.")
    status.start()
    yield
    await status.stop()


app = FastAPI(title="Linker", lifespan=lifespan, docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))


# ---------------------------------------------------------------- wachtwoord en sessie

PASSWORD_MIN = 8
SESSION_LONG = 30 * 24 * 3600    # "ingelogd blijven"
SESSION_SHORT = 12 * 3600
guard = auth.LoginGuard()


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2$600000${salt}${digest}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split("$")
        test = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(test, digest)
    except ValueError:
        return False


def password_hash() -> str:
    return db.settings(include_secret=True).get("password_hash") or ""


def locked() -> bool:
    return bool(password_hash())


def login_required() -> bool:
    """De hele startpagina zit achter de login (kan alleen met een wachtwoord)."""
    s = db.settings(include_secret=True)
    return s.get("require_login") == "1" and bool(s.get("password_hash"))


def _session_tag(stored: str) -> str:
    # Hoort bij het huidige wachtwoord: na een nieuw wachtwoord is iedereen uitgelogd
    return hashlib.sha256(("linker-session:" + stored).encode()).hexdigest()[:32]


def logged_in(request: Request) -> bool:
    stored = password_hash()
    if not stored:
        return False
    s = request.session
    try:
        fresh = float(s.get("exp", 0)) > time.time()
    except (TypeError, ValueError):
        fresh = False
    return fresh and hmac.compare_digest(str(s.get("auth", "")), _session_tag(stored))


def start_session(request: Request, stored: str, remember: bool = True):
    request.session.clear()
    request.session.update(auth=_session_tag(stored), exp=time.time() + (SESSION_LONG if remember else SESSION_SHORT))


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "onbekend"


def can_edit(request: Request) -> bool:
    return not locked() or logged_in(request)


# ---------------------------------------------------------------- toegang tot de hele pagina

# Ook zonder login bereikbaar: de loginpagina zelf, wat die nodig heeft en de healthcheck
PUBLIC_PATHS = {"/login", "/logout", "/favicon.svg", "/icon-192.png", "/icon-512.png",
                "/manifest.webmanifest", "/healthz", "/health"}
SECURITY_HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin"}
NO_FRAMES = {"X-Frame-Options": "DENY"}


async def gate(request: Request, call_next):
    path = request.url.path
    required = login_required()
    if required and path not in PUBLIC_PATHS and not path.startswith("/static/") and not logged_in(request):
        if request.method == "GET" and not path.startswith("/api/"):
            target = path + ("?" + request.url.query if request.url.query else "")
            response = RedirectResponse("/login" + ("?" + urlencode({"next": target}) if target != "/" else ""),
                                        status_code=303)
        else:
            response = JSONResponse({"detail": "Log eerst in.", "login": True}, status_code=401)
    else:
        response = await call_next(request)
    for key, value in {**SECURITY_HEADERS, **(NO_FRAMES if required else {})}.items():
        response.headers.setdefault(key, value)
    return response


# Volgorde: de laatst toegevoegde draait als eerste. gate heeft de sessie nodig, dus die staat binnenin.
app.middleware("http")(gate)
app.add_middleware(SessionMiddleware, secret_key=_secret_key(), session_cookie="linker",
                   max_age=90 * 24 * 3600, same_site="lax", https_only=False)
app.add_middleware(auth.SecureCookieOnHttps, cookie_name="linker")
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")


def require_edit(request: Request):
    if not can_edit(request):
        raise HTTPException(401, "Bewerken is beveiligd met een wachtwoord. Ontgrendel eerst.")


# ---------------------------------------------------------------- invoer

def normalize_url(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        raise HTTPException(422, "Vul een adres in.")
    scheme = url.split(":", 1)[0].lower() if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url) else ""
    if scheme in ("javascript", "data", "vbscript", "file"):
        raise HTTPException(422, "Dit soort adres is niet toegestaan.")
    if scheme and (url.startswith(f"{scheme}://") or scheme in ("mailto", "tel")):
        return url
    # Geen schema: lokaal adres (IP, poort, localhost, .lan/.local) -> http, anders https
    host = re.split(r"[/:?#]", url, 1)[0].lower()
    local = host in ("localhost",) or host.endswith((".lan", ".local", ".home", ".internal")) or ":" in url
    try:
        ipaddress.ip_address(host)
        local = True
    except ValueError:
        pass
    return ("http://" if local else "https://") + url


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CollectionIn(NameIn):
    icon: str = Field(default="", max_length=500)


class SectionIn(NameIn):
    collection_id: int


class LinkIn(BaseModel):
    section_id: int
    name: str = Field(default="", max_length=80)    # leeg = titel van de pagina
    url: str = Field(min_length=1, max_length=2000)
    description: str = Field(default="", max_length=200)
    icon: str = Field(default="", max_length=500)
    check_enabled: bool = False
    check_url: str = Field(default="", max_length=2000)


class OrderIn(BaseModel):
    collections: list[int] | None = None
    sections: dict[str, list[int]] | None = None
    links: dict[str, list[int]] | None = None


class LoginIn(BaseModel):
    password: str


class SettingsIn(BaseModel):
    title: str | None = Field(default=None, max_length=60)
    search_engine: str | None = None
    search_custom: str | None = Field(default=None, max_length=500)
    new_tab: bool | None = None
    theme: str | None = None
    accent: str | None = None
    show_clock: bool | None = None
    show_subtitle: bool | None = None
    show_category_icons: bool | None = None
    card_size: str | None = None
    background_dim: bool | None = None
    check_interval: int | None = Field(default=None, ge=0, le=86400)
    new_password: str | None = Field(default=None, max_length=200)
    remove_password: bool | None = None
    require_login: bool | None = None


def _link_values(body: LinkIn):
    if not db.one("SELECT id FROM sections WHERE id = ?", (body.section_id,)):
        raise HTTPException(404, "Die sectie bestaat niet meer. Ververs de pagina.")
    check_url = normalize_url(body.check_url) if body.check_url.strip() else ""
    url = normalize_url(body.url)
    name = body.name.strip() or _host(url)
    return (body.section_id, name, url, body.description.strip(),
            body.icon.strip(), 1 if body.check_enabled else 0, check_url)


def _host(url):
    host = urlparse(url).hostname or url
    return host.removeprefix("www.")[:80]


def _state(request: Request):
    s = db.settings()
    engine = s["search_engine"]
    search_url = s["search_custom"] if engine == "custom" else SEARCH_ENGINES.get(engine, SEARCH_ENGINES["duckduckgo"])[1]
    return {
        "collections": db.tree(),
        "settings": s,
        "search_url": search_url or SEARCH_ENGINES["duckduckgo"][1],
        "engines": {k: v[0] for k, v in SEARCH_ENGINES.items()},
        "locked": locked(),
        "login_required": login_required(),
        "can_edit": can_edit(request),
        "version": APP_VERSION,
    }


# ---------------------------------------------------------------- pagina's

@app.get("/")
def index(request: Request):
    state = _state(request)
    s = state["settings"]
    return templates.TemplateResponse(request, "index.html", {"state": state, "state_json": db.dumps(state),
                                                              "s": s, "accent_ink": appicon.ink_for(s["accent"]),
                                                              "version": APP_VERSION})


@app.get("/manifest.webmanifest")
def manifest():
    s = db.settings()
    c = s["accent"].lstrip("#")
    return JSONResponse({
        "name": s["title"], "short_name": s["title"], "start_url": "/", "display": "standalone",
        "background_color": "#141a22", "theme_color": "#141a22",
        "icons": [{"src": f"/icon-192.png?c={c}", "sizes": "192x192", "type": "image/png"},
                  {"src": f"/icon-512.png?c={c}", "sizes": "512x512", "type": "image/png"},
                  {"src": f"/favicon.svg?c={c}", "sizes": "any", "type": "image/svg+xml"}],
    }, media_type="application/manifest+json")


# Logo in de accentkleur. ?c= is alleen om de browsercache te omzeilen als de kleur wijzigt.
@app.get("/favicon.svg")
def favicon():
    return Response(appicon.svg(db.settings()["accent"]), media_type="image/svg+xml",
                    headers={"Cache-Control": "no-cache"})


@app.get("/icon-192.png")
def app_icon_192():
    return _app_icon(192)


@app.get("/icon-512.png")
def app_icon_512():
    return _app_icon(512)


def _app_icon(size: int):
    accent = db.settings()["accent"]
    try:
        data = appicon.png(os.path.join(HERE, "static", f"icon-{size}.png"), accent)
    except Exception:   # nooit een kapot icoon: dan maar het standaardblauw
        logging.exception("App-icoon in accentkleur maken mislukt")
        return FileResponse(os.path.join(HERE, "static", f"icon-{size}.png"), media_type="image/png")
    return Response(data, media_type="image/png", headers={"Cache-Control": "no-cache"})


@app.get("/healthz")
@app.get("/health")
def healthz():
    return {"ok": True, "version": APP_VERSION}


@app.get("/api/state")
def api_state(request: Request):
    return _state(request)


@app.get("/api/status")
def api_status():
    return {str(k): v for k, v in status.RESULTS.items()}


# ---------------------------------------------------------------- iconen

ICON_HEADERS = {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
                "X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=604800"}


@app.get("/icon/{link_id}")
async def icon(link_id: int):
    link = db.one("SELECT url, icon FROM links WHERE id = ?", (link_id,))
    if not link:
        raise HTTPException(404)
    got = await icons.resolve(link["icon"], link["url"])
    if not got:
        return Response(status_code=404, headers={"Cache-Control": "no-store"})
    path, media = got
    return FileResponse(path, media_type=media, headers=ICON_HEADERS)


@app.get("/api/icon-preview", dependencies=[Depends(require_edit)])
async def icon_preview(icon: str = "", url: str = ""):
    """Voorbeeld in het linkformulier, vóór het opslaan."""
    try:
        page = normalize_url(url) if url.strip() else ""
    except HTTPException:
        page = ""
    if not icon.strip() and not page:
        raise HTTPException(404)
    got = await icons.resolve(icon, page)
    if not got:
        return Response(status_code=404, headers={"Cache-Control": "no-store"})
    path, media = got
    return FileResponse(path, media_type=media, headers=ICON_HEADERS)


@app.get("/api/page-info", dependencies=[Depends(require_edit)])
async def page_info(url: str):
    """Titel van een pagina, om het naamveld van een nieuwe snelkoppeling voor te vullen."""
    full = normalize_url(url)
    return {"url": full, "title": await icons.page_title(full)}


@app.post("/api/links/{link_id}/icon/refresh", dependencies=[Depends(require_edit)])
async def refresh_icon(link_id: int):
    link = db.one("SELECT url, icon FROM links WHERE id = ?", (link_id,))
    if not link:
        raise HTTPException(404, "Snelkoppeling niet gevonden.")
    got = await icons.resolve(link["icon"], link["url"], force=True)
    return {"found": bool(got)}


# ---------------------------------------------------------------- collecties

@app.post("/api/collections", dependencies=[Depends(require_edit)])
def create_collection(body: CollectionIn):
    cid = db.execute("INSERT INTO collections (name, icon, position) VALUES (?, ?, ?)",
                     (body.name.strip(), body.icon.strip(), db.next_position("collections")))
    db.execute("INSERT INTO sections (collection_id, name, position) VALUES (?, ?, 0)", (cid, db.DEFAULT_SECTION))
    return {"id": cid}


@app.put("/api/collections/{collection_id}", dependencies=[Depends(require_edit)])
def update_collection(collection_id: int, body: CollectionIn):
    db.execute("UPDATE collections SET name = ?, icon = ? WHERE id = ?",
               (body.name.strip(), body.icon.strip(), collection_id))
    return {"ok": True}


@app.delete("/api/collections/{collection_id}", dependencies=[Depends(require_edit)])
def delete_collection(collection_id: int):
    db.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    return {"ok": True}


# ---------------------------------------------------------------- secties

def _collection_or_404(collection_id):
    if not db.one("SELECT id FROM collections WHERE id = ?", (collection_id,)):
        raise HTTPException(404, "Die categorie bestaat niet meer. Ververs de pagina.")


@app.post("/api/sections", dependencies=[Depends(require_edit)])
def create_section(body: SectionIn):
    _collection_or_404(body.collection_id)
    sid = db.execute("INSERT INTO sections (collection_id, name, position) VALUES (?, ?, ?)",
                     (body.collection_id, body.name.strip(),
                      db.next_position("sections", "WHERE collection_id = ?", (body.collection_id,))))
    return {"id": sid}


@app.put("/api/sections/{section_id}", dependencies=[Depends(require_edit)])
def update_section(section_id: int, body: SectionIn):
    old = db.one("SELECT collection_id FROM sections WHERE id = ?", (section_id,))
    if not old:
        raise HTTPException(404, "Sectie niet gevonden.")
    _collection_or_404(body.collection_id)
    db.execute("UPDATE sections SET name = ?, collection_id = ? WHERE id = ?",
               (body.name.strip(), body.collection_id, section_id))
    if old["collection_id"] != body.collection_id:   # verplaatst: achteraan in de nieuwe categorie
        db.execute("UPDATE sections SET position = ? WHERE id = ?",
                   (db.next_position("sections", "WHERE collection_id = ?", (body.collection_id,)), section_id))
    return {"ok": True}


@app.delete("/api/sections/{section_id}", dependencies=[Depends(require_edit)])
def delete_section(section_id: int):
    db.execute("DELETE FROM sections WHERE id = ?", (section_id,))
    return {"ok": True}


@app.post("/api/sections/{section_id}/sort", dependencies=[Depends(require_edit)])
def sort_section(section_id: int, by: str = "name"):
    if by not in db.SORT_ORDERS:
        raise HTTPException(422, "Onbekende sortering.")
    db.sort_section(section_id, by)
    return {"ok": True}


# ---------------------------------------------------------------- links

@app.post("/api/links", dependencies=[Depends(require_edit)])
async def create_link(body: LinkIn):
    if not body.name.strip():   # geen naam opgegeven: de titel van de pagina
        body.name = await icons.page_title(normalize_url(body.url))
    values = _link_values(body)
    lid = db.execute(
        "INSERT INTO links (section_id, name, url, description, icon, check_enabled, check_url, position) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (*values, db.next_position("links", "WHERE section_id = ?", (body.section_id,))))
    status.trigger()
    return {"id": lid}


@app.put("/api/links/{link_id}", dependencies=[Depends(require_edit)])
def update_link(link_id: int, body: LinkIn):
    old = db.one("SELECT section_id FROM links WHERE id = ?", (link_id,))
    if not old:
        raise HTTPException(404, "Snelkoppeling niet gevonden.")
    values = _link_values(body)
    db.execute("UPDATE links SET section_id = ?, name = ?, url = ?, description = ?, icon = ?, "
               "check_enabled = ?, check_url = ? WHERE id = ?", (*values, link_id))
    if old["section_id"] != body.section_id:
        db.execute("UPDATE links SET position = ? WHERE id = ?",
                   (db.next_position("links", "WHERE section_id = ?", (body.section_id,)), link_id))
    status.RESULTS.pop(link_id, None)
    status.trigger()
    return {"ok": True}


@app.post("/api/links/{link_id}/move/{collection_id}", dependencies=[Depends(require_edit)])
def move_link(link_id: int, collection_id: int):
    """Snelkoppeling op een categorie in de zijbalk laten vallen: achteraan in de eerste sectie."""
    if not db.one("SELECT id FROM links WHERE id = ?", (link_id,)):
        raise HTTPException(404, "Snelkoppeling niet gevonden.")
    _collection_or_404(collection_id)
    sid = db.first_section(collection_id)
    db.execute("UPDATE links SET section_id = ?, position = ? WHERE id = ?",
               (sid, db.next_position("links", "WHERE section_id = ?", (sid,)), link_id))
    return {"ok": True}


@app.post("/api/links/{link_id}/visit", status_code=204)
def visit_link(link_id: int):
    """Een klik op een snelkoppeling tellen (via sendBeacon, ook als de pagina al wegnavigeert)."""
    db.record_visit(link_id, int(time.time()))
    return Response(status_code=204)


@app.delete("/api/links/{link_id}", dependencies=[Depends(require_edit)])
def delete_link(link_id: int):
    db.execute("DELETE FROM links WHERE id = ?", (link_id,))
    status.RESULTS.pop(link_id, None)
    return {"ok": True}


@app.put("/api/order", dependencies=[Depends(require_edit)])
def save_order(body: OrderIn):
    db.reorder(body.collections, body.sections, body.links)
    return {"ok": True}


# ---------------------------------------------------------------- uploads

MAX_UPLOAD = 8 * 1024 * 1024
ICON_KINDS = {"png", "jpg", "gif", "ico", "svg", "webp"}
BACKGROUND_KINDS = {"png", "jpg", "gif", "webp"}


async def _read_upload(request: Request, kinds, max_bytes):
    data = await request.body()
    if not data:
        raise HTTPException(422, "Er is geen bestand meegestuurd.")
    if len(data) > max_bytes:
        raise HTTPException(413, f"Dit bestand is te groot (max. {max_bytes // 1024 // 1024} MB).")
    kind = icons.sniff(data)
    if kind not in kinds:
        raise HTTPException(422, "Dit bestandstype wordt niet ondersteund. Gebruik " + ", ".join(sorted(kinds)) + ".")
    return data, kind


def _save_upload(data, kind, prefix):
    name = f"{prefix}-{hashlib.sha1(data).hexdigest()[:16]}.{kind}"
    with open(os.path.join(db.UPLOAD_DIR, name), "wb") as f:
        f.write(data)
    return name


@app.post("/api/upload/icon", dependencies=[Depends(require_edit)])
async def upload_icon(request: Request):
    data, kind = await _read_upload(request, ICON_KINDS, 2 * 1024 * 1024)
    return {"icon": "upload:" + _save_upload(data, kind, "icon")}


@app.post("/api/upload/background", dependencies=[Depends(require_edit)])
async def upload_background(request: Request):
    data, kind = await _read_upload(request, BACKGROUND_KINDS, MAX_UPLOAD)
    old = db.settings().get("background")
    name = _save_upload(data, kind, "background")
    db.set_settings({"background": name})
    if old and old != name and os.path.exists(os.path.join(db.UPLOAD_DIR, old)):
        os.remove(os.path.join(db.UPLOAD_DIR, old))
    return _state(request)


@app.delete("/api/upload/background", dependencies=[Depends(require_edit)])
def remove_background(request: Request):
    old = db.settings().get("background")
    db.set_settings({"background": ""})
    if old and os.path.exists(os.path.join(db.UPLOAD_DIR, old)):
        os.remove(os.path.join(db.UPLOAD_DIR, old))
    return _state(request)


@app.get("/background")
def background():
    name = db.settings().get("background")
    path = os.path.join(db.UPLOAD_DIR, os.path.basename(name or ""))
    if not name or not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path, media_type=icons.TYPES[name.rsplit(".", 1)[-1]], headers=ICON_HEADERS)


# ---------------------------------------------------------------- instellingen

THEMES = ("auto", "dark", "light", "oled")
CARD_SIZES = ("compact", "normal")


@app.put("/api/settings", dependencies=[Depends(require_edit)])
def save_settings(request: Request, body: SettingsIn):
    values = {}
    for key in ("title", "search_custom"):
        v = getattr(body, key)
        if v is not None:
            values[key] = v.strip()
    if body.title is not None and not values["title"]:
        values["title"] = "Linker"
    if body.search_engine is not None:
        if body.search_engine not in SEARCH_ENGINES:
            raise HTTPException(422, "Onbekende zoekmachine.")
        values["search_engine"] = body.search_engine
    if body.search_engine == "custom" and "{q}" not in (body.search_custom or ""):
        raise HTTPException(422, "Een eigen zoekmachine heeft {q} nodig op de plek van de zoekterm, "
                                 "bv. https://zoek.voorbeeld.nl/?q={q}")
    if body.theme is not None:
        if body.theme not in THEMES:
            raise HTTPException(422, "Onbekend thema.")
        values["theme"] = body.theme
    if body.accent is not None:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", body.accent):
            raise HTTPException(422, "Kies een kleur als #rrggbb.")
        values["accent"] = body.accent.lower()
    if body.card_size is not None:
        if body.card_size not in CARD_SIZES:
            raise HTTPException(422, "Onbekende kaartgrootte.")
        values["card_size"] = body.card_size
    for key in ("new_tab", "show_clock", "show_subtitle", "show_category_icons", "background_dim"):
        v = getattr(body, key)
        if v is not None:
            values[key] = "1" if v else "0"
    if body.check_interval is not None:
        values["check_interval"] = str(body.check_interval if body.check_interval == 0
                                       else max(body.check_interval, 15))
    new_hash = None
    if body.remove_password:
        values["password_hash"] = ""
        values["require_login"] = "0"   # zonder wachtwoord kan niemand meer inloggen
    elif body.new_password:
        if len(body.new_password) < PASSWORD_MIN:
            raise HTTPException(422, f"Kies een wachtwoord van minstens {PASSWORD_MIN} tekens.")
        new_hash = values["password_hash"] = hash_password(body.new_password)
    if body.require_login is not None and not body.remove_password:
        if body.require_login and not (new_hash or password_hash()):
            raise HTTPException(422, "Stel eerst een wachtwoord in. Zonder wachtwoord kun je niet inloggen.")
        values["require_login"] = "1" if body.require_login else "0"
    db.set_settings(values)
    if body.remove_password:
        request.session.clear()
    elif new_hash:   # nieuw wachtwoord: alle andere apparaten zijn uitgelogd, dit apparaat blijft ingelogd
        start_session(request, new_hash)
    status.trigger()
    return _state(request)


def _login_wait_message(wait: int) -> str:
    minutes = max(1, math.ceil(wait / 60))
    return f"Te veel mislukte pogingen. Probeer het over {minutes} {'minuut' if minutes == 1 else 'minuten'} opnieuw."


@app.post("/api/login")
def login(request: Request, body: LoginIn):
    """Bewerken ontgrendelen vanuit de pagina (als alleen bewerken beveiligd is)."""
    ip = client_ip(request)
    wait = guard.wait_time(ip)
    if wait:
        raise HTTPException(429, _login_wait_message(wait))
    stored = password_hash()
    if stored:
        if not verify_password(body.password, stored):
            guard.failed(ip)
            raise HTTPException(401, "Dat wachtwoord klopt niet.")
        guard.succeeded(ip)
        start_session(request, stored)
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


# ---------------------------------------------------------------- loginpagina

LOGIN_CSP = ("default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
             "manifest-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")


def _login_page(request: Request, next_path: str, error: str = "", status_code: int = 200):
    s = db.settings()
    response = templates.TemplateResponse(
        request, "login.html",
        {"s": s, "accent_ink": appicon.ink_for(s["accent"]), "next": next_path, "error": error, "version": APP_VERSION},
        status_code=status_code)
    response.headers["Content-Security-Policy"] = LOGIN_CSP
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/login")
def login_page(request: Request, next: str = "/"):
    target = auth.safe_next(next)
    if not login_required() or logged_in(request):
        return RedirectResponse(target, status_code=303)
    return _login_page(request, target)


@app.post("/login")
async def login_submit(request: Request):
    raw = await request.body()
    if len(raw) > 8192:
        raise HTTPException(413)
    form = parse_qs(raw.decode("utf-8", "replace"))
    password = (form.get("password") or [""])[0]
    target = auth.safe_next((form.get("next") or ["/"])[0])
    remember = (form.get("remember") or [""])[0] == "1"
    stored = password_hash()
    if not login_required() or not stored:
        return RedirectResponse(target, status_code=303)
    ip = client_ip(request)
    wait = guard.wait_time(ip)
    if wait:
        return _login_page(request, target, _login_wait_message(wait), 429)
    if not password or not await run_in_threadpool(verify_password, password, stored):
        guard.failed(ip)
        logging.warning("Mislukte login vanaf %s", ip)
        return _login_page(request, target, "Dat wachtwoord klopt niet.", 401)
    guard.succeeded(ip)
    start_session(request, stored, remember)
    return RedirectResponse(target, status_code=303)


@app.post("/logout")
def logout_page(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------- back-up

@app.get("/api/export", dependencies=[Depends(require_edit)])
def export():
    return JSONResponse(db.export_data(), headers={
        "Content-Disposition": f'attachment; filename="linker-{date.today().isoformat()}.json"'})


@app.post("/api/import", dependencies=[Depends(require_edit)])
async def import_file(request: Request):
    """Back-up of export van een andere dienst. Een Linker-back-up vervangt alles (tenzij mode=append),
    de rest wordt als nieuwe categorie(ën) toegevoegd."""
    raw = await request.body()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "Dit bestand is te groot (max. 20 MB).")
    try:
        kind, collections, settings_in, replace = importers.detect(raw)
    except importers.ImportError_ as e:
        raise HTTPException(422, str(e))
    if request.query_params.get("mode") == "append":
        replace, settings_in = False, None
    counts = db.insert_tree(collections, replace=replace, settings_in=settings_in)
    if replace:
        status.RESULTS.clear()
    status.trigger()
    return {"kind": kind, "replaced": replace, **counts, "state": _state(request)}


@app.post("/api/import/inspect", dependencies=[Depends(require_edit)])
async def inspect_import(request: Request):
    """Vooraf laten zien wat een import gaat doen."""
    try:
        kind, collections, _, replace = importers.detect(await request.body())
    except importers.ImportError_ as e:
        raise HTTPException(422, str(e))
    links = sum(len(sec.get("links") or []) for c in collections for sec in c.get("sections") or [])
    return {"kind": kind, "replace": replace, "collections": len(collections), "links": links}
