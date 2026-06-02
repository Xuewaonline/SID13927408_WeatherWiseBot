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

    c.execute("""
        CREATE TABLE IF NOT EXISTS saved_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_telegram_id TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_telegram_id TEXT NOT NULL,
            preferred_city TEXT DEFAULT 'Hong Kong',
            created_at TEXT NOT NULL,
            FOREIGN KEY (owner_telegram_id) REFERENCES users(telegram_id),
            UNIQUE(owner_telegram_id, account_telegram_id)
        )
    """)

    conn.commit()
    conn.close()


# ==================== User Login / Register ====================

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


# ==================== Saved Accounts (常用账户) ====================

def add_saved_account(owner_telegram_id, account_name, account_telegram_id, preferred_city="Hong Kong"):
    """
    Add a saved account for the logged-in user.
    Returns (success: bool, message: str).
    """
    owner_telegram_id = owner_telegram_id.strip()
    account_telegram_id = account_telegram_id.strip()
    account_name = account_name.strip()

    if not account_name or not account_telegram_id:
        return False, "Account name and Telegram ID are required."

    conn = _get_conn()
    c = conn.cursor()

    # Check duplicate
    c.execute(
        "SELECT id FROM saved_accounts WHERE owner_telegram_id = ? AND account_telegram_id = ?",
        (owner_telegram_id, account_telegram_id),
    )
    if c.fetchone():
        conn.close()
        return False, f"Account '{account_telegram_id}' already exists."

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO saved_accounts (owner_telegram_id, account_name, account_telegram_id, preferred_city, created_at) VALUES (?, ?, ?, ?, ?)",
        (owner_telegram_id, account_name, account_telegram_id, preferred_city, now),
    )
    conn.commit()
    conn.close()
    return True, f"Account '{account_name}' saved."


def get_saved_accounts(owner_telegram_id):
    """Return all saved accounts for a user."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM saved_accounts WHERE owner_telegram_id = ? ORDER BY created_at",
        (owner_telegram_id.strip(),),
    )
    accounts = [dict(row) for row in c.fetchall()]
    conn.close()
    return accounts


def update_saved_account(account_id, **kwargs):
    """Update a saved account. Accepted fields: account_name, account_telegram_id, preferred_city."""
    allowed = {"account_name", "account_telegram_id", "preferred_city"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False

    conn = _get_conn()
    c = conn.cursor()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [account_id]
    c.execute(f"UPDATE saved_accounts SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True


def delete_saved_account(account_id):
    """Delete a saved account by its database ID."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM saved_accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()
    return True


# Initialize DB on module import
init_db()
