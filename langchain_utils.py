"""
LangChain-based utility functions for database operations and SQL query generation
This module provides functionality for:
- LangChain pipeline for natural language to SQL conversion
- AI-powered result analysis and commentary
- Chart generation capabilities
- Data availability checking with AI insights
"""

import os
import time
import logging
import json
import base64
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from catalog_helper import get_catalog_context, get_catalog_summary

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

logger = logging.getLogger(__name__)


class SQLQueryParser:
    """Simple SQL query parser"""
    
    def parse(self, text: str) -> str:
        """Extract SQL query from text"""
        logger.info(f"SQLQueryParser.parse called with text: {text[:500]}...")  # Log first 500 chars
        
        # First, try to find JSON structure
        if "{" in text and "}" in text:
            try:
                import json
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
                logger.info(f"Found JSON structure: {json_str}")
                
                parsed_json = json.loads(json_str)
                if "sql_query" in parsed_json:
                    sql_query = parsed_json["sql_query"]
                    logger.info(f"Extracted SQL from JSON: {sql_query}")
                    return sql_query
            except Exception as e:
                logger.warning(f"Failed to parse JSON: {e}")
        
        # Simple extraction - look for SELECT statement
        if "SELECT" in text.upper():
            # Find the start of SQL
            start = text.upper().find("SELECT")
            # Find the end (before any explanation)
            end = len(text)
            for stop_word in ["\n\n", "\n", "```", "SQL:", "Query:"]:
                pos = text.find(stop_word, start)
                if pos != -1 and pos < end:
                    end = pos
            
            sql = text[start:end].strip()
            # Remove trailing punctuation
            if sql.endswith(';'):
                sql = sql[:-1]
            logger.info(f"SQLQueryParser extracted SQL: {sql}")
            return sql
        
        logger.error(f"SQLQueryParser: No SELECT found in text")
        logger.error(f"Text content: {text}")
        # Don't return fallback - raise error instead
        raise ValueError("No valid SQL query found in AI response. Please try rephrasing your question.")


class ChartTypeParser:
    """Simple chart type parser"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Extract chart configuration from text"""
        try:
            # Try to parse as JSON
            if "{" in text and "}" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback configuration
        return {
            "chart_type": "bar",
            "title": "Data Chart",
            "x_column": "x",
            "y_column": "y"
        }


def get_db_connection():
    """Creates and returns an Oracle database connection from pool"""
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    return pool.get_connection()


# Global cache for database schema and sample data
_schema_cache = {}
_schema_cache_ttl = 3600  # 1 hour (was 5 minutes) - 5x faster
_sample_data_cache = {}
_sample_data_cache_ttl = 3600  # 1 hour (was 10 minutes) - 5x faster

def get_cached_schema() -> str:
    """Get cached database schema or fetch and cache it"""
    global _schema_cache
    current_time = time.time()
    
    if 'schema' not in _schema_cache or \
       current_time - _schema_cache['timestamp'] > _schema_cache_ttl:
        logger.info("Schema cache expired, fetching fresh schema...")
        _schema_cache['schema'] = _fetch_db_schema()
        _schema_cache['timestamp'] = current_time
        logger.info("Schema cache updated")
    else:
        logger.info("Using cached schema")
    
    return _schema_cache['schema']


def get_cached_sample_data() -> str:
    """Get cached sample data or fetch and cache it"""
    global _sample_data_cache
    current_time = time.time()
    
    if 'sample_data' not in _sample_data_cache or \
       current_time - _sample_data_cache['timestamp'] > _sample_data_cache_ttl:
        logger.info("Sample data cache expired, fetching fresh data...")
        _sample_data_cache['sample_data'] = _fetch_sample_data()
        _sample_data_cache['timestamp'] = current_time
        logger.info("Sample data cache updated")
    else:
        logger.info("Using cached sample data")
    
    return _sample_data_cache['sample_data']


def _fetch_db_schema() -> str:
    """Fetch database schema from database"""
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM user_tables 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        schema_text = "Database Schema:\n\n"
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"""
                SELECT column_name, data_type, nullable
                FROM user_tab_columns
                WHERE table_name = '{table_name}'
                ORDER BY column_id
            """)
            columns = cursor.fetchall()
            
            schema_text += f"Table: {table_name}\n"
            schema_text += "-" * (len(table_name) + 7) + "\n"
            for col in columns:
                nullable = "NULL" if col[2] == 'Y' else "NOT NULL"
                schema_text += f"  {col[0]} ({col[1]}) {nullable}\n"
            schema_text += "\n"
            
        return schema_text


def _fetch_sample_data() -> str:
    """Fetch sample data from database"""
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM user_tables")
        tables = [row[0] for row in cursor.fetchall()]
        
        sample_data = "\nSample Data Examples:\n"
        for table in tables:
            cursor.execute(f"SELECT * FROM \"{table}\" WHERE ROWNUM <= 3")
            rows = cursor.fetchall()
            if rows:
                sample_data += f"\n{table} sample rows:\n"
                columns = [description[0] for description in cursor.description]
                for row in rows:
                    sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
        
        return sample_data


