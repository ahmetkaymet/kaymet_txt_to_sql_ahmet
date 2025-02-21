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


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a SQLite database connection with dictionary row factory.

    The connection is configured to use sqlite3.Row as the row_factory, which allows
    accessing columns both by index and by name.

    Returns:
        sqlite3.Connection: A connection object to the SQLite database with row_factory
            set to sqlite3.Row for dictionary-like access to rows.
    """
    
    conn = sqlite3.connect("data.db")
 
    conn.row_factory = sqlite3.Row
    return conn


def get_db_schema() -> str:
    """Retrieves the complete schema of all tables in the database.

    This function connects to the database, queries the sqlite_master table
    to get all CREATE TABLE statements, and joins them into a single string.
    The connection and cursor are automatically closed when the function returns
    due to the context manager.

    Returns:
        str: A string containing the SQL CREATE statements for all tables
            in the database, separated by newlines.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()  
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        schema = cursor.fetchall()
        return "\n".join([row[0] for row in schema if row[0]])



def generate_sql_query(natural_query: str) -> Tuple[str, str]:
    """Generates an SQL query from a natural language query using OpenAI's GPT-4o.

    This function takes a natural language query, sends it to OpenAI's GPT-4o model
    along with the database schema, and extracts both the explanation and the SQL
    query from the model's response. The response is parsed to extract the SQL query
    from between markdown code blocks.

    Args:
        natural_query (str): The natural language query to convert to SQL.

    Returns:
        Tuple[str, str]: A tuple containing:
            - full_response (str): The complete response from GPT-4o including the
                natural language explanation and the SQL query with markdown formatting
            - sql_query (str): The extracted SQL query without the markdown formatting
                (```sql```) tags, ready for execution
    """
    
    schema = get_db_schema()
    prompt = f"Database Schema:\n{schema}\n\nUser Query:\n{natural_query}"

    system_content = (
        "You are a database expert. Answer user questions naturally. "
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
        model="gpt-4o",
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
    """Executes an SQL query and returns the results as a list of dictionaries.

    Args:
        query (str): The SQL query to execute.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries where each dictionary represents
            a row with column names as keys and cell values as values. Returns an
            empty list if no results are found.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        if not results:
            return []
        
        return [{columns[i]: value for i, value in enumerate(row)} for row in results]


def process_natural_query(natural_query: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Processes a natural language query by converting it to SQL and executing it.

    Args:
        natural_query (str): The natural language query to process.

    Returns:
        Tuple[str, List[Dict[str, Any]]]: A tuple containing:
            - explanation (str): The AI-generated explanation of the query and results
            - results (List[Dict[str, Any]]): The query results as a list of dictionaries
    """
    explanation, sql_query = generate_sql_query(natural_query)
    results = execute_sql_query(sql_query)
    return explanation, results
