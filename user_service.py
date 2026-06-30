"""
User Service Module

Responsibilities:
- Users: register with a username (display name) + Telegram ID. The username
  is the public identifier shown across the UI; the raw Telegram ID is treated
  as private and is only revealed on demand (see app.py sidebar / Account page).
  New registrations require a non-empty username — login-only flow never
  exposes the Telegram ID directly.
- Groups: each user can create contact groups (e.g. Family, Colleagues) with a
  preferred city. A group holds multiple Telegram IDs and supports one-click
  batch weather push to every member.

Persistence:
- All users / groups / members live in a local SQLite database (``users.db``
  next to this module). The DB survives app restarts and Streamlit refreshes —
  accounts and groups created in past sessions are permanently available.
- The schema is versioned via SQLite ``PRAGMA user_version``. ``init_db`` runs
  forward-only migrations so an existing DB is upgraded in place without losing
  data. See ``_run_migrations``.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# Bump when the schema changes. Add a matching branch in _run_migrations.
SCHEMA_VERSION = 2


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_columns(c, table):
    c.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in c.fetchall()}


def _run_migrations(c):
    """Forward-only schema migrations driven by PRAGMA user_version.

    Each branch upgrades from version N to N+1 and must be idempotent so that
    running it on an already-migrated DB is a no-op. Existing rows are never
    dropped.
    """
    c.execute("PRAGMA user_version")
    current = c.fetchone()[0]

    if current < 2:
        # v1 → v2: add last_login_at to track returning users.
        if "last_login_at" not in _table_columns(c, "users"):
            c.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
        current = 2

    c.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def init_db():
    """Create tables if missing, then run migrations and create indexes."""
    conn = _get_conn()
    c = conn.cursor()

    # ----- users -----
    # nickname is the public display name and is required at registration time
    # (enforced in application code so existing rows with empty nicknames are
    # not broken by a schema change). telegram_id is private — the UI never
    # shows it without an explicit click.
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            nickname TEXT NOT NULL DEFAULT '',
            favorite_city TEXT DEFAULT 'Hong Kong',
            created_at TEXT NOT NULL
        )
    """)

    # ----- groups -----
    c.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT DEFAULT 'Hong Kong',
            description TEXT DEFAULT '',
            owner_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    """)

    # ----- group_members -----
    c.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            telegram_id TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            added_at TEXT NOT NULL,
            UNIQUE(group_id, telegram_id),
            FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE
        )
    """)

    # Bring an existing DB up to the current schema version.
    _run_migrations(c)

    # Indexes that speed up the common lookups (CREATE IF NOT EXISTS is a
    # no-op when they already exist).
    c.execute("CREATE INDEX IF NOT EXISTS idx_groups_owner_id ON groups(owner_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_group_members_telegram_id ON group_members(telegram_id)")

    conn.commit()
    conn.close()


# ============================================================
# User functions
# ============================================================

def user_exists(telegram_id):
    """Return True if the Telegram ID is already registered."""
    telegram_id = (telegram_id or "").strip()
    if not telegram_id:
        return False
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
    found = c.fetchone() is not None
    conn.close()
    return found


def register_user(telegram_id, nickname, favorite_city="Hong Kong"):
    """Register a brand-new user.

    Both telegram_id and nickname are required. Returns the new user dict on
    success, or None if validation fails or the telegram_id is already taken.
    """
    telegram_id = (telegram_id or "").strip()
    nickname = (nickname or "").strip()
    if not telegram_id or not nickname:
        return None
    if user_exists(telegram_id):
        return None

    favorite_city = (favorite_city or "").strip() or "Hong Kong"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (telegram_id, nickname, favorite_city, created_at, last_login_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (telegram_id, nickname, favorite_city, now, now),
        )
        conn.commit()
        c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = dict(c.fetchone())
    except sqlite3.IntegrityError:
        user = None
    conn.close()
    return user


def touch_login(telegram_id):
    """Update last_login_at for a returning user. Safe to call on every login."""
    telegram_id = (telegram_id or "").strip()
    if not telegram_id:
        return False
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET last_login_at = ? WHERE telegram_id = ?", (now, telegram_id))
    conn.commit()
    ok = c.rowcount > 0
    conn.close()
    return ok


def login_user(telegram_id):
    """Login an existing user by Telegram ID.

    Updates ``last_login_at`` and returns the fresh user dict, or None if the
    Telegram ID is not registered.
    """
    user = get_user(telegram_id)
    if not user:
        return None
    touch_login(telegram_id)
    return get_user(telegram_id)


def register_or_login(telegram_id, nickname=None):
    """Login an existing user, or register a new one.

    - If the Telegram ID is already registered, returns the stored user.
    - If it is a new Telegram ID, a non-empty nickname is required to
      complete registration. Without a nickname the function returns None
      so the caller can prompt the user for the missing username.
    """
    telegram_id = (telegram_id or "").strip()
    if not telegram_id:
        return None

    existing = get_user(telegram_id)
    if existing:
        return existing

    if not nickname or not nickname.strip():
        return None

    return register_user(telegram_id, nickname.strip())


