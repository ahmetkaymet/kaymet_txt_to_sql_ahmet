"""
Utility functions for storing and retrieving query history
"""

import sqlite3
import uuid
import json
from typing import List, Dict, Any


__all__ = ['save_query_history', 'generate_session_id', 'get_session_history']


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the query history database."""
    conn = sqlite3.connect("query_history.db")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_history_db():
    """Initialize the query history database."""
    with get_db_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            natural_query TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            gpt_explanation TEXT NOT NULL,
            query_result TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def save_query_history(session_id: str, natural_query: str, sql_query: str, gpt_explanation: str, query_result: List[Dict[str, Any]]):
    """Save the query and its results to the history database."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO query_history (session_id, natural_query, sql_query, gpt_explanation, query_result)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, natural_query, sql_query, gpt_explanation, json.dumps(query_result))
        )
        conn.commit()


def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    """Retrieve the query history for a specific session."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM query_history WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        results = cursor.fetchall()
        return [dict(row) for row in results] if results else []


# Initialize the history database when the module is imported
initialize_history_db() 