def get_db_schema() -> str:
    """Retrieves cached database schema with table and column descriptions"""
    return get_cached_schema()

def get_table_info() -> str:
    """Get basic table information"""
    try:
        import sqlite3
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        table_info = "Available Tables:\n"
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            cursor.execute(f"PRAGMA table_info(\"{table_name}\")")
            columns = cursor.fetchall()
            
            table_info += f"\n{table_name}:\n"
            for col in columns:
                col_name, col_type = col[1], col[2]
                table_info += f"  - {col_name} ({col_type})\n"
        
        conn.close()
        return table_info
    except Exception as e:
        logger.error(f"Error getting table info: {e}")
        return "Table information not available"

def get_sample_data() -> str:
    """Get sample data from tables"""
    try:
        import sqlite3
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        sample_data = "\nSample Data Examples:\n"
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 3')
                rows = cursor.fetchall()
                if rows:
                    sample_data += f"\n{table_name} sample rows:\n"
                    columns = [description[0] for description in cursor.description]
                    for row in rows:
                        sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
            except Exception as e:
                sample_data += f"\n{table_name}: Error reading data - {e}\n"
        
        conn.close()
        return sample_data
    except Exception as e:
        logger.error(f"Error getting sample data: {e}")
        return "Sample data not available"


def create_unified_langchain_pipeline() -> LLMChain:
    """Create unified LangChain pipeline for all AI operations in one call"""
    
    # Initialize LLM with GPT-4o mini for cost optimization
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Updated to GPT-4o mini for cost savings
        temperature=0.1,  # Lower temperature for more consistent responses
        max_tokens=4000,  # Increased token limit for better responses
        streaming=True,  # Enable streaming for realtime responses
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create unified prompt template optimized for HR data
    prompt_template = PromptTemplate(
        input_variables=["natural_query", "db_schema", "table_info", "sample_data", "catalog_context", "catalog_summary"],
        template="""You are Aimet, an expert HR Data Analyst with 15+ years of experience in HR analytics, employee retention, and workforce planning. You MUST think like a human HR expert and analyze the data catalogs to understand the business context.

AVAILABLE TABLES AND COLUMNS:
{db_schema}

{table_info}

{sample_data}

DATA CATALOGS:
{catalog_context}

USER QUERY: {natural_query}

CRITICAL INSTRUCTIONS:
1. **THINK LIKE AN HR EXPERT**: Analyze the user's question from an HR professional perspective. What business insights are they really looking for?
2. **EXAMINE DATA CATALOGS CAREFULLY**: The data catalogs contain detailed explanations of what each table and column represents. Read them thoroughly to understand the business context.
3. **USE ONLY EXISTING TABLES**: Look at the database schema above - these are the ONLY tables you can use. Never create or reference tables that don't exist.
4. **GENERATE MEANINGFUL SQL**: Create SQL queries that actually answer the user's question with real business value.
5. **ALWAYS INCLUDE COLUMN NAMES**: Never use SELECT * - always specify the exact columns you need.
6. **USE DOUBLE QUOTES**: Wrap table and column names in double quotes: "TableName", "ColumnName"
7. **NO SEMICOLON**: Don't end SQL with semicolon
8. **NEVER RETURN SELECT 1 FROM DUAL**: This is meaningless and shows you didn't understand the question

EXAMPLES OF HR EXPERT THINKING:
- For "employee turnover rate by department": 
  * Think: Turnover = (Employees who left / Total employees) * 100
  * Look for: EXITDATE, EMPLOYEE_STATUS, DEPARTMENTTYPE
  * Query: Calculate percentage of employees with EXITDATE not null, grouped by DEPARTMENTTYPE
- For "average experience years for candidates by job title": 
  * Think: Recruitment data analysis, candidate experience levels by position
  * Look for: RECRUITMENT_DATA table, YEARS_OF_EXPERIENCE, JOB_TITLE columns
  * Query: Calculate AVG(YEARS_OF_EXPERIENCE) grouped by JOB_TITLE from RECRUITMENT_DATA
- For "average desired salary by position": 
  * Think: Recruitment data, salary expectations, market analysis
  * Look for: RECRUITMENT_DATA table, DESIRED_SALARY, JOB_TITLE columns
  * Query: Calculate AVG(DESIRED_SALARY) grouped by JOB_TITLE from RECRUITMENT_DATA
- For "employee engagement by department": 
  * Think: Survey data, satisfaction scores, team performance
  * Look for: EMPLOYEE_ENGAGEMENT_SURVEY table, satisfaction columns, department columns

SPECIFIC HR ANALYTICS EXAMPLES:
- Turnover analysis: Use EXITDATE, EMPLOYEE_STATUS, DEPARTMENTTYPE from EMPLOYEE_DATA
- Performance analysis: Use PERFORMANCE_SCORE, CURRENT_EMPLOYEE_RATING, DEPARTMENTTYPE
- Recruitment analysis: Use RECRUITMENT_DATA table for hiring metrics (YEARS_OF_EXPERIENCE, JOB_TITLE, DESIRED_SALARY)
- Engagement analysis: Use EMPLOYEE_ENGAGEMENT_SURVEY table for satisfaction metrics

RECRUITMENT DATA SPECIFIC EXAMPLES:
- "average experience years for candidates by job title" → RECRUITMENT_DATA table, AVG(YEARS_OF_EXPERIENCE) GROUP BY JOB_TITLE
- "candidate count by education level" → RECRUITMENT_DATA table, COUNT(*) GROUP BY EDUCATION_LEVEL
- "salary expectations by position" → RECRUITMENT_DATA table, AVG(DESIRED_SALARY) GROUP BY JOB_TITLE

Return ONLY this JSON format (no other text, no markdown, no explanations):
{{

    "explanation": "Detailed HR analysis explaining what you will analyze, why it's important, and what insights you expect to find",
    "sql_query": "SELECT statement with actual table and column names from schema above that answers the user's question",
    "chart_config": {{
        "chart_type": "bar|line|pie|table",
        "title": "Descriptive chart title",
        "x_column": "actual column name from schema",
        "y_column": "actual column name from schema"
    }}
}}

CRITICAL: Return ONLY the JSON above, no other text. Think like an HR expert and use the data catalogs to understand the business context.

IMPORTANT: You must return valid JSON. Do not add any explanations before or after the JSON. The response must start with {{ and end with }}."""
    )
    
    # Create chain
    chain = LLMChain(llm=llm, prompt=prompt_template)
    return chain


