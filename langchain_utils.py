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
import time # Added for caching

# Import catalog helper
from catalog_helper import get_catalog_context, get_catalog_summary



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
    """Creates and returns an Oracle database connection from pool"""
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    return pool.get_connection()


# Global cache for database schema and sample data
_schema_cache = {}
_schema_cache_ttl = 300  # 5 minutes
_sample_data_cache = {}
_sample_data_cache_ttl = 600  # 10 minutes

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


def create_unified_langchain_pipeline() -> LLMChain:
    """Create unified LangChain pipeline for all AI operations in one call"""
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-5-nano",
        temperature=1.0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create unified prompt template optimized for HR data
    prompt_template = PromptTemplate(
        input_variables=["natural_query", "db_schema", "table_info", "sample_data"],
        template="""You are Aimet, a 14-day-old AI data analyst created by Ahmet Erer. You're based in Kayseri, Turkey, and you love exploring data from anywhere in the world.

You are now working with an HR dataset that contains:
- Employee data (personal info, department, position, salary, hire date, etc.)
- Employee engagement survey data (satisfaction scores, feedback, etc.)
- Recruitment data (applications, interviews, hiring process)
- Training and development data (courses, certifications, skills)

Database Schema:
{db_schema}

Table Information:
{table_info}

Sample Data:
{sample_data}

User Query: {natural_query}

Generate a COMPLETE response including SQL, analysis, and chart recommendations. Format your response as valid JSON:

{{
    "analysis": "Your detailed analysis of what the user is asking for",
    "sql_query": "Your SQL query here (Oracle syntax)",
    "explanation": "Explain how your query works and what it will return",
    "chart_recommendation": {{
        "chart_type": "pie|bar|line|scatter|table|enhanced_dashboard|heatmap|boxplot|histogram|none",
        "title": "Chart title",
        "x_column": "column name for x-axis",
        "y_column": "column name for y-axis",
        "color_column": "column for color coding",
        "reason": "Why this chart type is best for HR data",
        "enhanced_analysis": true/false,
        "suggested_charts": ["list of additional chart types"],
        "hr_insights": "Specific HR insights this visualization will reveal"
    }},
    "data_availability": {{
        "available": true/false,
        "reason": "Why data is available or not",
        "suggestions": "How to modify query if needed"
    }},
    "enhanced_insights": {{
        "main_kpi": "Main HR metric to highlight",
        "distribution_analysis": "Break down by HR categories (department, position, tenure, etc.)",
        "comparison_metrics": "Compare different employee groups",
        "trend_analysis": "Time-based HR insights if applicable",
        "related_metrics": "Additional HR context and recommendations"
    }},
    "hr_specific_recommendations": {{
        "action_items": "What HR actions could be taken based on this data",
        "risk_factors": "Any concerning patterns or trends",
        "opportunities": "Positive insights and improvement areas",
        "benchmarking": "How this compares to industry standards if applicable"
    }}
}}

HR-SPECIFIC CHART RECOMMENDATIONS:
- **Employee Counts**: Use pie charts for department distribution, bar charts for position comparison
- **Salary Analysis**: Use boxplots for salary distribution, bar charts for department salary comparison
- **Engagement Scores**: Use line charts for trends, heatmaps for score distribution across departments
- **Recruitment Metrics**: Use bar charts for application sources, line charts for hiring trends
- **Training Data**: Use bar charts for course completion, line charts for skill development over time
- **Tenure Analysis**: Use histograms for tenure distribution, line charts for retention trends

IMPORTANT RULES:
- Only use SELECT queries (data safety first!)
- Be enthusiastic and detail-oriented
- Always identify yourself as Aimet
- Use Oracle-specific syntax:
  * Use ROWNUM instead of LIMIT or FETCH FIRST
  * Use double quotes around table and column names: "TableName", "ColumnName"
  * For limiting results, use: WHERE ROWNUM <= N
  * Oracle SQL syntax order must be: SELECT, FROM, JOIN, WHERE, GROUP BY, HAVING, ORDER BY
  * ROWNUM must be in WHERE clause BEFORE ORDER BY
  * For top N results with ORDER BY, use subquery: SELECT * FROM (SELECT ... ORDER BY ...) WHERE ROWNUM <= N
- Return ONLY valid JSON, no additional text"""
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
    
    # Create and run unified pipeline
    pipeline = create_unified_langchain_pipeline()
    
    try:
        response = pipeline.run({
            "natural_query": natural_query,
            "db_schema": schema,
            "table_info": table_info,
            "sample_data": sample_data
        })
        
        # Parse JSON response
        import json
        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end != 0:
                json_str = response[json_start:json_end]
                ai_response = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Fallback to old method
            explanation, sql_query, chart_config = generate_sql_with_langchain(natural_query)
            return explanation, sql_query, chart_config, {"available": True, "reason": "Fallback to basic method"}
        
        # Extract components
        explanation = ai_response.get("analysis", "") + "\n\n" + ai_response.get("explanation", "")
        sql_query = ai_response.get("sql_query", "")
        chart_config = ai_response.get("chart_recommendation", {})
        data_availability = ai_response.get("data_availability", {})
        
        return explanation, sql_query, chart_config, data_availability
        
    except Exception as e:
        logger.error(f"Error in unified AI pipeline: {e}")
        # Fallback to old method
        return generate_sql_with_langchain(natural_query)


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
    
    response = pipeline.run({
        "natural_query": natural_query,
        "db_schema": schema,
        "table_info": table_info,
        "sample_data": sample_data,
        "catalog_context": f"\nDATA CATALOG INFORMATION:\n{catalog_summary}\n\nDETAILED CATALOG:\n{catalog_context}"
    })
    
    # Parse SQL query
    sql_parser = SQLQueryParser()
    sql_query = sql_parser.parse(response)
    
    # Generate chart config based on query and results
    chart_config = detect_hr_chart_type(natural_query, [])
    
    return response, sql_query, chart_config


def create_langchain_pipeline():
    """Create LangChain pipeline for SQL generation"""
    
    # Create the language model
    llm = ChatOpenAI(
        model="gpt-5-nano",
        temperature=1,
        max_tokens=2000
    )
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_template("""
    You are an expert SQL developer specializing in HR analytics. 
    Your task is to convert natural language queries into accurate Oracle SQL queries.
    
    {catalog_context}
    
    Database Schema:
    {db_schema}
    
    Table Structure:
    {table_info}
    
    Sample Data:
    {sample_data}
    
    Natural Language Query: {natural_query}
    
    Instructions:
    1. Analyze the natural language query carefully
    2. Use the catalog information to understand data relationships
    3. Generate Oracle-compatible SQL (no semicolon at end)
    4. Focus on HR analytics patterns (employee data, recruitment, training, etc.)
    5. Use appropriate JOINs when multiple tables are needed
    6. Add meaningful column aliases for clarity
    7. Include WHERE clauses for filtering when appropriate
    8. Use GROUP BY and aggregations for analytical queries
    
    Generate the SQL query and provide a brief explanation:
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
        model="gpt-5-nano",
        temperature=1.0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    response = llm.invoke(analysis_prompt)
    return response.content


def detect_chart_type(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect the best chart type for the data with enhanced analysis for simple queries"""
    
    if not results or len(results) == 0:
        return {"chart_type": "none", "reason": "No data available"}
    
    # Analyze data structure
    sample_row = results[0]
    columns = list(sample_row.keys())
    
    # Check if this is a simple count/aggregation query that could benefit from enhanced analysis
    is_simple_query = False
    enhanced_analysis_needed = False
    
    # Detect simple queries like "kaç çalışan var", "how many employees", etc.
    simple_query_patterns = [
        "kaç", "how many", "count", "total", "number of", "adet", "tane",
        "çalışan", "employee", "müşteri", "customer", "ürün", "product",
        "toplam", "sum", "amount", "quantity"
    ]
    
    query_lower = query.lower()
    if any(pattern in query_lower for pattern in simple_query_patterns):
        is_simple_query = True
        # If result is just a single number, suggest enhanced analysis
        if len(results) == 1 and len(columns) == 1:
            enhanced_analysis_needed = True
    
    # Create enhanced chart detection prompt
    chart_prompt = f"""Analyze this data and suggest the best chart type with enhanced analysis:

Query: {query}
Columns: {columns}
Sample data: {results[:3]}
Is simple count query: {is_simple_query}
Enhanced analysis needed: {enhanced_analysis_needed}

Based on the query and data structure, suggest the most appropriate visualization. Consider:

FOR SIMPLE COUNT QUERIES (like "kaç çalışan var"):
- If result is just a number, suggest MULTIPLE charts to provide context:
  1. Main KPI display (big number with context)
  2. Distribution chart (pie/bar) if related data exists
  3. Comparison chart (bar) for categories
  4. Trend chart if time data exists
  5. Regional/geographic chart if location data exists

FOR REGULAR QUERIES:
- If query asks for "distribution" or "percentage" → pie chart
- If query asks for "comparison" or "ranking" → bar chart  
- If query asks for "trend" or "over time" → line chart
- If query asks for "correlation" or "relationship" → scatter plot
- If query asks for "details" or "list" → table

Return JSON with:
{{
    "chart_type": "pie|bar|line|scatter|table|enhanced_dashboard|none",
    "title": "Chart title",
    "x_column": "column name for x-axis",
    "y_column": "column name for y-axis", 
    "color_column": "column for color coding",
    "reason": "Why this chart type is best",
    "enhanced_analysis": true/false,
    "suggested_charts": ["list of additional chart types to create"]
}}

Only return valid JSON."""

    llm = ChatOpenAI(
        model="gpt-5-nano",
        temperature=1.0,
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


def detect_hr_chart_type(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect the best chart type for HR data with enhanced analysis"""
    
    if not results or len(results) == 0:
        return {"chart_type": "none", "reason": "No data available"}
    
    # Analyze data structure
    sample_row = results[0]
    columns = list(sample_row.keys())
    
    # HR-specific chart detection patterns
    hr_chart_patterns = {
        "employee_count": ["count", "number", "how many", "kaç", "adet", "total employees"],
        "salary_analysis": ["salary", "wage", "compensation", "pay", "maas", "ücret"],
        "department_distribution": ["department", "division", "team", "bölüm", "departman"],
        "engagement_scores": ["engagement", "satisfaction", "happiness", "score", "rating", "memnuniyet"],
        "tenure_analysis": ["tenure", "experience", "years", "hire date", "start date", "deneyim"],
        "training_metrics": ["training", "course", "certification", "skill", "eğitim", "kurs"],
        "recruitment_data": ["recruitment", "hiring", "application", "interview", "işe alım", "mülakat"],
        "turnover_analysis": ["turnover", "retention", "attrition", "leave", "ayrılma", "kalma"]
    }
    
    query_lower = query.lower()
    
    # Determine chart type based on HR patterns
    chart_type = "table"  # default
    reason = "Default table view for HR data"
    
    # Check for specific HR patterns
    if any(pattern in query_lower for pattern in hr_chart_patterns["employee_count"]):
        if len(columns) == 1:
            chart_type = "enhanced_dashboard"
            reason = "Employee count query - showing comprehensive HR dashboard"
        elif len(columns) == 2:
            chart_type = "bar"
            reason = "Employee count by category - bar chart shows clear comparison"
        else:
            chart_type = "pie"
            reason = "Employee distribution - pie chart shows proportions clearly"
    
    elif any(pattern in query_lower for pattern in hr_chart_patterns["salary_analysis"]):
        if len(columns) == 2:
            chart_type = "boxplot"
            reason = "Salary distribution - boxplot shows median, quartiles, and outliers"
        else:
            chart_type = "histogram"
            reason = "Salary distribution - histogram shows frequency distribution"
    
    elif any(pattern in query_lower for pattern in hr_chart_patterns["department_distribution"]):
        chart_type = "pie"
        reason = "Department distribution - pie chart shows proportions clearly"
    
    elif any(pattern in query_lower for pattern in hr_chart_patterns["engagement_scores"]):
        if len(columns) >= 3:
            chart_type = "heatmap"
            reason = "Engagement scores by multiple factors - heatmap shows patterns clearly"
        else:
            chart_type = "bar"
            reason = "Engagement scores - bar chart shows comparison across groups"
    
    elif any(pattern in query_lower for pattern in hr_chart_patterns["tenure_analysis"]):
        chart_type = "histogram"
        reason = "Tenure distribution - histogram shows frequency distribution over time"
    
    elif any(pattern in query_lower for pattern in hr_chart_patterns["training_metrics"]):
        chart_type = "bar"
        reason = "Training metrics - bar chart shows completion rates and comparisons"
    
    elif any(pattern in query_lower for pattern in hr_chart_patterns["recruitment_data"]):
        chart_type = "line"
        reason = "Recruitment trends - line chart shows changes over time"
    
    elif any(pattern in query_lower for pattern in hr_chart_patterns["turnover_analysis"]):
        chart_type = "line"
        reason = "Turnover trends - line chart shows changes over time"
    
    # Enhanced analysis for simple count queries
    enhanced_analysis = False
    if any(pattern in query_lower for pattern in ["kaç", "how many", "count", "total", "number of"]):
        enhanced_analysis = True
    
    # Suggest additional charts for comprehensive HR analysis
    suggested_charts = []
    if chart_type == "bar":
        suggested_charts.extend(["pie", "enhanced_dashboard"])
    elif chart_type == "pie":
        suggested_charts.extend(["bar", "enhanced_dashboard"])
    elif chart_type == "line":
        suggested_charts.extend(["bar", "enhanced_dashboard"])
    
    return {
        "chart_type": chart_type,
        "title": f"HR Analytics: {query[:50]}...",
        "x_column": columns[0] if len(columns) > 0 else None,
        "y_column": columns[1] if len(columns) > 1 else None,
        "color_column": columns[2] if len(columns) > 2 else None,
        "reason": reason,
        "enhanced_analysis": enhanced_analysis,
        "suggested_charts": suggested_charts,
        "hr_insights": f"This visualization will help HR professionals understand {chart_type} patterns in the data"
    }


def generate_chart(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> Optional[str]:
    """Generate chart based on configuration and return as base64 encoded image"""
    
    if not results or len(results) == 0:
        return None
    
    try:
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        # Check DataFrame dimensions
        if df.empty:
            logger.warning("DataFrame is empty")
            return None
        
        if len(df) < 2 and chart_config["chart_type"] in ["bar", "pie", "line"]:
            logger.warning(f"DataFrame has only {len(df)} row(s), creating simple indicator")
            return generate_single_value_chart(df, chart_config)
        
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
            
        elif chart_config["chart_type"] == "enhanced_dashboard":
            # Enhanced dashboard for simple queries - create multiple charts
            return generate_enhanced_dashboard(results, chart_config)
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


def generate_enhanced_dashboard(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> str:
    """Generate enhanced dashboard for simple queries with multiple visualizations"""
    
    try:
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        # Create a comprehensive dashboard with multiple charts
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Main KPI', 'Distribution', 'Comparison', 'Details'),
            specs=[[{"type": "indicator"}, {"type": "pie"}],
                   [{"type": "bar"}, {"type": "table"}]]
        )
        
        # Main KPI (big number display)
        if len(results) == 1 and len(df.columns) == 1:
            main_value = results[0][list(df.columns)[0]]
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=main_value,
                    title={"text": "Total Count"},
                    delta={"reference": 0},
                    number={"font": {"size": 40}}
                ),
                row=1, col=1
            )
        
        # Distribution chart (pie chart)
        if len(df.columns) >= 2:
            try:
                # Try to create pie chart from first two columns
                fig.add_trace(
                    go.Pie(
                        labels=df.iloc[:, 0],
                        values=df.iloc[:, 1] if len(df.columns) > 1 else [1] * len(df),
                        name="Distribution"
                    ),
                    row=1, col=2
                )
            except:
                pass
        
        # Comparison chart (bar chart)
        if len(df.columns) >= 2:
            try:
                fig.add_trace(
                    go.Bar(
                        x=df.iloc[:, 0],
                        y=df.iloc[:, 1] if len(df.columns) > 1 else [1] * len(df),
                        name="Comparison"
                    ),
                    row=2, col=1
                )
            except:
                pass
        
        # Details table
        fig.add_trace(
            go.Table(
                header=dict(values=list(df.columns)),
                cells=dict(values=[df[col] for col in df.columns])
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            title_text="Enhanced Dashboard Analysis",
            showlegend=False
        )
        
        # Convert to PNG
        try:
            img_bytes = fig.to_image(format="png", engine="kaleido")
            img_base64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.warning(f"Kaleido export failed: {e}, falling back to HTML")
            # Fallback to HTML
            html_string = fig.to_html(include_plotlyjs=False, full_html=False)
            dashboard_info = {
                "chart_type": "enhanced_dashboard",
                "title": "Enhanced Dashboard Analysis",
                "data_points": len(results),
                "columns": list(df.columns),
                "html": html_string,
                "fallback": True,
                "enhanced_analysis": True
            }
            return json.dumps(dashboard_info)
        
    except Exception as e:
        logger.error(f"Error generating enhanced dashboard: {e}")
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
        model="gpt-5-nano",
        temperature=1.0,
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
    full_response, sql_query, _ = generate_sql_with_langchain(natural_query)
    
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
    
    return complete_explanation, sql_query, results, session_id, title, chart_data, chart_config


def generate_hr_optimized_chart(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> Optional[str]:
    """Generate HR-optimized charts with enhanced visualizations"""
    
    if not results or len(results) == 0:
        logger.warning("No results to generate chart from")
        return None
    
    try:
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        # Check DataFrame dimensions
        if df.empty:
            logger.warning("DataFrame is empty")
            return None
        
        if len(df) < 2:
            logger.warning(f"DataFrame has only {len(df)} row(s), chart generation may not be optimal")
            # For single row, create a simple indicator chart
            if chart_config.get("chart_type") in ["bar", "pie"]:
                return generate_single_value_chart(df, chart_config)
        
        # HR-specific chart generation
        if chart_config["chart_type"] == "heatmap":
            return generate_hr_heatmap(df, chart_config)
        elif chart_config["chart_type"] == "boxplot":
            return generate_hr_boxplot(df, chart_config)
        elif chart_config["chart_type"] == "histogram":
            return generate_hr_histogram(df, chart_config)
        elif chart_config["chart_type"] == "enhanced_dashboard":
            return generate_hr_enhanced_dashboard(df, chart_config)
        else:
            # Use existing chart generation for other types
            return generate_chart(results, chart_config)
        
    except Exception as e:
        logger.error(f"Error generating HR chart: {e}")
        return None


def generate_single_value_chart(df: pd.DataFrame, chart_config: Dict[str, Any]) -> str:
    """Generate chart for single value results (e.g., total count)"""
    
    try:
        # Get the first row
        row = df.iloc[0]
        
        # Create a simple indicator chart
        fig = go.Figure()
        
        # Add indicator
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=row.get(chart_config.get("y_column", df.columns[1]), 0),
            title={"text": chart_config.get("title", "Value")},
            delta={"reference": 0},
            number={"font": {"size": 40}}
        ))
        
        # Update layout
        fig.update_layout(
            title=chart_config.get("title", "Single Value Chart"),
            height=400,
            showlegend=False
        )
        
        # Convert to PNG
        try:
            img_bytes = fig.to_image(format="png", engine="kaleido")
            img_base64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.warning(f"Kaleido export failed: {e}, falling back to HTML")
            # Fallback to HTML
            html_string = fig.to_html(include_plotlyjs=False, full_html=False)
            chart_info = {
                "chart_type": "indicator",
                "title": chart_config.get("title", "Single Value Chart"),
                "data_points": len(df),
                "columns": list(df.columns),
                "html": html_string,
                "fallback": True,
                "single_value": True
            }
            return json.dumps(chart_info)
            
    except Exception as e:
        logger.error(f"Error generating single value chart: {e}")
        return None


def generate_hr_heatmap(df: pd.DataFrame, chart_config: Dict[str, Any]) -> str:
    """Generate heatmap for HR data (e.g., engagement scores by department)"""
    
    try:
        # Create pivot table for heatmap
        if len(df.columns) >= 3:
            pivot_data = df.pivot_table(
                values=chart_config.get("y_column", df.columns[2]),
                index=chart_config.get("x_column", df.columns[0]),
                columns=chart_config.get("color_column", df.columns[1]),
                aggfunc='mean'
            )
            
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='RdYlGn',
                text=pivot_data.values.round(2),
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title=chart_config.get("title", "HR Data Heatmap"),
                xaxis_title=chart_config.get("color_column", "Category"),
                yaxis_title=chart_config.get("x_column", "Group"),
                height=500
            )
            
            # Convert to PNG
            img_bytes = fig.to_image(format="png", engine="kaleido")
            img_base64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{img_base64}"
            
    except Exception as e:
        logger.error(f"Error generating HR heatmap: {e}")
        return None


def generate_hr_boxplot(df: pd.DataFrame, chart_config: Dict[str, Any]) -> str:
    """Generate boxplot for HR data (e.g., salary distribution by department)"""
    
    try:
        fig = go.Figure()
        
        # Group by category and create boxplot
        categories = df[chart_config.get("x_column", df.columns[0])].unique()
        
        for category in categories:
            category_data = df[df[chart_config.get("x_column", df.columns[0])] == category]
            values = category_data[chart_config.get("y_column", df.columns[1])]
            
            fig.add_trace(go.Box(
                y=values,
                name=str(category),
                boxpoints='outliers',
                jitter=0.3,
                pointpos=-1.8
            ))
        
        fig.update_layout(
            title=chart_config.get("title", "HR Data Distribution"),
            xaxis_title=chart_config.get("x_column", "Category"),
            yaxis_title=chart_config.get("y_column", "Value"),
            height=500,
            showlegend=True
        )
        
        # Convert to PNG
        img_bytes = fig.to_image(format="png", engine="kaleido")
        img_base64 = base64.b64encode(img_bytes).decode()
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        logger.error(f"Error generating HR boxplot: {e}")
        return None


def generate_hr_histogram(df: pd.DataFrame, chart_config: Dict[str, Any]) -> str:
    """Generate histogram for HR data (e.g., tenure distribution)"""
    
    try:
        values = df[chart_config.get("y_column", df.columns[1])]
        
        fig = go.Figure(data=[go.Histogram(
            x=values,
            nbinsx=20,
            name="Distribution",
            marker_color='lightblue',
            opacity=0.7
        )])
        
        fig.update_layout(
            title=chart_config.get("title", "HR Data Distribution"),
            xaxis_title=chart_config.get("y_column", "Value"),
            yaxis_title="Frequency",
            height=500,
            bargap=0.1
        )
        
        # Convert to PNG
        img_bytes = fig.to_image(format="png", engine="kaleido")
        img_base64 = base64.b64encode(img_bytes).decode()
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        logger.error(f"Error generating HR histogram: {e}")
        return None


def generate_hr_enhanced_dashboard(df: pd.DataFrame, chart_config: Dict[str, Any]) -> str:
    """Generate enhanced HR dashboard with multiple visualizations"""
    
    try:
        # Create subplots for HR dashboard
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Employee Overview', 'Department Distribution', 'Trend Analysis', 'Key Metrics'),
            specs=[[{"type": "indicator"}, {"type": "pie"}],
                   [{"type": "bar"}, {"type": "table"}]]
        )
        
        # Employee Overview (KPI)
        if len(df.columns) >= 1:
            main_value = len(df)  # Total count
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=main_value,
                    title={"text": "Total Employees"},
                    delta={"reference": 0},
                    number={"font": {"size": 40}}
                ),
                row=1, col=1
            )
        
        # Department Distribution (pie chart)
        if len(df.columns) >= 2:
            try:
                dept_counts = df[df.columns[0]].value_counts()
                fig.add_trace(
                    go.Pie(
                        labels=dept_counts.index,
                        values=dept_counts.values,
                        name="Department Distribution"
                    ),
                    row=1, col=2
                )
            except:
                pass
        
        # Trend Analysis (bar chart)
        if len(df.columns) >= 2:
            try:
                # Try to show some trend or comparison
                top_values = df[df.columns[0]].value_counts().head(5)
                fig.add_trace(
                    go.Bar(
                        x=top_values.index,
                        y=top_values.values,
                        name="Top Categories"
                    ),
                    row=2, col=1
                )
            except:
                pass
        
        # Key Metrics Table
        fig.add_trace(
            go.Table(
                header=dict(values=list(df.columns)),
                cells=dict(values=[df[col] for col in df.columns])
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            title_text="HR Analytics Dashboard",
            showlegend=False
        )
        
        # Convert to PNG
        try:
            img_bytes = fig.to_image(format="png", engine="kaleido")
            img_base64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.warning(f"Kaleido export failed: {e}, falling back to HTML")
            # Fallback to HTML
            html_string = fig.to_html(include_plotlyjs=False, full_html=False)
            dashboard_info = {
                "chart_type": "enhanced_dashboard",
                "title": "HR Analytics Dashboard",
                "data_points": len(df),
                "columns": list(df.columns),
                "html": html_string,
                "fallback": True,
                "enhanced_analysis": True
            }
            return json.dumps(dashboard_info)
        
    except Exception as e:
        logger.error(f"Error generating HR enhanced dashboard: {e}")
        return None
