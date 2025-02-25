"""
Query History Module

This module provides functionality for storing and retrieving query history in a SQLite database.
It manages session-based tracking of natural language queries, their SQL translations,
GPT explanations, and query results.

Functions:
    generate_session_id(): Generate unique session IDs
    save_query_history(): Save query history with results
    get_all_sessions(): Retrieve all sessions with their queries
    initialize_history_db(): Initialize the history database

Example:
    >>> session_id = generate_session_id()
    >>> save_query_history(
    ...     session_id=session_id,
    ...     natural_query="Show all products",
    ...     sql_query="SELECT * FROM Products",
    ...     gpt_explanation="Detailed analysis...",
    ...     query_result=[{"ProductID": "123"}],
    ...     title="Product List Query"
    ... )
    >>> sessions = get_all_sessions()
"""

import sqlite3
import uuid
import json
from typing import List, Dict, Any, Optional, Union

__all__ = ['save_query_history', 'generate_session_id', 'get_all_sessions']


def get_db_connection() -> sqlite3.Connection:
    """Create and return a connection to the query history database."""
    conn = sqlite3.connect("query_history.db")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_history_db() -> None:
    """Initialize the query history database schema."""
    with get_db_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            natural_query TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            gpt_explanation TEXT NOT NULL,
            query_result TEXT NOT NULL,
            title TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def save_query_history(
    session_id: str,
    natural_query: str,
    sql_query: str,
    gpt_explanation: str,
    query_result: List[Dict[str, Any]],
    title: Optional[str] = None
) -> None:
    """Save query details and results to history database."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO query_history (
                session_id, natural_query, sql_query,
                gpt_explanation, query_result, title
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, natural_query, sql_query, gpt_explanation,
             json.dumps(query_result), title)
        )
        conn.commit()


def parse_query_result(result_str: str) -> Union[Dict, List, str]:
    """Parse query result string into Python object."""
    if isinstance(result_str, (dict, list)):
        return result_str

    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        try:
            import ast
            return ast.literal_eval(result_str)
        except (ValueError, SyntaxError):
            return result_str


def get_all_sessions() -> List[Dict[str, Any]]:
    """Retrieve all query sessions with their queries."""
    with get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM query_history 
            ORDER BY session_id, timestamp DESC
        """)
        all_queries = cursor.fetchall()

        if not all_queries:
            return []

        sessions = {}
        for query in all_queries:
            query_dict = dict(query)
            session_id = query_dict['session_id']

            if session_id not in sessions:
                sessions[session_id] = {
                    'id': session_id,
                    'queries': []
                }

            query_dict['query_result'] = parse_query_result(query_dict['query_result'])
            sessions[session_id]['queries'].append(query_dict)

        return list(sessions.values())


# Initialize the history database when the module is imported
initialize_history_db() 
