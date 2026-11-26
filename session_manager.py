import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from config import SESSIONS_DB_PATH, BASE_DIR

DB_PATH = SESSIONS_DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            thread_id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""")


def create_session(thread_id: str):
    with get_connection() as conn:
        conn.execute(
            """
        INSERT OR IGNORE INTO sessions (thread_id)
        VALUES (?)
        """,
            (thread_id,),
        )


def update_title(thread_id: str, title: str):
    with get_connection() as conn:
        conn.execute(
            """
        UPDATE sessions
        SET title = ?, updated_at = CURRENT_TIMESTAMP
        WHERE thread_id = ?;
        """,
            (title, thread_id),
        )


def get_sessions():
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT thread_id, title, created_at, updated_at
            FROM sessions
            ORDER BY updated_at DESC
        """)

        return cursor.fetchall()


def get_session(thread_id: str):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT thread_id, title, created_at, updated_at
            FROM sessions
            WHERE thread_id = ?
            """,
            (thread_id,),
        )

        return cursor.fetchone()


def delete_session(thread_id: str):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM sessions
            WHERE thread_id = ?;
            """,
            (thread_id,),
        )

        return cursor.rowcount > 0


def clear_title(thread_id: str):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET title = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE thread_id = ?
            """,
            (thread_id,),
        )


def touch_session(thread_id: str):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE thread_id = ?
            """,
            (thread_id,),
        )
