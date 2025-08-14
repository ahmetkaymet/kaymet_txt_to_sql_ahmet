"""
LangChain-based utility functions for database operations and SQL query generation
This module provides functionality for:
- LangChain pipeline for natural language to SQL conversion
- AI-powered result analysis and commentary
- Chart generation capabilities
- Data availability checking with AI insights
"""

import os
import re
import json
import logging
import datetime
from config.oracle_config import OracleConnection
from typing import List, Dict, Any, Tuple, Optional, Union
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import io
import base64

# LangChain imports
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

logger = logging.getLogger(__name__)


class SQLQueryParser(BaseOutputParser):
    """Custom parser for SQL query extraction"""
    
    def parse(self, text: str) -> str:
        """Extract SQL query from AI response"""
        # Extract SQL query from markdown code blocks
        sql_start = text.find("```sql")
        if sql_start != -1:
            sql_end = text.find("```", sql_start + 6)
            if sql_end != -1:
                sql_query = text[sql_start + 6:sql_end].strip()
            else:
                # Fallback if closing code block not found
                lines = text.strip().split('\n')
                sql_query = next((line for line in lines if line.upper().startswith("SELECT")), "SELECT * FROM Stores LIMIT 5")
        else:
            # Fallback if no code block found
            lines = text.strip().split('\n')
            sql_query = next((line for line in lines if line.upper().startswith("SELECT")), "SELECT * FROM Stores LIMIT 5")
        
        # Clean up SQL query - Oracle DB doesn't need semicolons
        if ";" in sql_query:
            sql_query = sql_query.split(";")[0].strip()
        
        # Remove any trailing semicolon for Oracle DB compatibility
        sql_query = sql_query.strip().rstrip(";")
        
        return sql_query


class ChartTypeParser(BaseOutputParser):
    """Parser for chart type detection"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse chart type and configuration from AI response"""
        try:
            # Try to parse as JSON first
            if "{" in text and "}" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        # Default chart configuration
        return {
            "chart_type": "table",
            "title": "Data Visualization",
            "x_column": None,
            "y_column": None,
            "color_column": None
        }


def get_db_connection():
    """Creates and returns an Oracle database connection"""
    db = OracleConnection()
    return db.connect()


def get_db_schema() -> str:
    """Retrieves database schema with table and column descriptions"""
    with get_db_connection() as conn:
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


def create_langchain_pipeline() -> LLMChain:
    """Create LangChain pipeline for SQL generation"""
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create prompt template
    prompt_template = PromptTemplate(
        input_variables=["natural_query", "db_schema", "table_info", "sample_data"],
        template="""You are Aimet, a 14-day-old AI data analyst created by Ahmet Erer. You're based in Kayseri, Turkey, and you love exploring data from anywhere in the world.

Database Schema:
{db_schema}

Table Information:
{table_info}

Sample Data:
{sample_data}

User Query: {natural_query}

Generate a SQL query and provide a detailed explanation. Format your response as:

**Analysis:**
[Your detailed analysis of what the user is asking for]

**SQL Query:**
```sql
[Your SQL query here]
```

**Explanation:**
[Explain how your query works and what it will return]

**Chart Recommendation:**
[Suggest what type of chart would be best for this data, if applicable]

Remember:
- Only use SELECT queries (data safety first!)
- When asked about cities like New York, use State='NY'
- Be enthusiastic and detail-oriented
- Always identify yourself as Aimet
- IMPORTANT: This is an Oracle database, so use Oracle-specific syntax:
  * Use ROWNUM instead of LIMIT or FETCH FIRST
  * Use double quotes around table and column names: "TableName", "ColumnName"
  * For limiting results, use: WHERE ROWNUM <= N
  * Oracle doesn't support LIMIT or FETCH FIRST syntax
  * IMPORTANT: Oracle SQL syntax order must be: SELECT, FROM, JOIN, WHERE, GROUP BY, HAVING, ORDER BY
  * ROWNUM must be in WHERE clause BEFORE ORDER BY
  * For top N results with ORDER BY, use subquery: SELECT * FROM (SELECT ... ORDER BY ...) WHERE ROWNUM <= N"""
    )
    
    # Create chain
    chain = LLMChain(llm=llm, prompt=prompt_template)
    return chain


