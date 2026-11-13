"""
Database layer (SQLite) - multi-user version.

Every transaction and budget belongs to a user.  After login, main_mdi.py
calls set_current_user(user_id) once; from then on every function below only
sees and changes that user's rows, so the screens need no changes.

Settings (theme, font size, language, currency) stay application-wide.

An existing finance.db from the single-user version is upgraded
automatically by initialize_db(): the old rows are kept, and the first
account that is created becomes their owner.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Store the database beside this Python file.
DB_PATH = Path(__file__).resolve().parent / "finance.db"

_current_user_id = None


# --------------------------------------------------------------------------- #
# Current user
# --------------------------------------------------------------------------- #
def set_current_user(user_id):
    """Set (or, with None, clear) the logged-in user."""
    global _current_user_id
    _current_user_id = user_id


def get_current_user_id():
    return _current_user_id


def _user_id():
    if _current_user_id is None:
        raise RuntimeError("No user is logged in.")
    return _current_user_id


# --------------------------------------------------------------------------- #
# Connections
# --------------------------------------------------------------------------- #
def connect_db():
    """Create and return a database connection."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_session():
    """Open a connection; commit on success, roll back on error, always close."""
    connection = connect_db()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        salt BLOB NOT NULL,
        password_hash BLOB NOT NULL,
        iterations INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL
            CHECK (type IN ('income', 'expense')),
        amount REAL NOT NULL CHECK (amount > 0),
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT DEFAULT '',
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        category TEXT NOT NULL,
        limit_amount REAL NOT NULL
            CHECK (limit_amount > 0),
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE (user_id, month, category)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
"""


def _columns(connection, table):
    return [row["name"] for row in connection.execute(f"PRAGMA table_info({table})")]


def _migrate_to_multi_user(connection):
    """Upgrade a single-user database (no user_id columns) in place."""
    if "user_id" not in _columns(connection, "transactions"):
        connection.execute("""
            ALTER TABLE transactions
            ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
        """)

    if "user_id" not in _columns(connection, "budgets"):
        # The UNIQUE rule changes from (month, category) to
        # (user_id, month, category), which SQLite can only do by rebuilding
        # the table.  Row ids are preserved.
        connection.executescript("""
            BEGIN;
            CREATE TABLE budgets_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                limit_amount REAL NOT NULL
                    CHECK (limit_amount > 0),
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, month, category)
            );
            INSERT INTO budgets_new (id, month, category, limit_amount)
                SELECT id, month, category, limit_amount FROM budgets;
            DROP TABLE budgets;
            ALTER TABLE budgets_new RENAME TO budgets;
            COMMIT;
        """)


def initialize_db():
    """Create all required tables if they do not exist, and upgrade old ones."""
    with database_session() as connection:
        connection.executescript(SCHEMA)
        _migrate_to_multi_user(connection)


def claim_unassigned_data(user_id):
    """
    Give rows that have no owner (created before accounts existed) to this user.
    Returns (transactions_claimed, budgets_claimed).
    """
    with database_session() as connection:
        transactions = connection.execute(
            "UPDATE transactions SET user_id = ? WHERE user_id IS NULL",
            (user_id,)
        ).rowcount

        budgets = connection.execute(
            "UPDATE budgets SET user_id = ? WHERE user_id IS NULL",
            (user_id,)
        ).rowcount

    return transactions, budgets


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #
def add_transaction(data):
    """Insert a transaction and return its new ID."""
    user_id = _user_id()

    with database_session() as connection:
        cursor = connection.execute("""
            INSERT INTO transactions
                (type, amount, category, date, description, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["type"],
            round(float(data["amount"]), 2),
            data["category"].strip(),
            data["date"],
            data.get("description", "").strip(),
            user_id
        ))

        return cursor.lastrowid