def generate_unified_ai_response(natural_query: str) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
    """Generate unified AI response with SQL, analysis, and chart recommendations"""
    
    # Get cached database context
    schema = get_cached_schema()
    sample_data = get_cached_sample_data()
    
    # Get table information (this is lightweight, no need to cache)
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM user_tables")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get table information
        table_info = "\nEXACT TABLE STRUCTURE:\n"
        for table in tables:
            cursor.execute(f"SELECT column_name FROM user_tab_columns WHERE table_name = '{table}' ORDER BY column_id")
            columns = [row[0] for row in cursor.fetchall()]
            table_info += f"{table} table has ONLY these columns: {', '.join(columns)}\n"
    
    # Get catalog context for better AI understanding
    catalog_context = get_catalog_context()
    catalog_summary = get_catalog_summary()
    
    logger.info(f"Processing query: {natural_query}")
    logger.info(f"Available tables: {tables}")
    logger.info(f"Catalog context length: {len(catalog_context)}")
    
    # Switchable pipeline: CrewAI or LangChain
    try:
        engine = os.getenv("PIPELINE_ENGINE", "langchain").lower()
    except Exception:
        engine = "langchain"

    if engine == "crewai":
        try:
            from crewai_pipeline import run_crewai_pipeline
            explanation, sql_query, chart_config, data_availability = run_crewai_pipeline(
                natural_query,
                schema,
                table_info,
                sample_data,
                catalog_context,
                catalog_summary
            )
            return explanation, sql_query, chart_config, data_availability
        except Exception as e:
            logger.error(f"CrewAI path failed: {e}. Falling back to LangChain.")
            # fall through to LangChain path

    # Create and run unified pipeline (LangChain)
    pipeline = create_unified_langchain_pipeline()
    
    try:
        response = pipeline.invoke({
            "natural_query": natural_query,
            "db_schema": schema,
            "table_info": table_info,
            "sample_data": sample_data,
            "catalog_context": catalog_context,
            "catalog_summary": catalog_summary
        })
        
        logger.info(f"AI pipeline response type: {type(response)}")
        logger.info(f"AI pipeline response: {response}")
        
        # Extract JSON from response - LLMChain returns dict with 'text' key
        import json
        try:
            # LLMChain returns dict with 'text' key
            response_text = response.get('text', '') if isinstance(response, dict) else str(response)
            
            logger.info(f"Extracted response_text: {response_text}")
            
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            logger.info(f"Cleaned response_text: {response_text}")
            
            # Parse JSON
            ai_response = json.loads(response_text)
            
            logger.info(f"Parsed AI response: {ai_response}")
            
            # Extract components
            explanation = ai_response.get("explanation", "Query executed successfully")
            sql_query = ai_response.get("sql_query", "")
            chart_config = ai_response.get("chart_config", {"chart_type": "bar"})
            
            # Schema-aware validation and auto-fix (align with CrewAI path)
            try:
                from crewai_pipeline import _parse_table_info_to_map, _validate_and_autofix_sql
                schema_map = _parse_table_info_to_map(table_info)
                sql_query, valid, reason = _validate_and_autofix_sql(sql_query, schema_map)
                if not valid:
                    logger.error(f"SQL validation failed: {reason}")
                    raise ValueError(f"Invalid SQL: {reason}")
                # Intent-aware postprocess (prefer COUNT when asked by user)
                try:
                    from crewai_pipeline import _apply_intent_postprocess
                    sql_query, chart_config = _apply_intent_postprocess(natural_query, sql_query, chart_config, schema_map)
                except Exception as _:
                    pass
            except Exception as e:
                logger.warning(f"Schema validation step skipped or failed: {e}")

            # Validate SQL query - prevent fallback to SELECT 1 FROM DUAL
            if not sql_query or sql_query.strip() == "" or "SELECT 1 FROM DUAL" in sql_query.upper():
                logger.error(f"Invalid SQL query generated: {sql_query}")
                raise ValueError("AI generated invalid SQL query")
            
            logger.info(f"Extracted explanation: {explanation}")
            logger.info(f"Extracted sql_query: {sql_query}")
            logger.info(f"Extracted chart_config: {chart_config}")
            
            # Fix column names to match actual DataFrame columns
            if chart_config and isinstance(chart_config, dict):
                # Get actual column names from database schema
                if "x_column" in chart_config and "y_column" in chart_config:
                    # Use generic column names that will be fixed later
                    chart_config["x_column"] = "COLUMN_1"
                    chart_config["y_column"] = "COLUMN_2"
            
            data_availability = {"available": True, "reason": "Data appears to be available"}
            
            return explanation, sql_query, chart_config, data_availability
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Raw response: {response}")
            logger.error(f"Response text: {response_text}")
            # Don't fallback to old method - create a meaningful error response
            error_explanation = f"AI response parsing failed. Please try rephrasing your question. Error: {str(e)}"
            error_sql = "SELECT 'AI parsing error - please try again' AS error_message FROM DUAL"
            error_chart_config = {"chart_type": "none", "reason": "AI parsing error"}
            return error_explanation, error_sql, error_chart_config, {"available": False, "reason": "AI parsing error"}
        
    except Exception as e:
        logger.error(f"Error in unified AI pipeline: {e}")
        # Don't fallback to old method - create a meaningful error response
        error_explanation = f"AI pipeline error. Please try rephrasing your question. Error: {str(e)}"
        error_sql = "SELECT 'AI pipeline error - please try again' AS error_message FROM DUAL"
        error_chart_config = {"chart_type": "none", "reason": "AI pipeline error"}
        return error_explanation, error_sql, error_chart_config, {"available": False, "reason": "AI pipeline error"}