def generate_sql_with_langchain(natural_query: str) -> Tuple[str, str, str]:
    """Generate SQL query using LangChain pipeline"""
    
    # Get database context
    schema = get_db_schema()
    
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
    
    # Create and run pipeline
    pipeline = create_langchain_pipeline()
    
    response = pipeline.run({
        "natural_query": natural_query,
        "db_schema": schema,
        "table_info": table_info,
        "sample_data": sample_data
    })
    
    # Parse SQL query
    sql_parser = SQLQueryParser()
    sql_query = sql_parser.parse(response)
    
    return response, sql_query, "langchain_generated"


def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """Executes SQL query and returns results as a list of dictionaries"""
    query = query.strip()
    logger.info(f"Executing query: {query}")

    # Security checks
    dangerous_commands = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(cmd in query.upper() for cmd in dangerous_commands):
        logger.warning(f"Dangerous SQL command detected: {query}")
        return [{"warning": "Data modification operations are not allowed."}]
    
    with get_db_connection() as conn:
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
            logger.error(f"Error executing query: {str(e)}")
            return [{"error": f"Error: {str(e)}"}]


def analyze_results_with_ai(query: str, results: List[Dict[str, Any]], sql_query: str) -> str:
    """Use AI to analyze query results and provide insights"""
    
    if not results or len(results) == 0:
        return "No data found for this query. The database doesn't contain any records matching your criteria."
    
    # Convert results to readable format
    results_summary = f"Query returned {len(results)} rows of data."
    if len(results) > 0:
        sample_data = "\nSample results:\n"
        for i, row in enumerate(results[:3]):  # Show first 3 rows
            sample_data += f"Row {i+1}: {', '.join([f'{k}={v}' for k, v in row.items()])}\n"
        results_summary += sample_data
    
    # Create AI analysis prompt
    analysis_prompt = f"""As Aimet, analyze these query results and provide natural language insights:

Original Query: {query}
SQL Query: {sql_query}
Results: {results_summary}

Provide a natural, conversational analysis that:
1. Explains what the results mean in plain language
2. Highlights key findings or patterns
3. Suggests what insights can be drawn
4. Mentions the number of results found
5. Uses your enthusiastic personality

Keep it conversational and helpful!"""

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    response = llm.invoke(analysis_prompt)
    return response.content


