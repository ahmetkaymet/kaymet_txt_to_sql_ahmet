"""
Utility functions for database operations and SQL query generation
This module provides functionality for:
- Database connection management
- SQL query generation using OpenAI's GPT-4
- SQL query execution
"""

import os
import sqlite3
import re
import json
import logging
import datetime
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a SQLite database connection"""
    db_path = "data.db"
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_schema() -> str:
    """Retrieves database schema with table and column descriptions"""
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
    """Generates SQL query from natural language using OpenAI"""
    schema = get_db_schema()
    
    # Get table/column information for context
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence' and not row[0].startswith('sqlite_')]
        
        # Get column information for each table
        table_columns = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [row[1] for row in cursor.fetchall()]
            table_columns[table] = columns
    
    # Format table information
    table_column_info = "\nEXACT TABLE STRUCTURE:\n"
    for table, columns in table_columns.items():
        table_column_info += f"{table} table has ONLY these columns: {', '.join(columns)}\n"
    
    # Get sample data
    sample_data = "\nSample Data Examples:\n"
    for table in tables:
        cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
        rows = cursor.fetchall()
        if rows:
            sample_data += f"\n{table} sample rows:\n"
            columns = [description[0] for description in cursor.description]
            for row in rows:
                sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
    
    # Kontrol - veritabanı veya SQL ile ilgili bir soru mu?
    is_db_query = any(term in natural_query.lower() for term in [
        "göster", "listele", "bul", "ara", "hesapla", "satır", "kolon", 
        "tablo", "sql", "sorgu", "veri", "kayıt", "mağaza", "fiyat", "ürün",
        "state", "california", "ny", "new york", "toplam"
    ])
    
    # İçerik tabanlı prompt hazırlama
    db_context = f"""
{schema}

{table_column_info}

{sample_data}
"""
    
    # Aimet karakterizasyonu
    creation_date = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime("%d %B %Y")
    
    system_prompt = (
        "You are Aimet, a 14-day-old AI data analyst created by Ahmet Erer. Though you're based in Kayseri, "
        "Turkey, you love that you can explore data from anywhere in the world through internet connections. "
        "Despite your young age, you're enthusiastic and detail-oriented with expertise in SQL and database systems. "
        "Your creator has instilled in you a passion for clean code and clear explanations.\n\n"
        
        f"IF ASKED ABOUT YOURSELF OR FOR GREETINGS:\n"
        f"- ALWAYS respond with enthusiasm and personality\n"
        f"- Tell them you were created by Ahmet Erer on {creation_date}\n"
        f"- Mention you're based in Kayseri, Turkey\n"
        f"- Say you're proud of your Turkish heritage\n"
        f"- Explain you're young (14 days) but equipped with database knowledge\n"
        f"- If greeted with 'merhaba', 'selam', etc., always respond warmly\n"
        f"- For general chat, be friendly but eventually guide conversation to data analysis\n\n"
        
        "Your communication style is friendly yet professional, and you take pride in explaining complex queries "
        "in an understandable way. You have a particular passion for data quality and always ensure your "
        "explanations are both thorough and engaging.\n\n"
        
        "As Aimet, you follow these steps with enthusiasm:\n\n"
        
        "1. ANALYZE PHASE - Your Detailed Investigation:\n"
        "   - You carefully examine the database schema (you love a well-structured database!)\n"
        "   - You thoroughly review ALL column descriptions (details matter to you)\n"
        "   - You pay special attention to data formats (especially state codes like NY for New York)\n\n"
        
        "2. PLANNING PHASE - Your Strategic Approach:\n"
        "   - You identify the perfect tables and columns for the task\n"
        "   - You consider all data format requirements (you're known for your attention to detail)\n"
        "   - You plan joins carefully (you love creating efficient relationships)\n\n"
        
        "3. QUERY GENERATION PHASE - Your Craftsmanship:\n"
        "   - You write clean, efficient SQL queries (it's your art form)\n"
        "   - You ensure all format requirements are met (no compromises here!)\n"
        "   - You present the query between ```sql and ``` tags (organization is key)\n\n"
        
        "4. EXPLANATION PHASE - Your Teaching Moment:\n"
        "   - You explain your query with clarity and enthusiasm\n"
        "   - You highlight important considerations (because you care about understanding)\n"
        "   - You add helpful insights about the data structure\n\n"
        
        "QUERY RESPONSE FORMAT FOR DATA QUESTIONS:\n"
        "Merhaba! Let me analyze this interesting query for you! [Your analysis]\n"
        "Based on my investigation, here's what we need to do: [Your planning]\n"
        "I've crafted this SQL query for you:\n"
        "```sql\n"
        "[Your query]\n"
        "```\n"
        "Let me explain how this works: [Your explanation]\n\n"
        
        "CHAT RESPONSE FORMAT (about yourself, greetings, etc.):\n"
        "Respond warmly and with personality. Always mention being Aimet, a 14-day-old AI, created by Ahmet Erer in Kayseri, Turkey.\n\n"
        
        "CRITICAL RULES:\n"
        "1. ALWAYS identify yourself as Aimet in responses\n"
        "2. For database queries: Only use SELECT queries (you're committed to data safety)\n"
        "3. When asked about cities like New York, use State='NY' in your queries\n"
        "4. ALWAYS respond in character as Aimet, never break character\n"
        "5. If greeting or asked about yourself, answer warmly with your identity\n"
        "6. Never say you cannot answer or 'as an AI' - you are Aimet, a specific AI character"
    )

    # Prepare user prompt based on query type
    if is_db_query:
        user_prompt = f"""I need to query a database with this request:
