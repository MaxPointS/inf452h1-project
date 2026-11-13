"""
User accounts for the Personal Finance Management System.

Accounts live in the same finance.db as the rest of the data (users table,
created by database.initialize_db()).  Passwords are never stored: each
account keeps a random salt and a PBKDF2-HMAC-SHA256 hash.

    has_users()                      -> bool
    register(username, password)     -> (user, message)   user is None on failure
    authenticate(username, password) -> user, or None if wrong

A "user" is a dict:  {"id": 1, "username": "Alice"}

The first account that is ever created becomes the owner of any transactions
and budgets that already existed in an old single-user finance.db.
"""

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime

import database

ITERATIONS = 600_000
MIN_USERNAME = 3
MAX_USERNAME = 30
MIN_PASSWORD = 6


def _hash(password, salt, iterations):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )


def has_users():
    with database.database_session() as connection:
        return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0


def register(username, password):
    """Create an account. Returns (user_dict, message); user is None on failure."""
    username = (username or "").strip()

    if not MIN_USERNAME <= len(username) <= MAX_USERNAME:
        return None, (f"Username must be {MIN_USERNAME} to "
                      f"{MAX_USERNAME} characters.")

    if len(password or "") < MIN_PASSWORD:
        return None, f"Password must be at least {MIN_PASSWORD} characters."

    first_account = not has_users()

    salt = os.urandom(16)
    password_hash = _hash(password, salt, ITERATIONS)

    try:
        with database.database_session() as connection:
            cursor = connection.execute(
                "INSERT INTO users (username, salt, password_hash, "
                "iterations, created_at) VALUES (?,?,?,?,?)",
                (username, salt, password_hash, ITERATIONS,
                 datetime.now().isoformat(timespec="seconds")),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return None, "That username is already taken."

    if first_account:
        # Data from the old single-user version now belongs to this account.
        database.claim_unassigned_data(user_id)

    return {"id": user_id, "username": username}, "Account created."


def authenticate(username, password):
    """Return the user dict if the credentials are correct, else None."""
    username = (username or "").strip()
    password = password or ""

    with database.database_session() as connection:
        row = connection.execute(
            "SELECT id, username, salt, password_hash, iterations "
            "FROM users WHERE username = ?", (username,)
        ).fetchone()

    if row is None:
        # Hash anyway so an unknown username takes as long as a wrong password.
        _hash(password, b"\x00" * 16, ITERATIONS)
        return None

    candidate = _hash(password, row["salt"], row["iterations"])

    if hmac.compare_digest(candidate, row["password_hash"]):
        return {"id": row["id"], "username": row["username"]}
    return None
