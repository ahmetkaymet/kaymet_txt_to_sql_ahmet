"""
Simple Query History Module
This module provides basic functionality for storing and retrieving query history using SQLite.
"""

import sqlite3
import json
import os
import uuid
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "query_history.db")

def generate_session_id() -> str:
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_history_db():
    """Create the query history table if it doesn't exist"""
    with get_db_connection() as conn:
        # Create the table if it doesn't exist
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

def save_query_history(session_id: str, natural_query: str, sql_query: str, 
                      explanation: str, query_result: List[Dict[str, Any]], 
                      title: str = None) -> None:
    """Save a query to history"""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO query_history (
                session_id, natural_query, sql_query,
                gpt_explanation, query_result, title
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, natural_query, sql_query, explanation,
             json.dumps(query_result), title)
        )
        conn.commit()

def get_all_sessions() -> List[Dict[str, Any]]:
    """Get all query sessions, ordered by timestamp"""
    with get_db_connection() as conn:
        # Get all queries, ordered by timestamp descending
        cursor = conn.execute("""
            SELECT 
                id,
                session_id,
                natural_query,
                sql_query,
                gpt_explanation as explanation,
                query_result,
                title,
                timestamp
            FROM query_history 
            ORDER BY timestamp DESC
        """)
        queries = cursor.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for query in queries:
            query_dict = dict(query)
            # Parse the JSON string back to a Python object
            query_dict['query_result'] = json.loads(query_dict['query_result'])
            result.append(query_dict)
            
        # Group by session_id
        sessions = {}
        for query in result:
            session_id = query['session_id']
            if session_id not in sessions:
                sessions[session_id] = {
                    'id': session_id,
                    'queries': []
                }
            sessions[session_id]['queries'].append(query)
            
        return list(sessions.values())

# Initialize database when module is imported
initialize_history_db() 