def detect_chart_type(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect the best chart type for the data"""
    
    if not results or len(results) == 0:
        return {"chart_type": "none", "reason": "No data available"}
    
    # Analyze data structure
    sample_row = results[0]
    columns = list(sample_row.keys())
    
    # Create chart detection prompt
    chart_prompt = f"""Analyze this data and suggest the best chart type:

Query: {query}
Columns: {columns}
Sample data: {results[:3]}

Based on the query and data structure, suggest the most appropriate visualization. Consider:
- If query asks for "distribution" or "percentage" → pie chart
- If query asks for "comparison" or "ranking" → bar chart  
- If query asks for "trend" or "over time" → line chart
- If query asks for "correlation" or "relationship" → scatter plot
- If query asks for "details" or "list" → table

Return JSON with:
{{
    "chart_type": "pie|bar|line|scatter|table|none",
    "title": "Chart title",
    "x_column": "column name for x-axis",
    "y_column": "column name for y-axis", 
    "color_column": "column for color coding",
    "reason": "Why this chart type is best"
}}

Only return valid JSON."""

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    try:
        response = llm.invoke(chart_prompt)
        chart_parser = ChartTypeParser()
        result = chart_parser.parse(response.content)
        
        # Validate and improve chart configuration
        if result.get("chart_type") == "bar" and not result.get("y_column"):
            # For bar charts, try to find numeric columns
            numeric_cols = [col for col in columns if any(isinstance(row.get(col), (int, float)) for row in results)]
            if numeric_cols:
                result["y_column"] = numeric_cols[0]
        
        if result.get("chart_type") == "pie" and not result.get("y_column"):
            # For pie charts, try to find numeric columns
            numeric_cols = [col for col in columns if any(isinstance(row.get(col), (int, float)) for row in results)]
            if numeric_cols:
                result["y_column"] = numeric_cols[0]
        
        return result
    except Exception as e:
        logger.error(f"Error detecting chart type: {e}")
        return {"chart_type": "table", "title": "Data Table", "reason": "Default fallback"}


def generate_chart(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> Optional[str]:
    """Generate chart based on configuration and return as base64 encoded image"""
    
    if not results or len(results) == 0:
        return None
    
    try:
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        if chart_config["chart_type"] == "pie":
            # Pie chart
            fig = px.pie(
                df, 
                values=chart_config.get("y_column", df.columns[1]), 
                names=chart_config.get("x_column", df.columns[0]),
                title=chart_config.get("title", "Data Distribution")
            )
            
        elif chart_config["chart_type"] == "bar":
            # Bar chart
            fig = px.bar(
                df,
                x=chart_config.get("x_column", df.columns[0]),
                y=chart_config.get("y_column", df.columns[1]),
                title=chart_config.get("title", "Data Comparison"),
                color=chart_config.get("color_column")
            )
            
        elif chart_config["chart_type"] == "line":
            # Line chart
            fig = px.line(
                df,
                x=chart_config.get("x_column", df.columns[0]),
                y=chart_config.get("y_column", df.columns[1]),
                title=chart_config.get("title", "Data Trend"),
                color=chart_config.get("color_column")
            )
            
        elif chart_config["chart_type"] == "scatter":
            # Scatter plot
            fig = px.scatter(
                df,
                x=chart_config.get("x_column", df.columns[0]),
                y=chart_config.get("y_column", df.columns[1]),
                title=chart_config.get("title", "Data Correlation"),
                color=chart_config.get("color_column")
            )
            
        else:
            # Default to table view
            return None
        
        # Convert to PNG using kaleido
        try:
            img_bytes = fig.to_image(format="png", engine="kaleido")
            img_base64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.warning(f"Kaleido export failed: {e}, falling back to HTML")
            # Fallback to HTML
            html_string = fig.to_html(include_plotlyjs=False, full_html=False)
            chart_info = {
                "chart_type": chart_config["chart_type"],
                "title": chart_config.get("title", "Data Chart"),
                "data_points": len(results),
                "columns": list(df.columns),
                "html": html_string,
                "fallback": True
            }
            return json.dumps(chart_info)
        
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None


async def check_data_availability_with_ai(query: str) -> Tuple[bool, str]:
    """Use AI to check if data is available for the query"""
    
    schema = get_db_schema()
    
    availability_prompt = f"""Analyze this query to determine if data exists in the database:

Query: {query}

Database Schema:
{schema}

Determine if this query can return meaningful data. Consider:
1. Are the requested tables present?
2. Do the columns exist?
3. Is the data type appropriate?
4. Are there any obvious data access issues?

Return JSON with:
{{
    "data_available": true/false,
    "reason": "Detailed explanation",
    "suggestions": "How to modify query if needed"
}}

Only return valid JSON."""

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    try:
        response = llm.invoke(availability_prompt)
        
        # Parse response
        if "{" in response.content and "}" in response.content:
            json_start = response.content.find("{")
            json_end = response.content.rfind("}") + 1
            json_str = response.content[json_start:json_end]
            result = json.loads(json_str)
            
            return result.get("data_available", False), result.get("reason", "Unable to determine")
        else:
            return False, "AI response format error"
            
    except Exception as e:
        logger.error(f"Error checking data availability: {e}")
        return False, f"Error during availability check: {str(e)}"


async def process_natural_query_langchain(natural_query: str, session_id: str = None) -> Tuple[str, str, List[Dict[str, Any]], str, str, Optional[str], Dict[str, Any]]:
    """Process natural language query using LangChain pipeline"""
    
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
    full_response, sql_query, _ = generate_sql_with_langchain(natural_query)
    
    # Execute the query
    results = execute_sql_query(sql_query)
    
    # Analyze results with AI
    ai_analysis = analyze_results_with_ai(natural_query, results, sql_query)
    
    # Combine original response with AI analysis
    complete_explanation = f"{full_response}\n\n--- AI Analysis ---\n{ai_analysis}"
    
    # Detect chart type
    chart_config = detect_chart_type(natural_query, results)
    
    # Generate chart if applicable
    chart_data = None
    if chart_config["chart_type"] != "none" and chart_config["chart_type"] != "table":
        chart_data = generate_chart(results, chart_config)
    
    # Generate title
    title = f"Query: {natural_query[:50]}..." if len(natural_query) > 50 else natural_query
    
    # Save to history
    save_query_history(session_id, natural_query, sql_query, str(results), complete_explanation, title, chart_data, str(chart_config))
    
    return complete_explanation, sql_query, results, session_id, title, chart_data, chart_config