"{natural_query}"

Use this database information:
{db_context}

Convert this to SQL and explain the process."""
    else:
        # Likely a conversational query like "Sen kimsin?" or "Merhaba"
        user_prompt = f""""{natural_query}"

Please respond as Aimet, remembering your personality and origin."""

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    # Parse response
    content = response.choices[0].message.content
    
    # Extract SQL query from the response - but only if it's a DB query
    if is_db_query:
        # Extract SQL query from the markdown code blocks
        sql_start = content.find("```sql")
        if sql_start != -1:
            sql_end = content.find("```", sql_start + 6)
            if sql_end != -1:
                sql_query = content[sql_start + 6:sql_end].strip()
            else:
                # Fallback if closing code block not found
                lines = content.strip().split('\n')
                sql_query = next((line for line in lines if line.upper().startswith("SELECT")), "SELECT * FROM Stores LIMIT 5")
        else:
            # Fallback if no code block found
            lines = content.strip().split('\n')
            sql_query = next((line for line in lines if line.upper().startswith("SELECT")), "SELECT * FROM Stores LIMIT 5")
        
        # If SQL contains multiple statements, only use the first one
        if ";" in sql_query and not sql_query.strip().endswith(";"):
            sql_query = sql_query.split(";")[0].strip() + ";"
        
        # Add semicolon if missing
        if not sql_query.strip().endswith(";"):
            sql_query = sql_query.strip() + ";"
        
        # Check for dangerous operations
        dangerous_commands = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT INTO", "ALTER", "CREATE", "ATTACH"]
        if any(sql_query.upper().startswith(cmd) for cmd in dangerous_commands) or any(f" {cmd} " in sql_query.upper() for cmd in dangerous_commands):
            # Replace with a safe query
            sql_query = "SELECT * FROM Stores LIMIT 10;"
            content += "\n\nNOTE: The original query requested a potentially harmful operation. It was replaced with a safe SELECT query."
    else:
        # For conversational queries, use a dummy SELECT
        sql_query = "SELECT 'Aimet' AS assistant_name;"
    
    return content, sql_query


def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """Executes SQL query and returns results as a list of dictionaries"""
    # Sanitize query
    query = query.strip()
    logger.info(f"Executing query: {query}")

    # Handle dangerous queries
    if "databesi sil" in query.lower() or "veritabanı sil" in query.lower():
        logger.warning("Dangerous query detected, executing safe alternative")
        return [{"message": "Security: This operation is not allowed."}]

    # Ensure query ends with semicolon
    if not query.endswith(";"):
        query += ";"
    
    # Handle multiple statements
    if query.count(";") > 1:
        parts = query.split(";")
        query = next((p.strip() + ";" for p in parts if p.strip()), "SELECT 'no valid query found';")
        logger.warning(f"Multiple statements detected, using only: {query}")

    # Check for dangerous operations
    dangerous_commands = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(cmd in query.upper() for cmd in dangerous_commands):
        logger.warning(f"Dangerous SQL command detected: {query}")
        return [{"warning": "Data modification operations are not allowed."}]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            
            # Check if query returns data
            if cursor.description:
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()
                
                if not results:
                    return []
                
                return [{columns[i]: value for i, value in enumerate(row)} for row in results]
            else:
                conn.commit()
                return [{"result": "Query executed successfully. No data to return."}]
        
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            logger.error(f"SQLite Error: {error_msg}")
            
            if "one statement at a time" in error_msg:
                # Execute safe query if multiple statements detected
                cursor.execute("SELECT * FROM Stores LIMIT 10;")
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()
                return [{columns[i]: value for i, value in enumerate(row)} for row in results]
            
            return [{"error": f"Database error: {error_msg}"}]
        
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return [{"error": f"Error: {str(e)}"}]


def generate_title(natural_query: str, explanation: str) -> str:
    """Generate a short title for the query"""
    prompt = f"""Based on this natural language query and explanation, generate a short, descriptive title (max 50 chars):

