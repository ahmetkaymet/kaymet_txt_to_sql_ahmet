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

#connection to database using sqlite library it converts the database to a row factory (dictionary format)
def get_db_connection() -> sqlite3.Connection:
    """Create and return database connection"""
    #it connects to the database
    conn = sqlite3.connect("data.db")
    #it converts the database to a row factory (dictionary format)  
    conn.row_factory = sqlite3.Row
    return conn

#get the schema of the database for instruction to the model
def get_db_schema() -> str:
    """Get database schema dynamically"""
    #it gets the schema from get_db_connection function
    with get_db_connection() as conn:
        cursor = conn.cursor()
        #it executes the query to get the schema    
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        #it fetches the schema
        schema = cursor.fetchall()
        #it returns the schema as a string.
        ##Also cursor() method close automatically when function return
        return "\n".join([row[0] for row in schema if row[0]])


#generate the sql query from the natural language query thanks to openai model
def generate_sql_query(natural_query: str) -> tuple[str, str]:
    
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
    #search for the sql query and the explanation in the response and defines them as sql_query and full_response 
    full_response = response.choices[0].message.content.strip()
    sql_start = full_response.find("```sql")
    sql_end = full_response.find("```", sql_start + 5)
    sql_query = full_response[sql_start + 6:sql_end].strip()

    #it returns the response and the sql query
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
