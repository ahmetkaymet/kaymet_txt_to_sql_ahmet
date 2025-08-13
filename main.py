"""
FastAPI application for natural language to SQL conversion using LangChain
This API provides endpoints:
- /generate-sql: Converts natural language queries to SQL using LangChain
- /execute-sql: Executes SQL queries against the database
- /sessions: Returns all query sessions
- /chart: Generates charts for query results
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_utils import (
    process_natural_query_langchain, 
    execute_sql_query,
    check_data_availability_with_ai,
    generate_chart,
    detect_chart_type
)
from query_history import get_all_sessions, save_query_history
from datetime import datetime
from openai import OpenAI
import sqlite3

"""
Logging Configuration
--------------------
Configures application-wide logging with the following features:
- Log Level: INFO (captures general flow, warnings, and errors)
- Format: Timestamp - Logger Name - Log Level - Message
- Usage: Tracks API requests, responses, and error states
- Purpose: Enables monitoring, debugging, and audit trail
"""
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Txt to SQL API with LangChain",
    description="API for converting natural language to SQL queries using LangChain pipeline",
    version="2.0.0"
)

# CORS ayarlarını en başa al
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Allow both localhost variations
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods during development
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers
)

# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Request headers: {request.headers}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint that returns API information"""
    logger.info("Root endpoint called")
    return {
        "name": "Text to SQL API with LangChain",
        "version": "2.0.0",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "This information"},
            {"path": "/sessions", "method": "GET", "description": "Get all query sessions"},
            {"path": "/generate-sql", "method": "POST", "description": "Generate SQL from natural language using LangChain"},
            {"path": "/execute-sql", "method": "POST", "description": "Execute natural language query with LangChain"},
            {"path": "/check-and-execute", "method": "POST", "description": "Check data availability and execute query"},
            {"path": "/chart", "method": "POST", "description": "Generate charts for query results"},
        ]
    }

class QueryRequest(BaseModel):
    """Request model for query endpoints"""
    query: str
    session_id: str | None = None

class GenerateSQLResponse(BaseModel):
    """Response model for generate-sql endpoint """
    explanation: str
    sql_query: str

class ExecuteSQLResponse(BaseModel):
    """Response model for execute-sql endpoint with LangChain enhancements

    This model contains the complete response including the explanation,
    the SQL query, its execution results, and chart information.

    Attributes:
        explanation (str): Detailed explanation of the SQL query generation process with AI analysis
        sql_query (str): The generated and executed SQL query
        results (List[Dict[str, Any]]): Query execution results, where each dictionary
            represents a row with column names as keys and cell values as values.
        session_id (str): The ID of the query session
        title (str): The title of the query
        chart_data (Optional[str]): Base64 encoded chart image if applicable
        chart_config (Dict[str, Any]): Chart configuration and metadata
    """
    explanation: str
    sql_query: str
    results: List[Dict[str, Any]]
    session_id: str
    title: str
    chart_data: Optional[str] = None
    chart_config: Dict[str, Any] = {}

class Session(BaseModel):
    """Model for a query session"""
    id: str
    queries: List[Dict[str, Any]]

class ChartRequest(BaseModel):
    """Request model for chart generation"""
    query: str
    chart_type: Optional[str] = None
    x_column: Optional[str] = None
    y_column: Optional[str] = None

@app.get("/sessions")
async def get_sessions():
    """Get all query sessions from SQLite database"""
    try:
        from query_history import get_all_sessions
        # Doğrudan query_history modülünün fonksiyonunu kullanalım
        sessions = get_all_sessions()
        
        # Logla ve cevap döndür
        logger.info(f"Returned {len(sessions)} sessions with total {sum(len(s['queries']) for s in sessions)} queries")
        return JSONResponse(content=sessions)
    except Exception as e:
        logger.error(f"Error getting sessions: {e}", exc_info=True)
        return JSONResponse(content=[])

@app.post("/generate-sql", response_model=GenerateSQLResponse)
async def generate_sql(request: QueryRequest) -> GenerateSQLResponse:
    """Generate SQL query from natural language input using LangChain

    This endpoint takes a natural language query and converts it to SQL using LangChain pipeline.
    It returns both an explanation of the conversion process and the resulting SQL query.

    Args:
        request (QueryRequest): Request object containing the natural language query

    Returns:
        GenerateSQLResponse: Object containing:
            - explanation: Detailed explanation of the SQL generation process
            - sql_query: The generated SQL query

    Example:
        Request: {"query": "Show all stores in New York"}
        Response: {
            "explanation": "Converting query for NY stores...",
            "sql_query": "SELECT * FROM Stores WHERE State = 'NY'"
        }
    """
    try:
        # Use LangChain pipeline for SQL generation
        from langchain_utils import generate_sql_with_langchain
        explanation, sql_query, _ = generate_sql_with_langchain(request.query)
        return GenerateSQLResponse(explanation=explanation, sql_query=sql_query)
    except Exception as e:
        logger.error(f"Error generating SQL with LangChain: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating SQL: {str(e)}")