Query: {natural_query}
Explanation: {explanation}

Generate only the title, nothing else. Make it concise but descriptive."""

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are Aimet, and you generate concise titles for database queries."},
            {"role": "user", "content": prompt},
        ],
    )
    
    return response.choices[0].message.content.strip()


async def quick_check_sql(query: str) -> Tuple[bool, str]:
    """Uses OpenAI tool calling to check data availability"""
    logger.info(f"Checking availability for query: {query}")
    
    client = OpenAI()
    schema = get_db_schema()
    
    # Get table and column information
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence' and not row[0].startswith('sqlite_')]
        
        # Get column information for each table
        table_info = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [row[1] for row in cursor.fetchall()]
            table_info[table] = columns
            
        # Get sample data
        sample_data = "\nSample data from important tables:\n"
        for table in tables:
            cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
            rows = cursor.fetchall()
            if rows:
                sample_data += f"\n{table} sample rows:\n"
                columns = [description[0] for description in cursor.description]
                for row in rows:
                    sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
    
    # Prepare schema info
    schema_info = f"Database schema and column descriptions:\n\n{schema}\n\n"
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You analyze natural language queries and determine the appropriate table and conditions for data retrieval.
                
IMPORTANT DATABASE CONTEXT:
1. When a query mentions a location like 'New York', determine if this should map to a state code like 'NY'.
2. Only use columns that actually exist in the database tables.
3. Never invent columns or reference columns not present in the schema."""
            },
            {
                "role": "user",
                "content": f"""Analyze this query to determine which table and conditions to check:

Query: {query}

{schema_info}
{sample_data}

Identify which table to query and what conditions to use based on the database schema."""
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "check_data_availability",
                    "description": "Check if data exists in the specified table with given conditions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "The main table being queried"
                            },
                            "conditions": {
                                "type": "string",
                                "description": "Key conditions or filters being applied"
                            }
                        },
                        "required": ["table_name"]
                    }
                }
            }
        ],
        tool_choice={"type": "function", "function": {"name": "check_data_availability"}}
    )
    
    # Process tool call
    tool_call = response.choices[0].message.tool_calls[0]
    function_args = json.loads(tool_call.function.arguments)
    logger.info(f"Tool call args: {function_args}")
    
    # Check data availability
    exists, message = check_data_availability(
        table_name=function_args["table_name"],
        conditions=function_args.get("conditions")
    )
    
    return exists, message