def get_transactions(filters=None):
    """
    Return the current user's transactions as a list of dictionaries.

    Optional filters:
        type, category, start_date, end_date, search
    """
    filters = filters or {}

    query = "SELECT * FROM transactions WHERE user_id = ?"
    parameters = [_user_id()]

    if filters.get("type"):
        query += " AND type = ?"
        parameters.append(filters["type"])

    if filters.get("category"):
        query += " AND category = ?"
        parameters.append(filters["category"])

    if filters.get("start_date"):
        query += " AND date >= ?"
        parameters.append(filters["start_date"])

    if filters.get("end_date"):
        query += " AND date <= ?"
        parameters.append(filters["end_date"])

    if filters.get("search"):
        query += " AND description LIKE ?"
        parameters.append("%" + filters["search"] + "%")

    query += " ORDER BY date DESC, id DESC"

    with database_session() as connection:
        rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]


def get_transaction_by_id(transaction_id):
    """Return one of the current user's transactions, or None if not found."""
    with database_session() as connection:
        row = connection.execute("""
            SELECT * FROM transactions WHERE id = ? AND user_id = ?
        """, (transaction_id, _user_id())).fetchone()

        return dict(row) if row else None


def update_transaction(transaction_id, data):
    """Update a transaction. Return True if a row was updated."""
    with database_session() as connection:
        cursor = connection.execute("""
            UPDATE transactions
            SET type = ?, amount = ?, category = ?,
                date = ?, description = ?
            WHERE id = ? AND user_id = ?
        """, (
            data["type"],
            round(float(data["amount"]), 2),
            data["category"].strip(),
            data["date"],
            data.get("description", "").strip(),
            transaction_id,
            _user_id()
        ))

        return cursor.rowcount > 0


def delete_transaction(transaction_id):
    """Delete a transaction. Return True if deleted."""
    with database_session() as connection:
        cursor = connection.execute("""
            DELETE FROM transactions WHERE id = ? AND user_id = ?
        """, (transaction_id, _user_id()))

        return cursor.rowcount > 0


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #
def add_budget(data):
    """Insert a budget and return its new ID."""
    user_id = _user_id()

    with database_session() as connection:
        cursor = connection.execute("""
            INSERT INTO budgets (month, category, limit_amount, user_id)
            VALUES (?, ?, ?, ?)
        """, (
            data["month"],
            data["category"].strip(),
            round(float(data["limit_amount"]), 2),
            user_id
        ))

        return cursor.lastrowid


def get_budgets(month):
    """Return all of the current user's budgets for a month."""
    with database_session() as connection:
        rows = connection.execute("""
            SELECT * FROM budgets
            WHERE month = ? AND user_id = ?
            ORDER BY category
        """, (month, _user_id())).fetchall()

        return [dict(row) for row in rows]


def update_budget(budget_id, data):
    """Update a budget. Return True if a row was updated."""
    with database_session() as connection:
        cursor = connection.execute("""
            UPDATE budgets
            SET month = ?, category = ?, limit_amount = ?
            WHERE id = ? AND user_id = ?
        """, (
            data["month"],
            data["category"].strip(),
            round(float(data["limit_amount"]), 2),
            budget_id,
            _user_id()
        ))

        return cursor.rowcount > 0


def delete_budget(budget_id):
    """Delete a budget. Return True if deleted."""
    with database_session() as connection:
        cursor = connection.execute("""
            DELETE FROM budgets WHERE id = ? AND user_id = ?
        """, (budget_id, _user_id()))

        return cursor.rowcount > 0


# --------------------------------------------------------------------------- #
# Settings (application-wide, not per user)
# --------------------------------------------------------------------------- #
def get_setting(key):
    """Return a setting value, or None if not saved."""
    with database_session() as connection:
        row = connection.execute("""
            SELECT value FROM settings WHERE key = ?
        """, (key,)).fetchone()

        return row["value"] if row else None


def save_setting(key, value):
    """Insert a setting or replace its existing value."""
    with database_session() as connection:
        connection.execute("""
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))