@app.post("/execute-sql", response_model=ExecuteSQLResponse)
async def execute_sql(request: QueryRequest) -> ExecuteSQLResponse:
    """Generate and execute SQL query from natural language input using LangChain"""
    logger.info(f"Executing SQL for query: {request.query}")
    try:
        # Use LangChain pipeline for complete processing
        explanation, sql_query, results, session_id, title, chart_data, chart_config = await process_natural_query_langchain(
            request.query, 
            request.session_id
        )
        
        # Save to query history
        from query_history import save_query_history
        save_query_history(
            session_id=session_id,
            natural_query=request.query,
            sql_query=sql_query,
            query_result=str(results),
            explanation=explanation,
            title=title,
            chart_data=chart_data,
            chart_config=str(chart_config)
        )
        
        # Limit the number of results returned
        if results and len(results) > 100:
            results = results[:100]
            explanation += "\n(Note: Results limited to first 100 rows for better performance)"
        
        response = ExecuteSQLResponse(
            explanation=explanation,
            sql_query=sql_query,
            results=results,
            session_id=session_id,
            title=title,
            chart_data=chart_data,
            chart_config=chart_config
        )
        
        logger.info(f"Query executed successfully with LangChain, session_id: {session_id}")
        return response
    except Exception as e:
        logger.error(f"Error executing query with LangChain: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")

@app.post("/chart", response_model=Dict[str, Any])
async def generate_chart_endpoint(request: ChartRequest) -> Dict[str, Any]:
    """Generate chart for query results"""
    logger.info(f"Generating chart for query: {request.query}")
    
    try:
        # First execute the query to get results
        explanation, sql_query, results, session_id, title, _, _ = await process_natural_query_langchain(
            request.query
        )
        
        if not results or len(results) == 0:
            return {
                "error": "No data available for chart generation",
                "message": "The query returned no results to visualize."
            }
        
        # Detect chart type if not specified
        if not request.chart_type:
            chart_config = detect_chart_type(request.query, results)
        else:
            chart_config = {
                "chart_type": request.chart_type,
                "x_column": request.x_column,
                "y_column": request.y_column,
                "title": f"Chart for: {request.query}"
            }
        
        # Generate chart
        chart_data = generate_chart(results, chart_config)
        
        if chart_data:
            return {
                "success": True,
                "chart_data": chart_data,
                "chart_config": chart_config,
                "results_count": len(results),
                "message": f"Chart generated successfully for {len(results)} results"
            }
        else:
            return {
                "success": False,
                "message": "Unable to generate chart for this data type",
                "chart_config": chart_config
            }
            
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")

# Simple in-memory cache
query_cache = {}

def get_cached_result(key: str) -> Optional[ExecuteSQLResponse]:
    """Get cached query result if it exists and is not expired"""
    if key in query_cache:
        timestamp, result = query_cache[key]
        # Cache expires after 5 minutes
        if datetime.now().timestamp() - timestamp < 300:
            return result
        else:
            del query_cache[key]
    return None

def cache_result(key: str, result: ExecuteSQLResponse) -> None:
    """Cache query result with timestamp"""
    query_cache[key] = (datetime.now().timestamp(), result)

class CheckAndExecuteResponse(BaseModel):
    """Response model for check-and-execute endpoint"""
    status: str
    message: str
    data: Optional[ExecuteSQLResponse] = None

@app.post("/check-and-execute", response_model=CheckAndExecuteResponse)
async def check_and_execute(request: QueryRequest) -> CheckAndExecuteResponse:
    """Check data availability and execute SQL query if data exists using LangChain"""
    logger.info(f"Checking data availability for query: {request.query}")
    
    # First, check data availability using AI
    is_available, check_message = await check_data_availability_with_ai(request.query)
    logger.info(f"Availability check result: {is_available}, message: {check_message}")
    
    if not is_available:
        return CheckAndExecuteResponse(
            status="no_data",
            message=check_message,
            data=None
        )
    
    # If data is available, proceed with LangChain execution
    explanation, sql_query, results, session_id, title, chart_data, chart_config = await process_natural_query_langchain(
        request.query, 
        request.session_id
    )
    
    # Save query to history
    save_query_history(
        session_id=session_id,
        natural_query=request.query,
        sql_query=sql_query,
        query_result=str(results),
        explanation=explanation,
        title=title,
        chart_data=chart_data,
        chart_config=str(chart_config)
    )
    
    response = ExecuteSQLResponse(
        explanation=explanation,
        sql_query=sql_query,
        results=results,
        session_id=session_id,
        title=title,
        chart_data=chart_data,
        chart_config=chart_config
    )
    
    return CheckAndExecuteResponse(
        status="success",
        message="Query executed successfully with LangChain",
        data=response
    )

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server with LangChain support...")
    uvicorn.run(
        "main:app",  # string olarak uygulama yolunu ver
        host="127.0.0.1",
        port=8000,
        log_level="debug",
        reload=True
    )