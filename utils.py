"""
Utility functions for database operations and SQL query generation
This module provides functionality for:
- Database connection management
- SQL query generation using OpenAI's GPT-4
- SQL query execution
"""

import os
import sqlite3
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from openai import OpenAI


# Load OpenAI API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def get_db_connection() -> sqlite3.Connection:
    """Create and return database connection"""
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_db_schema() -> str:
    """Get database schema dynamically"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        schema = cursor.fetchall()
        return "\n".join([row[0] for row in schema if row[0]])


def generate_sql_query(natural_query: str) -> tuple[str, str]:
    """Convert natural language query to SQL with a natural language explanation."""
    schema = get_db_schema()
    prompt = f"Database Schema:\n{schema}\n\nUser Query:\n{natural_query}"

    system_content = (
        "You are a database expert. Answer user questions naturally and "
        "include an SQL query in your response. Write the SQL query between ```sql and ``` "
        "tags. Example format:\n\n"
        "I can show you the sales data using this query:\n"
        "```sql\n"
        "SELECT * FROM sales\n"
        "```\n"
        "This query will show you all sales records.\n\n"
        "IMPORTANT: Only SELECT queries are allowed for security reasons. "
        "INSERT, UPDATE, DELETE queries are not allowed."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
    )

    full_response = response.choices[0].message.content.strip()
    sql_start = full_response.find("```sql")
    sql_end = full_response.find("```", sql_start + 5)
    sql_query = full_response[sql_start + 6:sql_end].strip()

    return full_response, sql_query


def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """Execute SQL query and return results."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        if not results:
            return []
        
        return [{columns[i]: value for i, value in enumerate(row)} for row in results]


def process_natural_query(natural_query: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Process a natural language query and return both the explanation and results."""
    explanation, sql_query = generate_sql_query(natural_query)
    results = execute_sql_query(sql_query)
    return explanation, results
