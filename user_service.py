"""
User Service Module
Manage user accounts and preferences with local JSON storage.
"""

import json
import os

USER_DATA_FILE = os.path.join(os.path.dirname(__file__), "user_data.json")


def _load_all_users():
    """Load all user data from JSON file."""
    if not os.path.exists(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_all_users(users):
    """Save all user data to JSON file."""
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def register_or_login(telegram_id):
    """
    Register a new user or return existing user by telegram ID.
    Returns user dict with profile info.
    """
    telegram_id = telegram_id.strip()
    if not telegram_id:
        return None

    users = _load_all_users()

    if telegram_id in users:
        return users[telegram_id]

    new_user = {
        "telegram_id": telegram_id,
        "nickname": "",
        "favorite_city": "Hong Kong",
        "created_at": ""
    }

    users[telegram_id] = new_user
    _save_all_users(users)
    return new_user


def get_user(telegram_id):
    """Get user profile by telegram ID. Returns None if not found."""
    users = _load_all_users()
    return users.get(telegram_id.strip())


def update_user(telegram_id, **kwargs):
    """
    Update user profile fields.
    Accepted fields: nickname, favorite_city
    """
    telegram_id = telegram_id.strip()
    users = _load_all_users()

    if telegram_id not in users:
        return False

    allowed = {"nickname", "favorite_city"}
    for key, value in kwargs.items():
        if key in allowed:
            users[telegram_id][key] = value

    _save_all_users(users)
    return True


def list_users():
    """Return list of all registered users (for admin purposes)."""
    users = _load_all_users()
    return list(users.values())
