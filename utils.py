"""
Utility functions for database operations and SQL query generation
This module provides functionality for:
- Database connection management
- SQL query generation using OpenAI's GPT-4
- SQL query execution
"""

import os
import sqlite3
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI


# Load OpenAI API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API key not found in .env file")
client = OpenAI(api_key=api_key)


def get_db_connection() -> sqlite3.Connection:
    """
    Create and return database connection
    Returns:
        SQLite database connection object
    """
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_db_schema() -> str:
    """
    Get database schema dynamically
    Returns:
        String containing the database schema
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        schema = cursor.fetchall()
        return "\n".join([row[0] for row in schema if row[0]])


def generate_sql_query(natural_query: str) -> str:
    """
    Convert natural language query to SQL. Only generates SELECT queries.
    Args:
        natural_query: Natural language query string
    Returns:
        Generated SQL query string (SELECT only)
    Raises:
        ValueError: If the generated query is not a SELECT query
    """
    schema = get_db_schema()
    prompt = f"Database Schema:\n{schema}\n\nUser Query:\n{natural_query}"

    system_content = (
        "You are a SQL query converter that ONLY generates SELECT queries.\n"
        "Create queries according to this schema and use exact table/column names.\n"
        "Case sensitivity in requests doesn't matter.\n"
        "Please return only the SQL query, no additional explanations.\n"
        "Use UPPERCASE for all SQL keywords.\n"
        "Use proper indentation.\n"
        "IMPORTANT: You must ONLY generate SELECT queries. Any request for INSERT, "
        "UPDATE, DELETE, DROP or other modification operations should be rejected "
        "with the message 'Only SELECT queries are allowed for security reasons'.\n"
        "Examples of allowed queries:\n"
        "- SELECT * FROM table\n"
        "- SELECT column FROM table WHERE condition\n"
        "Examples of rejected queries:\n"
        "- INSERT INTO table\n"
        "- UPDATE table\n"
        "- DELETE FROM table\n"
        "- DROP TABLE"
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
    )

    generated_query = response.choices[0].message.content.strip()
    
    # Double check that the generated query is SELECT only
    if not generated_query.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for security reasons")

    return generated_query


def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """
    Execute SQL query and return results. Only allows SELECT queries.
    Args:
        query: SQL query string to execute (must be a SELECT query)
    Returns:
        List of dictionaries containing query results
    Raises:
        ValueError: If query is not a SELECT query
    """
    # Check if query is read-only (SELECT only)
    if not query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for security reasons")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        if not results:  # For empty results
            return []
        
        formatted_results = [{columns[i]: value for i, value in enumerate(row)} for row in results]
        
        return formatted_results
