"""
Query History Module

This module provides functionality for storing and retrieving query history in a SQLite database.
It manages session-based tracking of natural language queries, their SQL translations,
GPT explanations, and query results.

The module includes functions for:
    - Generating unique session IDs
    - Saving query history with results
    - Retrieving session-specific history
    - Initializing the history database

Example:
    >>> session_id = generate_session_id()
    >>> save_query_history(
    ...     session_id=session_id,
    ...     natural_query="Show all products",
    ...     sql_query="SELECT * FROM Products",
    ...     gpt_explanation="Detailed analysis...",
    ...     query_result=[{"ProductID": "123"}]
    ... )
    >>> history = get_session_history(session_id)
"""

import sqlite3
import uuid
import json
from typing import List, Dict, Any


__all__ = ['save_query_history', 'generate_session_id', 'get_session_history']


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the query history database.
    
    The connection is configured to use sqlite3.Row as the row_factory,
    which allows accessing columns both by index and by name.
    
    Returns:
        sqlite3.Connection: A connection object to the query history database
            with row_factory set to sqlite3.Row.
    """
    conn = sqlite3.connect("query_history.db")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_history_db():
    """Initialize the query history database schema.
    
    Creates the query_history table if it doesn't exist with the following columns:
        - id: INTEGER PRIMARY KEY AUTOINCREMENT
        - session_id: TEXT NOT NULL
        - natural_query: TEXT NOT NULL
        - sql_query: TEXT NOT NULL
        - gpt_explanation: TEXT NOT NULL
        - query_result: TEXT NOT NULL
        - timestamp: DATETIME DEFAULT CURRENT_TIMESTAMP
    """
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
    """Generate a unique session ID using UUID4.
    
    Returns:
        str: A unique UUID4 string to be used as session identifier.
    """
    return str(uuid.uuid4())


def save_query_history(session_id: str, natural_query: str, sql_query: str, 
                      gpt_explanation: str, query_result: List[Dict[str, Any]]):
    """Save query details and results to the history database.
    
    Args:
        session_id (str): Unique identifier for the query session.
        natural_query (str): The original natural language query from the user.
        sql_query (str): The generated SQL query.
        gpt_explanation (str): Detailed explanation from GPT about query analysis and generation.
        query_result (List[Dict[str, Any]]): The results returned by executing the SQL query.
            Will be stored as a JSON string in the database.
    """
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
    """Retrieve the query history for a specific session.
    
    Args:
        session_id (str): The session ID to retrieve history for.
    
    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the query history
            for the specified session, ordered by timestamp. Each dictionary contains:
            - id: The record ID
            - session_id: The session identifier
            - natural_query: The original query
            - sql_query: The generated SQL
            - gpt_explanation: The detailed analysis
            - query_result: The query results (as JSON string)
            - timestamp: When the query was executed
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM query_history WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        results = cursor.fetchall()
        return [dict(row) for row in results] if results else []


# Initialize the history database when the module is imported
initialize_history_db() 