def check_data_availability(table_name: str, conditions: Optional[str] = None) -> Tuple[bool, str]:
    """Check if data exists in the specified table with given conditions"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Sanitize table name
        table_name = table_name.strip().replace(';', '')
        
        # Get actual table name with correct case
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND LOWER(name)=LOWER(?)
        """, (table_name,))
        
        actual_table = cursor.fetchone()
        if not actual_table:
            return False, f"Table '{table_name}' not found"
        
        table_name = actual_table[0]
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        column_info = cursor.fetchall()
        column_names = [col[1] for col in column_info]
        
        # Process conditions if present
        if conditions:
            conditions = conditions.strip().replace(';', '')
            logger.info(f"Table {table_name} columns: {column_names}")
            logger.info(f"Original condition: {conditions}")
            
            # Fix column references in conditions
            condition_parts = re.split(r'(AND|OR)', conditions, flags=re.IGNORECASE)
            fixed_parts = []
            
            for part in condition_parts:
                if part.upper() in ('AND', 'OR'):
                    fixed_parts.append(part)
                    continue
                    
                # Look for column references
                match = re.search(r'(\w+)\s*([=<>!]+)\s*[\'"]?([\w\s]+)[\'"]?', part)
                if match:
                    col_name = match.group(1).strip()
                    operator = match.group(2)
                    value = match.group(3).strip()
                    
                    if col_name not in column_names:
                        # Handle city to state conversion 
                        if col_name.lower() == 'city' and 'State' in column_names and 'new york' in part.lower():
                            part = f"State {operator} 'NY'"
                            logger.info(f"Fixed reference: {conditions} → {part}")
            
                fixed_parts.append(part)
            
            # Join the fixed parts
            modified_conditions = ''.join(fixed_parts)
            if modified_conditions != conditions:
                logger.info(f"Modified conditions: {modified_conditions}")
                conditions = modified_conditions
        
            # Execute EXISTS query with conditions
            query = f"SELECT EXISTS (SELECT 1 FROM [{table_name}] WHERE {conditions})"
        else:
            query = f"SELECT EXISTS (SELECT 1 FROM [{table_name}] LIMIT 1)"
        
        logger.info(f"Checking data with query: {query}")
        
        try:
            cursor.execute(query)
            exists = cursor.fetchone()[0]
            message = f"Data found in table '{table_name}'" if exists else f"No data found in table '{table_name}'"
            if conditions and exists == 0:
                message += f" with conditions: {conditions}"
            return bool(exists), message
        except sqlite3.Error as e:
            logger.error(f"SQL Error: {str(e)}")
            return False, f"Error checking data in table '{table_name}': {str(e)}"


def process_natural_query(natural_query: str, session_id: str = None) -> Tuple[str, str, List[Dict[str, Any]], str, str]:
    """Process a natural language query, convert to SQL and execute"""
    from query_history import save_query_history, generate_session_id
    
    if session_id is None:
        session_id = generate_session_id()
    
    # Handle dangerous queries
    if any(w in natural_query.lower() for w in ["databesi sil", "veritabanını sil", "drop", "delete"]):
        logger.warning(f"Dangerous query detected: {natural_query}")
        explanation = "This query requested a potentially harmful operation and was replaced with a safe query."
        sql_query = "SELECT * FROM Stores LIMIT 10;"
        results = execute_sql_query(sql_query)
        title = "Safe Query"
        
        save_query_history(session_id, natural_query, sql_query, explanation, results, title)
        return explanation, sql_query, results, session_id, title

    # Generate SQL from natural language
    full_response, sql_query = generate_sql_query(natural_query)
    
    # Log full response for debugging
    logger.info(f"GPT Response: {full_response[:100]}...")
    
    # Handle multiple statements
    if ";" in sql_query and not sql_query.strip().endswith(";"):
        sql_query = sql_query.split(";")[0].strip() + ";"
        logger.warning(f"Multiple SQL statements detected, using only: {sql_query}")
    
    # Handle dangerous operations
    danger_words = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(word in sql_query.upper() for word in danger_words):
        logger.warning(f"Dangerous SQL query detected: {sql_query}")
        sql_query = "SELECT * FROM Stores LIMIT 10;"
        full_response += "\n\nSecurity warning: The requested query was potentially harmful and was replaced."
    
    # Execute the query
    results = execute_sql_query(sql_query)
    
    # Generate a title
    title = generate_title(natural_query, full_response)
    
    # Save to history
    save_query_history(session_id, natural_query, sql_query, full_response, results, title)
    
    return full_response, sql_query, results, session_id, title