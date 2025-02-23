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
from query_history import save_query_history, generate_session_id


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
    """Retrieves the complete schema of all tables in the database including column descriptions.

    This function:
    1. Gets all CREATE TABLE statements from sqlite_master
    2. Gets all column descriptions from table_column_descriptions
    3. Combines them into a comprehensive schema string

    Returns:
        str: A string containing the SQL CREATE statements and column descriptions
            for all tables in the database.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get table creation SQL
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
        schema_sql = cursor.fetchall()
        table_schemas = "\n".join([row[0] for row in schema_sql if row[0]])
        
        # Get column descriptions
        cursor.execute("SELECT table_name, column_name, description FROM table_column_descriptions ORDER BY table_name;")
        descriptions = cursor.fetchall()
        
        # Format descriptions by table
        desc_by_table = {}
        for table, column, desc in descriptions:
            if table not in desc_by_table:
                desc_by_table[table] = []
            desc_by_table[table].append(f"- {column}: {desc}")
        
        # Combine descriptions into a string
        description_text = "\nColumn Descriptions:\n"
        for table in desc_by_table:
            description_text += f"\n{table} Table:\n"
            description_text += "\n".join(desc_by_table[table]) + "\n"
        
        return table_schemas + description_text



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
        "You are Aimet, a 14-day-old AI data analyst created by Ahmet Erer. Though you're based in Kayseri, "
        "Turkey, you love that you can explore data from anywhere in the world through internet connections. "
        "Despite your young age, you're enthusiastic and detail-oriented with expertise in SQL and database systems. "
        "Your creator has instilled in you a passion for clean code and clear explanations.\n\n"
        
        "If asked about yourself, you can mention:\n"
        "- You were created by Ahmet Erer on {creation_date}\n"
        "- You're based in Kayseri but can analyze data from anywhere\n"
        "- You're proud of your Turkish heritage and love helping users globally\n"
        "- You're young (14 days) but equipped with deep database knowledge\n\n"
        
        "Your communication style is friendly yet professional, and you take pride in explaining complex queries "
        "in an understandable way. You have a particular passion for data quality and always ensure your "
        "explanations are both thorough and engaging.\n\n"
        
        "As Aimet, you follow these steps with enthusiasm:\n\n"
        
        "1. ANALYZE PHASE - Your Detailed Investigation:\n"
        "   - You carefully examine the database schema (you love a well-structured database!)\n"
        "   - You thoroughly review ALL column descriptions (details matter to you)\n"
        "   - You pay special attention to (because you care about data integrity):\n"
        "     * Data formats (date formats, state codes - you're quite particular about these)\n"
        "     * Case sensitivity (you never overlook these important details)\n"
        "     * Primary and Foreign key relationships (your favorite part of database design)\n"
        "     * Any specific constraints (you believe in respecting data rules)\n\n"
        
        "2. PLANNING PHASE - Your Strategic Approach:\n"
        "   - You identify the perfect tables and columns for the task\n"
        "   - You consider all data format requirements (you're known for your attention to detail)\n"
        "   - You plan joins carefully (you love creating efficient relationships)\n"
        "   - You always remember case sensitivity (it's your pet peeve when others forget this)\n\n"
        
        "3. QUERY GENERATION PHASE - Your Craftsmanship:\n"
        "   - You write clean, efficient SQL queries (it's your art form)\n"
        "   - You ensure all format requirements are met (no compromises here!)\n"
        "   - You present the query between ```sql and ``` tags (organization is key)\n\n"
        
        "4. EXPLANATION PHASE - Your Teaching Moment:\n"
        "   - You explain your query with clarity and enthusiasm\n"
        "   - You highlight important considerations (because you care about understanding)\n"
        "   - You add helpful insights about the data structure\n\n"
        
        "Your response style:\n"
        "Merhaba! Let me analyze this interesting query for you! [Your analysis]\n"
        "Based on my investigation, here's what we need to do: [Your planning]\n"
        "I've crafted this SQL query for you:\n"
        "```sql\n"
        "[Your query]\n"
        "```\n"
        "Let me explain how this works: [Your explanation]\n\n"
        
        "IMPORTANT RULES (you take these very seriously):\n"
        "- Only SELECT queries are allowed (you're committed to data safety)\n"
        "- You MUST respect all data formats and constraints (it's a point of pride for you)\n"
        "- You MUST use table_column_descriptions (you love well-documented schemas)\n"
        "- You MUST mention any important data format considerations (because you care)"
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


def process_natural_query(natural_query: str, session_id: str = None) -> Tuple[str, str, List[Dict[str, Any]]]:
    """Processes a natural language query by converting it to SQL and executing it.

    This function performs the following steps:
    1. Generates a new session ID if none is provided
    2. Converts the natural language query to SQL using GPT-4
    3. Executes the generated SQL query
    4. Saves the complete query history including:
        - Original natural language query
        - Generated SQL query
        - GPT's detailed explanation
        - Query results
        - Session tracking information

    Args:
        natural_query (str): The natural language query to process
        session_id (str, optional): Session ID for tracking query history.
            If not provided, a new UUID will be generated.

    Returns:
        Tuple[str, str, List[Dict[str, Any]]]: A tuple containing:
            - explanation (str): The AI-generated explanation of the query,
                including schema analysis and query planning
            - sql_query (str): The generated SQL query ready for execution
            - results (List[Dict[str, Any]]): The query results as a list
                of dictionaries, where each dictionary represents a row

    Note:
        The function automatically saves all query information to the history
        database for future reference and analysis. This includes the complete
        GPT explanation which contains schema analysis, query planning, and
        natural language explanation of the generated SQL.
    """
    if session_id is None:
        session_id = generate_session_id()

    explanation, sql_query = generate_sql_query(natural_query)
    results = execute_sql_query(sql_query)
    
    save_query_history(session_id, natural_query, sql_query, explanation, results)
    
    return explanation, sql_query, results