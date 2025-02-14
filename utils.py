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

# Custom error classes
class SQLGenerationError(Exception):
    """Custom error for SQL generation failures"""

class SQLExecutionError(Exception):
    """Custom error for SQL execution failures"""

def get_db_connection() -> sqlite3.Connection:
    """
    Create and return database connection
    Returns:
        SQLite database connection object
    """
    try:
        conn = sqlite3.connect('data.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise e

def get_db_schema() -> str:
    """
    Get database schema dynamically
    Returns:
        String containing the database schema
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
            schema = cursor.fetchall()
            return "\n".join([row[0] for row in schema if row[0]])
    except Exception as e:
        raise e

def generate_sql_query(natural_query: str) -> str:
    """
    Convert natural language query to SQL
    Args:
        natural_query: Natural language query string
    Returns:
        Generated SQL query string
    Raises:
        SQLGenerationError: If query generation fails
    """
    try:
        schema = get_db_schema()
        prompt = f"""
        Database Schema:
        {schema}

        User Query:
        {natural_query}
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """
                You are a SQL query converter. The database has the following tables:
                    
                    1. Products:
                        - ProductID(PK)
                        - Name
                        - Category1(kids,men,women)
                        - Category2
                    
                    2. Transactions:
                        - StoreID(PK)
                        - ProductID(FK)
                        - Quantity
                        - PricePerQuantity
                        - Timestamp(Format: YYYY-MM-DD-HH-MM-SS)
                    
                    3. Stores:
                        - StoreID(PK, Store IDs always start with 'STO'. If user provides only numbers, prepend 'STO')
                        - State(Uses state abbreviations. If full state name is provided, use its abbreviation)
                        - ZipCode
                    
                Create queries according to this schema and use exact table/column names.
                Case sensitivity in requests doesn't matter.
                Please return only the SQL query, no additional explanations.
                Use UPPERCASE for all SQL keywords.
                Use proper indentation.
                For potentially dangerous operations. (operations such as deleting the table,changing the data,changing the schema ) Ask the user if he is sure, if so, use the same command. Accept when you say "I grant administrative permission"
                """},
                {"role": "user", "content": prompt}
            ]
        )

        generated_query = response.choices[0].message.content.strip()
        return generated_query

    except Exception as e:
        raise SQLGenerationError(f"Error generating SQL query: {str(e)}") from e

def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """
    Execute SQL query and return results
    Args:
        query: SQL query string to execute
    Returns:
        List of dictionaries containing query results
    Raises:
        SQLExecutionError: If query execution fails
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            if cursor.description is None:  # For non-SELECT queries
                conn.commit()
                return []
                
            columns = [description[0] for description in cursor.description]
            results = cursor.fetchall()
            
            if not results:  # For empty results
                return []
                
            formatted_results = [
                {columns[i]: value for i, value in enumerate(row)}
                for row in results
            ]
            
            return formatted_results

    except Exception as e:
        raise SQLExecutionError(f"Error executing SQL query: {str(e)}") from e