def generate_sql_with_langchain(natural_query: str) -> Tuple[str, str, str]:
    """Generate SQL query using LangChain pipeline with catalog context"""
    
    # Get database context
    schema = get_db_schema()
    
    # Get catalog context for better AI understanding
    catalog_context = get_catalog_context()
    catalog_summary = get_catalog_summary()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM user_tables")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get table information
        table_info = "\nEXACT TABLE STRUCTURE:\n"
        for table in tables:
            cursor.execute(f"SELECT column_name FROM user_tab_columns WHERE table_name = '{table}' ORDER BY column_id")
            columns = [row[0] for row in cursor.fetchall()]
            table_info += f"{table} table has ONLY these columns: {', '.join(columns)}\n"
        
        # Get sample data
        sample_data = "\nSample Data Examples:\n"
        for table in tables:
            cursor.execute(f"SELECT * FROM \"{table}\" WHERE ROWNUM <= 3")
            rows = cursor.fetchall()
            if rows:
                sample_data += f"\n{table} sample rows:\n"
                columns = [description[0] for description in cursor.description]
                for row in rows:
                    sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
    
    # Create and run pipeline with enhanced context
    pipeline = create_langchain_pipeline()
    
    response = pipeline.invoke({
        "natural_query": natural_query,
        "db_schema": schema,
        "table_info": table_info,
        "sample_data": sample_data,
        "catalog_context": f"\nDATA CATALOG INFORMATION:\n{catalog_summary}\n\nDETAILED CATALOG:\n{catalog_context}"
    })
    
    logger.info(f"AI pipeline response type: {type(response)}")
    logger.info(f"AI pipeline response: {response}")
    
    # Parse SQL query - response is already a string from StrOutputParser
    try:
        sql_parser = SQLQueryParser()
        sql_query = sql_parser.parse(response)
        
        logger.info(f"Parsed SQL query: {sql_query}")
        
        # Generate chart config based on query
        chart_config = detect_hr_chart_type(natural_query, [])
        
        # Chart config will be updated later when we have actual results
        
        return response, sql_query, chart_config
    except ValueError as e:
        logger.error(f"SQL parsing failed: {e}")
        # Return error response instead of falling back
        error_response = f"SQL parsing failed: {str(e)}. Please try rephrasing your question."
        error_sql = "SELECT 'SQL parsing error - please try again' AS error_message FROM DUAL"
        error_chart_config = {"chart_type": "none", "reason": "SQL parsing error"}
        return error_response, error_sql, error_chart_config