def get_user(telegram_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id.strip(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(telegram_id, **kwargs):
    telegram_id = telegram_id.strip()
    allowed = {"nickname", "favorite_city"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    # Nickname is the public identifier — never allow it to be cleared.
    if "nickname" in updates:
        nick = (updates["nickname"] or "").strip()
        if not nick:
            del updates["nickname"]
        else:
            updates["nickname"] = nick
    if not updates:
        return False

    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    if not c.fetchone():
        conn.close()
        return False

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [telegram_id]
    c.execute(f"UPDATE users SET {set_clause} WHERE telegram_id = ?", values)
    conn.commit()
    conn.close()
    return True


def list_users():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return users


# ============================================================
# Group functions
# ============================================================

def create_group(owner_telegram_id, name, city="Hong Kong", description=""):
    owner = get_user(owner_telegram_id)
    if not owner:
        return None
    name = (name or "").strip()
    if not name:
        return None

    city = (city or "").strip() or "Hong Kong"
    description = (description or "").strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO groups (name, city, description, owner_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, city, description, owner["id"], now),
    )
    conn.commit()
    group_id = c.lastrowid
    conn.close()
    return group_id


def list_groups(owner_telegram_id):
    """Return all groups owned by a user, each with a member_count."""
    owner = get_user(owner_telegram_id)
    if not owner:
        return []

    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT g.*,
               (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) AS member_count
        FROM groups g
        WHERE g.owner_id = ?
        ORDER BY g.created_at DESC
        """,
        (owner["id"],),
    )
    groups = [dict(row) for row in c.fetchall()]
    conn.close()
    return groups


def get_group(group_id, owner_telegram_id=None):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT g.*,
               (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) AS member_count
        FROM groups g
        WHERE g.id = ?
        """,
        (group_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    group = dict(row)
    if owner_telegram_id:
        owner = get_user(owner_telegram_id)
        if not owner or group.get("owner_id") != owner["id"]:
            return None
    return group


def update_group(group_id, **kwargs):
    allowed = {"name", "city", "description"}
    updates = {k: (v or "").strip() if k != "city" else ((v or "").strip() or "Hong Kong")
               for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False

    conn = _get_conn()
    c = conn.cursor()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [group_id]
    c.execute(f"UPDATE groups SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True


def delete_group(group_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
    c.execute("DELETE FROM groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()
    return True


# ============================================================
# Group member functions
# ============================================================

def add_group_member(group_id, telegram_id, display_name=""):
    telegram_id = (telegram_id or "").strip()
    if not telegram_id:
        return False
    display_name = (display_name or "").strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO group_members (group_id, telegram_id, display_name, added_at) VALUES (?, ?, ?, ?)",
            (group_id, telegram_id, display_name, now),
        )
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False  # duplicate (group_id, telegram_id)
    conn.close()
    return ok


def remove_group_member(group_id, telegram_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "DELETE FROM group_members WHERE group_id = ? AND telegram_id = ?",
        (group_id, telegram_id),
    )
    conn.commit()
    conn.close()
    return True


def list_group_members(group_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM group_members WHERE group_id = ? ORDER BY added_at",
        (group_id,),
    )
    members = [dict(row) for row in c.fetchall()]
    conn.close()
    return members


def get_group_broadcast_targets(group_id):
    """Return ordered, de-duplicated list of Telegram IDs in a group."""
    members = list_group_members(group_id)
    seen = []
    for m in members:
        tid = (m.get("telegram_id") or "").strip()
        if tid and tid not in seen:
            seen.append(tid)
    return seen


# ============================================================
# Diagnostics & backup
# ============================================================

def get_db_status():
    """Return a snapshot of the database for the Account page.

    Includes absolute path, schema version, and row counts. Used to make the
    "your data really is persisted" guarantee visible in the UI.
    """
    conn = _get_conn()
    c = conn.cursor()
    c.execute("PRAGMA user_version")
    version = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM groups")
    groups_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM group_members")
    members_count = c.fetchone()[0]
    conn.close()
    return {
        "path": os.path.abspath(DB_PATH),
        "schema_version": version,
        "expected_version": SCHEMA_VERSION,
        "users_count": users_count,
        "groups_count": groups_count,
        "members_count": members_count,
    }


def export_user_data(telegram_id):
    """Export a user's full data (profile + owned groups + members) as a dict.

    Useful as a JSON backup the user can download from the Account page.
    """
    user = get_user(telegram_id)
    if not user:
        return None
    groups = []
    for g in list_groups(telegram_id):
        members = list_group_members(g["id"])
        groups.append({
            "name": g["name"],
            "city": g["city"],
            "description": g.get("description", ""),
            "created_at": g["created_at"],
            "members": [
                {"display_name": m.get("display_name", ""), "telegram_id": m["telegram_id"]}
                for m in members
            ],
        })
    return {
        "profile": {
            "telegram_id": user["telegram_id"],
            "nickname": user.get("nickname", ""),
            "favorite_city": user.get("favorite_city", "Hong Kong"),
            "created_at": user.get("created_at"),
            "last_login_at": user.get("last_login_at"),
        },
        "groups": groups,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# Initialize DB on module import
init_db()
