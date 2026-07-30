# app/db.py — acceso a SQLite: esquema, helpers y semillas.
import os, sqlite3
from config import DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    host        TEXT NOT NULL DEFAULT 'localhost',
    port        INTEGER NOT NULL DEFAULT 25,
    use_tls     INTEGER NOT NULL DEFAULT 0,
    username    TEXT,
    password    TEXT,
    from_name   TEXT NOT NULL DEFAULT 'Soporte TI',
    from_email  TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS templates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    subject     TEXT NOT NULL,
    landing     TEXT NOT NULL DEFAULT 'microsoft',
    html        TEXT NOT NULL,
    text        TEXT NOT NULL DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS targets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    INTEGER NOT NULL,
    email       TEXT NOT NULL,
    first_name  TEXT DEFAULT '',
    last_name   TEXT DEFAULT '',
    position    TEXT DEFAULT '',
    UNIQUE(group_id, email),
    FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS campaigns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    profile_id  INTEGER,
    template_id INTEGER,
    group_id    INTEGER,
    base_url    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'draft',
    delay_min   INTEGER NOT NULL DEFAULT 45,
    delay_max   INTEGER NOT NULL DEFAULT 120,
    created_at  TEXT DEFAULT (datetime('now')),
    launched_at TEXT,
    FOREIGN KEY(profile_id)  REFERENCES profiles(id)  ON DELETE SET NULL,
    FOREIGN KEY(template_id) REFERENCES templates(id) ON DELETE SET NULL,
    FOREIGN KEY(group_id)    REFERENCES groups(id)    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS results (
    token        TEXT PRIMARY KEY,
    campaign_id  INTEGER NOT NULL,
    email        TEXT NOT NULL,
    pretext      TEXT,
    landing      TEXT,
    sent_at      TEXT, opened_at TEXT, clicked_at TEXT, submitted_at TEXT,
    ip           TEXT, user_agent TEXT,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);
"""


def get_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def query(sql, args=(), one=False):
    con = get_db()
    cur = con.execute(sql, args)
    rows = cur.fetchall()
    con.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    con = get_db()
    cur = con.execute(sql, args)
    con.commit()
    last = cur.lastrowid
    con.close()
    return last


def init_db():
    con = get_db()
    con.executescript(SCHEMA)
    con.commit()
    con.close()
    _seed()


def _seed():
    """Siembra un perfil local, un grupo y las plantillas por defecto si están vacías."""
    from app.pretexts import DEFAULT_PROFILE, DEFAULT_GROUP, DEFAULT_TEMPLATES
    if query("SELECT COUNT(*) c FROM profiles", one=True)["c"] == 0:
        p = DEFAULT_PROFILE
        execute("""INSERT INTO profiles(name,host,port,use_tls,username,password,from_name,from_email)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (p["name"], p["host"], p["port"], p["use_tls"], p["username"],
                 p["password"], p["from_name"], p["from_email"]))
    if query("SELECT COUNT(*) c FROM groups", one=True)["c"] == 0:
        execute("INSERT INTO groups(name) VALUES(?)", (DEFAULT_GROUP,))
    if query("SELECT COUNT(*) c FROM templates", one=True)["c"] == 0:
        for t in DEFAULT_TEMPLATES:
            execute("""INSERT INTO templates(name,subject,landing,html,text)
                       VALUES(?,?,?,?,?)""",
                    (t["name"], t["subject"], t["landing"], t["html"], t["text"]))
