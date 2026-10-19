"""SQLite-opslag: categorieën (tabel collections) → secties → snelkoppelingen (links), plus instellingen."""
import json
import os
import sqlite3
import threading

DATA_DIR = os.environ.get("DATA_DIR", "/config")
DB_PATH = os.path.join(DATA_DIR, "linker.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
_lock = threading.Lock()

DEFAULT_SETTINGS = {
    "title": "Linker",
    "search_engine": "duckduckgo",
    "search_custom": "",
    "new_tab": "1",
    "theme": "auto",          # auto | dark | light | oled
    "accent": "#3b7ddd",      # zelfde blauw als het logo
    "show_clock": "1",
    "show_subtitle": "1",     # omschrijving of adres onder de naam
    "show_category_icons": "0",  # icoon/emoji voor de categorieën in de zijbalk
    "card_size": "normal",    # compact | normal
    "check_interval": "60",   # seconden, 0 = uit
    "background": "",         # bestandsnaam in uploads/
    "background_dim": "1",
    "password_hash": "",
}
SECRET_SETTINGS = {"password_hash"}

LINK_FIELDS = ("name", "url", "description", "icon", "check_enabled", "check_url")


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        icon TEXT NOT NULL DEFAULT '',
        position INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY,
        collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY,
        section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        icon TEXT NOT NULL DEFAULT '',
        check_enabled INTEGER NOT NULL DEFAULT 1,
        check_url TEXT NOT NULL DEFAULT '',
        position INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
"""


def init():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        # Latere kolommen komen hier als idempotente migratie:
        # _add_column(conn, "links", "kolom", "TEXT NOT NULL DEFAULT ''")
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        # 0.2.2: het oude gele standaardaccent wordt het blauw van het logo
        conn.execute("UPDATE settings SET value = ? WHERE key = 'accent' AND value = '#f0b44c'",
                     (DEFAULT_SETTINGS["accent"],))
        _seed(conn)


STARTER = [("Privé", "🏠"), ("Werk", "💼")]
DEFAULT_SECTION = "Snelkoppelingen"


def _seed(conn):
    """Eerste start: categorieën Privé en Werk, zodat je direct snelkoppelingen kunt toevoegen."""
    if conn.execute("SELECT 1 FROM settings WHERE key = 'seeded'").fetchone():
        return
    if not conn.execute("SELECT 1 FROM collections LIMIT 1").fetchone():
        for pos, (name, icon) in enumerate(STARTER):
            cid = conn.execute("INSERT INTO collections (name, icon, position) VALUES (?, ?, ?)",
                               (name, icon, pos)).lastrowid
            conn.execute("INSERT INTO sections (collection_id, name, position) VALUES (?, ?, 0)",
                         (cid, DEFAULT_SECTION))
    conn.execute("INSERT INTO settings (key, value) VALUES ('seeded', '1')")


def _add_column(conn, table, column, ddl):
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def all_rows(sql, params=()):
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def one(sql, params=()):
    with connect() as conn:
        r = conn.execute(sql, params).fetchone()
        return dict(r) if r else None


def execute(sql, params=()):
    with _lock, connect() as conn:
        return conn.execute(sql, params).lastrowid


def next_position(table, where="", params=()):
    return one(f"SELECT COALESCE(MAX(position), -1) + 1 AS p FROM {table} {where}", params)["p"]


# ---------------------------------------------------------------- instellingen

def settings(include_secret=False):
    rows = {r["key"]: r["value"] for r in all_rows("SELECT key, value FROM settings")}
    merged = {k: rows.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    if not include_secret:
        for k in SECRET_SETTINGS:
            merged.pop(k, None)
    return merged


def set_settings(values: dict):
    with _lock, connect() as conn:
        for k, v in values.items():
            if k in DEFAULT_SETTINGS:
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                             "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (k, str(v)))


# ---------------------------------------------------------------- boom

def tree():
    cols = all_rows("SELECT id, name, icon FROM collections ORDER BY position, id")
    secs = all_rows("SELECT id, collection_id, name FROM sections ORDER BY position, id")
    links = all_rows("SELECT * FROM links ORDER BY position, id")
    by_sec = {s["id"]: {**s, "links": []} for s in secs}
    for link in links:
        link["check_enabled"] = bool(link["check_enabled"])
        if link["section_id"] in by_sec:
            by_sec[link["section_id"]]["links"].append(link)
    by_col = {c["id"]: {**c, "sections": []} for c in cols}
    for s in by_sec.values():
        if s["collection_id"] in by_col:
            by_col[s["collection_id"]]["sections"].append(s)
    return list(by_col.values())


def reorder(collections=None, sections=None, links=None):
    """collections: [id]; sections: {collection_id: [id]}; links: {section_id: [id]}"""
    with _lock, connect() as conn:
        for pos, cid in enumerate(collections or []):
            conn.execute("UPDATE collections SET position = ? WHERE id = ?", (pos, int(cid)))
        for cid, ids in (sections or {}).items():
            for pos, sid in enumerate(ids):
                conn.execute("UPDATE sections SET collection_id = ?, position = ? WHERE id = ?",
                             (int(cid), pos, int(sid)))
        for sid, ids in (links or {}).items():
            for pos, lid in enumerate(ids):
                conn.execute("UPDATE links SET section_id = ?, position = ? WHERE id = ?",
                             (int(sid), pos, int(lid)))


def sort_section(section_id):
    with _lock, connect() as conn:
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM links WHERE section_id = ? ORDER BY name COLLATE NOCASE", (section_id,))]
        for pos, lid in enumerate(ids):
            conn.execute("UPDATE links SET position = ? WHERE id = ?", (pos, lid))


def first_section(collection_id):
    """Eerste sectie van een collectie; maakt er een als die er niet is."""
    s = one("SELECT id FROM sections WHERE collection_id = ? ORDER BY position, id LIMIT 1", (collection_id,))
    if s:
        return s["id"]
    return execute("INSERT INTO sections (collection_id, name, position) VALUES (?, ?, 0)",
                   (collection_id, DEFAULT_SECTION))


# ---------------------------------------------------------------- back-up en import

def export_data():
    return {"app": "linker", "version": 1, "settings": {k: v for k, v in settings().items() if k != "background"},
            "collections": [
                {"name": c["name"], "icon": c["icon"], "sections": [
                    {"name": s["name"], "links": [{k: link[k] for k in LINK_FIELDS} for link in s["links"]]}
                    for s in c["sections"]]}
                for c in tree()]}


def insert_tree(collections, replace=False, settings_in=None):
    """collections: [{name, icon, sections: [{name, links: [{name, url, …}]}]}]. Geeft aantallen terug."""
    counts = {"collections": 0, "sections": 0, "links": 0}
    with _lock, connect() as conn:
        if replace:
            conn.execute("DELETE FROM collections")
        start = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM collections").fetchone()[0]
        for cpos, col in enumerate(collections):
            cid = conn.execute("INSERT INTO collections (name, icon, position) VALUES (?, ?, ?)",
                               (str(col.get("name") or "Collectie")[:80], str(col.get("icon") or "")[:500],
                                start + cpos)).lastrowid
            counts["collections"] += 1
            for spos, sec in enumerate(col.get("sections") or []):
                sid = conn.execute("INSERT INTO sections (collection_id, name, position) VALUES (?, ?, ?)",
                                   (cid, str(sec.get("name") or DEFAULT_SECTION)[:80], spos)).lastrowid
                counts["sections"] += 1
                for lpos, link in enumerate(sec.get("links") or []):
                    url = str(link.get("url") or "").strip()
                    if not url or url.lower().startswith(("javascript:", "data:", "place:", "vbscript:")):
                        continue
                    conn.execute(
                        "INSERT INTO links (section_id, name, url, description, icon, check_enabled, check_url, position) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (sid, str(link.get("name") or url)[:80], url[:2000], str(link.get("description") or "")[:200],
                         str(link.get("icon") or "")[:500], 1 if link.get("check_enabled", True) else 0,
                         str(link.get("check_url") or "")[:2000], lpos))
                    counts["links"] += 1
        for k, v in (settings_in or {}).items():
            if k in DEFAULT_SETTINGS and k not in SECRET_SETTINGS and k != "background":
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                             "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (k, str(v)))
    return counts


def dumps(obj):
    """JSON dat veilig in een <script>-blok past."""
    return (json.dumps(obj, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
