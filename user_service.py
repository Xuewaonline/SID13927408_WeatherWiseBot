"""
User Service Module
Manage user accounts and preferences with SQLite database.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def _get_conn():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they do not exist."""
    conn = _get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            nickname TEXT DEFAULT '',
            favorite_city TEXT DEFAULT 'Hong Kong',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def register_or_login(telegram_id):
    """Register a new user or return existing user by telegram ID."""
    telegram_id = telegram_id.strip()
    if not telegram_id:
        return None

    conn = _get_conn()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()

    if row:
        user = dict(row)
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO users (telegram_id, nickname, favorite_city, created_at) VALUES (?, ?, ?, ?)",
            (telegram_id, "", "Hong Kong", now),
        )
        conn.commit()
        c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = dict(c.fetchone())

    conn.close()
    return user


def get_user(telegram_id):
    """Get user profile by telegram ID."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id.strip(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(telegram_id, **kwargs):
    """Update user profile. Accepted fields: nickname, favorite_city."""
    telegram_id = telegram_id.strip()
    allowed = {"nickname", "favorite_city"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
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
    """Return all registered users."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return users


# Initialize DB on module import
init_db()
