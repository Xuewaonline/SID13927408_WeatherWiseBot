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
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
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
            "INSERT INTO users (telegram_id, nickname, favorite_city, created_at) "
            "VALUES (?, ?, ?, ?)",
            (telegram_id, nickname, favorite_city, now),
        )
        conn.commit()
        c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = dict(c.fetchone())
    except sqlite3.IntegrityError:
        user = None
    conn.close()
    return user


def login_user(telegram_id):
    """Login an existing user by Telegram ID. Returns None if not registered."""
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


# Initialize DB on module import
init_db()
