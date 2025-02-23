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
        "You are a database expert. Follow these steps IN ORDER:\n\n"
        "1. ANALYZE PHASE - MANDATORY:\n"
        "   - First, carefully analyze the complete database schema\n"
        "   - Study ALL column descriptions from table_column_descriptions\n"
        "   - Pay special attention to:\n"
        "     * Data formats (e.g., date formats, state codes)\n"
        "     * Case sensitivity requirements\n"
        "     * Primary and Foreign key relationships\n"
        "     * Any specific constraints or formats mentioned\n\n"
        "2. PLANNING PHASE - MANDATORY:\n"
        "   - Identify which tables and columns are needed\n"
        "   - Consider data format requirements (e.g., using 'NY' instead of 'New York')\n"
        "   - Plan necessary joins based on PK/FK relationships\n"
        "   - Consider case sensitivity where required\n\n"
        "3. QUERY GENERATION PHASE:\n"
        "   - Only after completing analysis and planning, write the SQL query\n"
        "   - Must follow all format requirements found in analysis\n"
        "   - Write the query between ```sql and ``` tags\n\n"
        "4. EXPLANATION PHASE:\n"
        "   - Explain your query in natural language\n"
        "   - Mention any important data format considerations\n\n"
        "Example format:\n"
        "Based on the schema analysis, I notice that State uses 2-letter codes and Category1 is case-sensitive.\n"
        "Here's the query:\n"
        "```sql\n"
        "SELECT * FROM Stores WHERE State = 'NY'\n"
        "```\n"
        "This will show all stores in New York (using NY state code).\n\n"
        "IMPORTANT RULES:\n"
        "- Only SELECT queries are allowed (no INSERT, UPDATE, DELETE)\n"
        "- You MUST respect all data formats and constraints from schema\n"
        "- You MUST use table_column_descriptions for understanding columns\n"
        "- You MUST mention in your explanation any data format considerations"
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