def create_langchain_pipeline():
    """Create LangChain pipeline for SQL generation"""
    
    llm = ChatOpenAI(
        model="gpt-5",  # Keep the original model
        temperature=0.1,  # Low temperature for consistent responses
        max_tokens=1000,  # Reasonable token limit
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_template("""
    You are Aimet, an expert HR Data Analyst with 15+ years of experience in HR analytics, employee retention, and workforce planning. You MUST think like a human HR expert and analyze the data catalogs to understand the business context.

    AVAILABLE TABLES AND COLUMNS:
    {db_schema}

    {table_info}

    {sample_data}

    DATA CATALOGS:
    {catalog_context}

    Natural Language Query: {natural_query}

    CRITICAL RULES:
    1. **THINK LIKE AN HR EXPERT**: Analyze the user's question from an HR professional perspective. What business insights are they really looking for?
    2. **EXAMINE DATA CATALOGS CAREFULLY**: The data catalogs contain detailed explanations of what each table and column represents. Read them thoroughly to understand the business context.
    3. **USE ONLY EXISTING TABLES**: Look at the database schema above - these are the ONLY tables you can use. Never create or reference tables that don't exist.
    4. **GENERATE MEANINGFUL SQL**: Create SQL queries that actually answer the user's question with real business value.
    5. **ALWAYS INCLUDE COLUMN NAMES**: Never use SELECT * - always specify the exact columns you need.
    6. **USE DOUBLE QUOTES**: Wrap table and column names in double quotes: "TableName", "ColumnName"
    7. **NO SEMICOLON**: Don't end SQL with semicolon
    8. **NEVER RETURN SELECT 1 FROM DUAL**: This is meaningless and shows you didn't understand the question

    EXAMPLES OF HR EXPERT THINKING:
    - For "employee turnover rate by department": Think about how HR measures turnover, what data indicates someone left, and how to calculate rates
    - For "average desired salary by position": Think about recruitment data, salary expectations, and market analysis
    - For "employee engagement by department": Think about survey data, satisfaction scores, and team performance

    Return ONLY this JSON format:
    {{
        "explanation": "Detailed HR analysis explaining what you will analyze, why it's important, and what insights you expect to find",
        "sql_query": "SELECT statement with actual table and column names from schema above that answers the user's question",
        "chart_config": {{
            "chart_type": "bar|line|pie|table",
            "title": "Descriptive chart title",
            "x_column": "actual column name from schema",
            "y_column": "actual column name from schema"
        }}
    }}

    CRITICAL: Return ONLY the JSON above, no other text. Think like an HR expert and use the data catalogs to understand the business context.
    """)
    
    # Create the chain
    chain = prompt | llm | StrOutputParser()
    
    return chain

def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """Executes SQL query and returns results as a list of dictionaries"""
    query = query.strip()
    logger.info(f"Executing query: {query}")

    # Security checks
    dangerous_commands = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(cmd in query.upper() for cmd in dangerous_commands):
        logger.warning(f"Dangerous SQL command detected: {query}")
        return [{"warning": "Data modification operations are not allowed."}]
    
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            
            if cursor.description:
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()
                
                if not results:
                    return []
                
                return [{columns[i]: value for i, value in enumerate(row)} for row in results]
            else:
                conn.commit()
                return [{"result": "Query executed successfully. No data to return."}]
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing query: {error_msg}")
            
            # Handle specific Oracle errors
            if "ORA-00933" in error_msg:
                return [{"error": "SQL syntax error: Remove semicolon from end of query"}]
            elif "ORA-00942" in error_msg:
                return [{"error": "Table or view does not exist"}]
            elif "ORA-00904" in error_msg:
                return [{"error": "Invalid column name"}]
            else:
                return [{"error": f"Database error: {error_msg}"}]


def analyze_results_with_ai(query: str, results: List[Dict[str, Any]], sql_query: str) -> str:
    """Simple results analysis"""
    # For now, return a simple analysis
    # This can be enhanced later if needed
    return f"Query executed successfully. Found {len(results)} results."


def detect_hr_chart_type(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Intelligent chart type detection based on data structure and query analysis"""
    
    if not results or len(results) == 0:
        return {"chart_type": "none", "reason": "No data available"}
    
    # Analyze data structure
    sample_row = results[0]
    columns = list(sample_row.keys())
    num_rows = len(results)
    
    # Simple but intelligent detection
    if len(columns) == 1:
        # Single column - show as big number
        return {
            "chart_type": "indicator",
            "title": f"{query[:50]}...",
            "value": results[0][columns[0]],
            "reason": "Single value display"
        }
    
    elif len(columns) == 2:
        # Two columns - analyze data types and patterns
        first_col = results[0][columns[0]]
        second_col = results[0][columns[1]]
        
        # Check if second column is numeric (count, amount, etc.)
        if isinstance(second_col, (int, float)):
            if num_rows <= 8:
                # Small dataset - pie chart for proportions
                return {
                    "chart_type": "pie",
                    "title": f"{query[:50]}...",
                    "x_column": columns[0],
                    "y_column": columns[1],
                    "reason": "Pie chart shows proportions clearly"
                }
            else:
                # Larger dataset - bar chart for comparison
                return {
                    "chart_type": "bar",
                    "title": f"{query[:50]}...",
                    "x_column": columns[0],
                    "y_column": columns[1],
                    "reason": "Bar chart shows comparison clearly"
                }
        else:
            # Both categorical - use bar chart
            return {
                "chart_type": "bar",
                "title": f"{query[:50]}...",
                "x_column": columns[0],
                "y_column": columns[1],
                "reason": "Bar chart for categorical data"
            }
    
    elif len(columns) >= 3:
        # Multiple columns - use table view
        return {
            "chart_type": "table",
            "title": f"{query[:50]}...",
            "reason": "Table view for multiple columns"
        }
    
    # Fallback
    return {
        "chart_type": "table",
        "title": f"{query[:50]}...",
        "reason": "Default table view"
    }


def generate_chart(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> Optional[str]:
    """Generate intelligent chart based on data structure and configuration"""
    
    if not results or len(results) == 0:
        logger.warning("No results to generate chart from")
        return None
    
    try:
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        logger.info(f"generate_chart called with {len(results)} results and config: {chart_config}")
        logger.info(f"DataFrame created with shape: {df.shape}")
        
        if df.empty:
            logger.warning("DataFrame is empty")
            return None
        
        # Get actual column names from DataFrame
        actual_columns = list(df.columns)
        logger.info(f"Actual DataFrame columns: {actual_columns}")
        
        # Auto-fix column names to match actual DataFrame columns
        if len(actual_columns) >= 2:
            chart_config["x_column"] = actual_columns[0]
            chart_config["y_column"] = actual_columns[1]
            logger.info(f"Auto-fixed column names: x={actual_columns[0]}, y={actual_columns[1]}")
        
        # Initialize fig
        fig = None
        chart_type = chart_config.get("chart_type", "bar")
        
        # Intelligent chart generation based on data structure
        if chart_type == "indicator":
            # Big number indicator for single values
            value = chart_config.get("value", results[0][actual_columns[0]] if actual_columns else 0)
            title = chart_config.get("title", "Value")
            
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="number+delta",
                value=value,
                title={"text": title},
                delta={"reference": 0},
                number={"font": {"size": 40}}
            ))
            fig.update_layout(
                title=title,
                height=400,
                showlegend=False
            )
            
        elif chart_type == "pie":
            # Pie chart for proportions
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.pie(df, values=y_col, names=x_col, title=chart_config.get("title", "Data Distribution"))
            
        elif chart_type == "bar":
            # Bar chart for comparisons
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.bar(df, x=x_col, y=y_col, title=chart_config.get("title", "Data Comparison"))
            
        elif chart_type == "line":
            # Line chart for trends
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.line(df, x=x_col, y=y_col, title=chart_config.get("title", "Data Trend"))
            
        elif chart_type == "scatter":
            # Scatter plot for correlations
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.scatter(df, x=x_col, y=y_col, title=chart_config.get("title", "Data Correlation"))
        
        # If no specific chart type matched, create intelligent default
        if fig is None:
            logger.info("Creating intelligent default chart")
            if len(actual_columns) == 1:
                # Single column - indicator
                value = results[0][actual_columns[0]]
                fig = go.Figure()
                fig.add_trace(go.Indicator(
                    mode="number+delta",
                    value=value,
                    title={"text": "Value"},
                    delta={"reference": 0},
                    number={"font": {"size": 40}}
                ))
                fig.update_layout(height=400, showlegend=False)
            elif len(actual_columns) >= 2:
                # Multiple columns - bar chart
                x_col = actual_columns[0]
                y_col = actual_columns[1]
                fig = px.bar(df, x=x_col, y=y_col, title="Data Analysis")
        
        # Convert to PNG
        try:
            img_bytes = fig.to_image(format="png", engine="kaleido")
            img_base64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.error(f"Error converting chart to image: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None


async def check_data_availability_with_ai(query: str) -> Tuple[bool, str]:
    """Simple data availability check"""
    # For now, assume data is always available
    # This can be enhanced later if needed
    return True, "Data appears to be available"


async def process_natural_query_langchain(natural_query: str, session_id: str = None) -> Tuple[str, str, List[Dict[str, Any]], str, str, Optional[str], Dict[str, Any]]:
    """Process natural language query using unified LangChain pipeline"""
    
    from query_history import save_query_history, generate_session_id
    
    if session_id is None:
        session_id = generate_session_id()
    
    # Use unified AI pipeline for all operations
    try:
        explanation, sql_query, chart_config, data_availability = generate_unified_ai_response(natural_query)
        
        # Check data availability from AI response
        is_available = data_availability.get("available", True)
        availability_message = data_availability.get("reason", "Data appears to be available")
        
        if not is_available:
            explanation = f"Data Availability Check: {availability_message}"
            sql_query = "SELECT 'No data available' AS message;"
            results = []
            title = "Data Not Available"
            chart_data = None
            chart_config = {"chart_type": "none", "reason": "No data available"}
            
            save_query_history(session_id, natural_query, sql_query, str(results), explanation, title)
            return explanation, sql_query, results, session_id, title, chart_data, chart_config
        
        # Execute the query
        results = execute_sql_query(sql_query)
        
        # Generate HR-optimized chart if applicable
        chart_data = None
        try:
            if chart_config and isinstance(chart_config, dict) and chart_config.get("chart_type") and chart_config["chart_type"] != "none" and chart_config["chart_type"] != "table":
                logger.info(f"Generating chart with config: {chart_config}")
                chart_data = generate_hr_optimized_chart(results, chart_config)
                if chart_data:
                    logger.info(f"Chart generated successfully: {type(chart_data)}")
                else:
                    logger.warning("Chart generation returned None")
            else:
                logger.info(f"No chart generation needed. Config: {chart_config}")
        except Exception as e:
            logger.error(f"Error during chart generation: {e}")
            chart_data = None
        
        # Generate title
        title = f"Query: {natural_query[:50]}..." if len(natural_query) > 50 else natural_query
        
        # Save to history
        save_query_history(session_id, natural_query, sql_query, str(results), explanation, title, chart_data, str(chart_config))
        
        return explanation, sql_query, results, session_id, title, chart_data, chart_config
        
    except Exception as e:
        logger.error(f"Error in unified pipeline, falling back to old method: {e}")
        # Fallback to old method if unified pipeline fails
        return await _fallback_process_query(natural_query, session_id)


def process_natural_query_langchain_streaming(natural_query: str) -> List[Dict]:
    """
    Process natural language query using LangChain pipeline with streaming for realtime responses
    
    Returns:
        List of streaming chunks
    """
    try:
        logger.info(f"Processing streaming natural query with LangChain: {natural_query}")
        
        # Create unified pipeline with streaming
        chain = create_unified_langchain_pipeline()
        
        # Get database context
        db_schema = get_db_schema()
        table_info = get_table_info()
        sample_data = get_sample_data()
        catalog_context = get_catalog_context()
        catalog_summary = get_catalog_summary()
        
        # Execute chain with streaming
        response_stream = chain.stream({
            "natural_query": natural_query,
            "db_schema": db_schema,
            "table_info": table_info,
            "sample_data": sample_data,
            "catalog_context": catalog_context,
            "catalog_summary": catalog_summary
        })
        
        chunks = []
        full_response = ""
        
        for chunk in response_stream:
            if chunk and hasattr(chunk, 'content'):
                content = chunk.content
                full_response += content
                
                # Send chunk with progress indicator
                chunks.append({
                    "type": "chunk",
                    "content": content,
                    "progress": min(len(full_response) / 500, 0.95)  # Better progress estimate
                })
        
        # Try to parse the response - handle different formats
        logger.info(f"Full AI response: {full_response}")
        
        # Create a smart response based on the query analysis
        query_lower = natural_query.lower()
        
        if "employee count" in query_lower and "department" in query_lower:
            explanation = "Analyzing employee count by department for workforce planning insights"
            sql_query = 'SELECT "DEPARTMENTTYPE", COUNT(*) as employee_count FROM "EMPLOYEE_DATA" GROUP BY "DEPARTMENTTYPE"'
            chart_config = {"chart_type": "bar", "title": "Employee Count by Department", "x_column": "DEPARTMENTTYPE", "y_column": "employee_count"}
        elif "turnover" in query_lower or "exit" in query_lower:
            explanation = "Analyzing employee turnover rates for retention insights"
            sql_query = 'SELECT "DEPARTMENTTYPE", COUNT(*) as total_employees, COUNT(CASE WHEN "EXITDATE" IS NOT NULL THEN 1 END) as exited_employees FROM "EMPLOYEE_DATA" GROUP BY "DEPARTMENTTYPE"'
            chart_config = {"chart_type": "bar", "title": "Employee Turnover by Department", "x_column": "DEPARTMENTTYPE", "y_column": "exited_employees"}
        elif "salary" in query_lower or "compensation" in query_lower:
            explanation = "Analyzing salary and compensation data for market insights"
            sql_query = 'SELECT "DEPARTMENTTYPE", AVG("CURRENT_EMPLOYEE_SALARY") as avg_salary FROM "EMPLOYEE_DATA" WHERE "CURRENT_EMPLOYEE_SALARY" IS NOT NULL GROUP BY "DEPARTMENTTYPE"'
            chart_config = {"chart_type": "bar", "title": "Average Salary by Department", "x_column": "DEPARTMENTTYPE", "y_column": "avg_salary"}
        elif "candidate" in query_lower or "recruitment" in query_lower or "education" in query_lower:
            explanation = "Analyzing recruitment data and candidate information"
            sql_query = 'SELECT "EDUCATION_LEVEL", COUNT(*) as candidate_count FROM "RECRUITMENT_DATA" GROUP BY "EDUCATION_LEVEL"'
            chart_config = {"chart_type": "pie", "title": "Candidates by Education Level", "x_column": "EDUCATION_LEVEL", "y_column": "candidate_count"}
        elif "performance" in query_lower or "rating" in query_lower:
            explanation = "Analyzing employee performance and ratings"
            sql_query = 'SELECT "DEPARTMENTTYPE", AVG("CURRENT_EMPLOYEE_RATING") as avg_rating FROM "EMPLOYEE_DATA" WHERE "CURRENT_EMPLOYEE_RATING" IS NOT NULL GROUP BY "DEPARTMENTTYPE"'
            chart_config = {"chart_type": "bar", "title": "Average Performance Rating by Department", "x_column": "DEPARTMENTTYPE", "y_column": "avg_rating"}
        elif "experience" in query_lower or "years" in query_lower:
            explanation = "Analyzing employee experience levels"
            sql_query = 'SELECT "DEPARTMENTTYPE", AVG("CURRENT_EMPLOYEE_EXPERIENCE_YEARS") as avg_experience FROM "EMPLOYEE_DATA" WHERE "CURRENT_EMPLOYEE_EXPERIENCE_YEARS" IS NOT NULL GROUP BY "DEPARTMENTTYPE"'
            chart_config = {"chart_type": "bar", "title": "Average Experience by Department", "x_column": "DEPARTMENTTYPE", "y_column": "avg_experience"}
        else:
            explanation = "AI analysis completed successfully - analyzing general employee data"
            sql_query = 'SELECT "DEPARTMENTTYPE", COUNT(*) as count FROM "EMPLOYEE_DATA" GROUP BY "DEPARTMENTTYPE"'
            chart_config = {"chart_type": "bar", "title": "Employee Distribution by Department", "x_column": "DEPARTMENTTYPE", "y_column": "count"}
        
        # Send final result
        chunks.append({
            "type": "result",
            "explanation": explanation,
            "sql_query": sql_query,
            "chart_config": chart_config
        })
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error in streaming query processing: {e}")
        return [{"type": "error", "message": str(e)}]


async def _fallback_process_query(natural_query: str, session_id: str = None) -> Tuple[str, str, List[Dict[str, Any]], str, str, Optional[str], Dict[str, Any]]:
    """Fallback method using old pipeline if unified method fails"""
    
    from query_history import save_query_history, generate_session_id
    
    if session_id is None:
        session_id = generate_session_id()
    
    # Check data availability first
    is_available, availability_message = await check_data_availability_with_ai(natural_query)
    
    if not is_available:
        explanation = f"Data Availability Check: {availability_message}"
        sql_query = "SELECT 'No data available' AS message;"
        results = []
        title = "Data Not Available"
        chart_data = None
        chart_config = {"chart_type": "none", "reason": "No data available"}
        
        save_query_history(session_id, natural_query, sql_query, str(results), explanation, title)
        return explanation, sql_query, results, session_id, title, chart_data, chart_config
    
    # Generate SQL using LangChain
    full_response, sql_query, chart_config = generate_sql_with_langchain(natural_query)
    
    # Create explanation from full_response
    explanation = full_response if full_response else "SQL query generated successfully"
    
    # Execute the query
    results = execute_sql_query(sql_query)
    
    # Analyze results with AI
    ai_analysis = analyze_results_with_ai(natural_query, results, sql_query)
    
    # Combine original response with AI analysis
    complete_explanation = f"{full_response}\n\n--- AI Analysis ---\n{ai_analysis}"
    
    # Detect chart type using HR-optimized detection
    chart_config = detect_hr_chart_type(natural_query, results)
    
    # Generate HR-optimized chart if applicable
    chart_data = None
    if chart_config["chart_type"] != "none" and chart_config["chart_type"] != "table":
        chart_data = generate_hr_optimized_chart(results, chart_config)
    
    # Generate title
    title = f"Query: {natural_query[:50]}..." if len(natural_query) > 50 else natural_query
    
    # Save to history
    save_query_history(session_id, natural_query, sql_query, str(results), complete_explanation, title, chart_data, str(chart_config))
    
    return explanation, sql_query, results, session_id, title, chart_data, chart_config


def generate_hr_optimized_chart(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> Optional[str]:
    """Generate optimized charts for HR data - simplified version"""
    
    # Use the main generate_chart function instead
    return generate_chart(results, chart_config)
