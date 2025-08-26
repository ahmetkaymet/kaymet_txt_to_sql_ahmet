"""
FastAPI application for natural language to SQL conversion using LangChain
This API provides endpoints:
- /generate-sql: Converts natural language queries to SQL using LangChain
- /execute-sql: Executes SQL queries against the database
- /sessions: Returns all query sessions
- /chart: Generates charts for query results
"""
import asyncio
import time
import datetime
from collections import deque
from typing import Dict, List, Any, Optional
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
    detect_hr_chart_type
)

# from user_roles import validate_user_query, get_user_permissions, user_manager
from query_history import save_query_history
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
    title="HR Analytics API with LangChain",
    description="AI-powered HR data analytics platform for employee, engagement, recruitment, and training data",
    version="2.0.0"
)

#CORS middleware settings at first - CORS middleware must be first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],  # Specific origins
    allow_credentials=True,  # Allow credentials
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods
    allow_headers=["*"],  # Allow all headers
)

# Add CORS debugging middleware
@app.middleware("http")
async def cors_debug_middleware(request: Request, call_next):
    """Debug CORS headers"""
    logger.info(f"CORS Debug - Origin: {request.headers.get('origin')}")
    logger.info(f"CORS Debug - Method: {request.method}")
    
    response = await call_next(request)
    logger.info(f"CORS Debug - Response status: {response.status_code}")
    return response

# Add optimized logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Only log essential information for performance
    start_time = time.time()
    
    try:
        response = await call_next(request)
        # Only log slow requests (>1 second) or errors
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: {request.method} {request.url} took {duration:.2f}s")
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url} - {e}")
        raise

@app.options("/{full_path:path}")
async def options_handler(request: Request):
    """Handle preflight OPTIONS requests for CORS"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true"
        }
    )

@app.get("/test-cors")
async def test_cors():
    """Test endpoint to verify CORS is working"""
    return {"message": "CORS test successful", "timestamp": datetime.datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint that returns API information"""
    logger.info("Root endpoint called")
    return {
        "name": "HR Analytics API with LangChain",
        "version": "2.0.0",
        "description": "AI-powered HR data analytics platform for employee, engagement, recruitment, and training data",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "This information"},
            {"path": "/sessions", "method": "GET", "description": "Get all HR query sessions"},
            {"path": "/generate-sql", "method": "POST", "description": "Generate SQL for HR data analysis using LangChain"},
            {"path": "/execute-sql", "method": "POST", "description": "Execute HR analytics query with LangChain"},
            {"path": "/check-and-execute", "method": "POST", "description": "Check HR data availability and execute analytics query"},
            {"path": "/chart", "method": "POST", "description": "Generate HR-specific charts and visualizations"},
            {"path": "/user-permissions/{username}", "method": "GET", "description": "Get user permissions"},
            {"path": "/users", "method": "GET", "description": "List all demo users"},

        ]
    }

class QueryRequest(BaseModel):
    """Request model for HR analytics query endpoints"""
    query: str
    session_id: str | None = None
    username: str = "demo_admin"  # Default admin user for demo

class GenerateSQLResponse(BaseModel):
    """Response model for HR analytics SQL generation endpoint"""
    explanation: str
    sql_query: str

class ExecuteSQLResponse(BaseModel):
    """Response model for HR analytics execution endpoint with LangChain enhancements

    This model contains the complete HR analytics response including the explanation,
    the SQL query, its execution results, and HR-specific chart information.

    Attributes:
        explanation (str): Detailed explanation of the HR analytics query generation process with AI analysis
        sql_query (str): The generated and executed SQL query for HR data
        results (List[Dict[str, Any]]): HR analytics results, where each dictionary
            represents a row with column names as keys and cell values as values.
        session_id (str): The ID of the HR analytics session
        title (str): The title of the HR analytics query
        chart_data (Optional[str]): Base64 encoded HR chart image if applicable
        chart_config (Dict[str, Any]): HR-specific chart configuration and metadata
    """
    explanation: str
    sql_query: str
    results: List[Dict[str, Any]]
    session_id: str
    title: str
    chart_data: Optional[str] = None
    chart_config: Dict[str, Any] = {}

class Session(BaseModel):
    """Model for an HR analytics query session"""
    id: str
    queries: List[Dict[str, Any]]

class ChartRequest(BaseModel):
    """Request model for HR analytics chart generation"""
    query: str
    chart_type: Optional[str] = None
    x_column: Optional[str] = None
    y_column: Optional[str] = None

@app.get("/sessions")
async def get_sessions(request: Request):
    """Get all HR analytics query sessions from SQLite database"""
    try:
        from query_history import get_all_sessions
        # Doğrudan query_history modülünün fonksiyonunu kullanalım
        sessions = get_all_sessions()
        
        # Minimal logging - only log when there are significant changes
        sessions_count = len(sessions)
        total_queries = sum(len(s['queries']) for s in sessions)
        
        # Cache the last count to avoid unnecessary logging
        if not hasattr(get_sessions, '_last_count'):
            get_sessions._last_count = (0, 0)
        
        last_sessions, last_queries = get_sessions._last_count
        if abs(sessions_count - last_sessions) > 5 or abs(total_queries - last_queries) > 10:
            logger.info(f"Sessions endpoint - {sessions_count} sessions, {total_queries} queries")
            get_sessions._last_count = (sessions_count, total_queries)
        
        return JSONResponse(content=sessions)
    except Exception as e:
        logger.error(f"Error getting sessions: {e}", exc_info=True)
        return JSONResponse(content=[])

@app.post("/generate-sql", response_model=GenerateSQLResponse)
async def generate_sql(request: QueryRequest) -> GenerateSQLResponse:
    """Generate SQL query for HR analytics from natural language input using LangChain

    This endpoint takes a natural language HR query and converts it to SQL using LangChain pipeline.
    It returns both an explanation of the conversion process and the resulting SQL query for HR data analysis.

    Args:
        request (QueryRequest): Request object containing the natural language HR analytics query

    Returns:
        GenerateSQLResponse: Object containing:
            - explanation: Detailed explanation of the HR SQL generation process
            - sql_query: The generated SQL query for HR data analysis

    Example:
        Request: {"query": "Show me employee count by department"}
        Response: {
            "explanation": "Converting HR query for employee count by department...",
            "sql_query": "SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department"
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
    """Generate and execute SQL query for HR analytics from natural language input using LangChain"""
    logger.info(f"Executing HR analytics SQL for query: {request.query}")
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
        
        logger.info(f"HR analytics query executed successfully with LangChain, session_id: {session_id}")
        return response
    except Exception as e:
        logger.error(f"Error executing query with LangChain: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}")

@app.post("/chart", response_model=Dict[str, Any])
async def generate_chart_endpoint(request: ChartRequest) -> Dict[str, Any]:
    """Generate HR-specific charts and visualizations for analytics results"""
    logger.info(f"Generating HR analytics chart for query: {request.query}")
    
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
            chart_config = detect_hr_chart_type(request.query, results)
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

# Request queue for sequential processing
request_queue = deque()
is_processing = False

def get_cached_result(key: str) -> Optional[ExecuteSQLResponse]:
    """Get cached query result if it exists and is not expired"""
    if key in query_cache:
        timestamp, result = query_cache[key]
        # Cache expires after 5 minutes
        if datetime.datetime.now().timestamp() - timestamp < 300:
            return result
        else:
            del query_cache[key]
    return None

def cache_result(key: str, result: ExecuteSQLResponse) -> None:
    """Cache query result with timestamp"""
    query_cache[key] = (datetime.datetime.now().timestamp(), result)

class CheckAndExecuteResponse(BaseModel):
    """Response model for check-and-execute endpoint"""
    status: str
    message: str
    data: Optional[ExecuteSQLResponse] = None

async def process_request_queue():
    """Process requests in the queue sequentially"""
    global is_processing
    
    while request_queue:
        if is_processing:
            await asyncio.sleep(0.1)
            continue
            
        is_processing = True
        try:
            request_data = request_queue.popleft()
            request, future = request_data
            
            # Process the request
            processing_start_time = time.time()
            logger.info(f"🔄 Starting to process query: {request.query}")
            
            explanation, sql_query, results, session_id, title, chart_data, chart_config = await process_natural_query_langchain(
                request.query, 
                request.session_id
            )
            
            processing_end_time = time.time()
            processing_duration = (processing_end_time - processing_start_time) * 1000  # Convert to milliseconds
            logger.info(f"✅ Query processing completed in {processing_duration:.2f}ms")
            
            # Check if data was available
            if not results or (len(results) == 1 and 'message' in results[0] and 'No data available' in str(results[0])):
                response = CheckAndExecuteResponse(
                    status="no_data",
                    message="No data available for this query",
                    data=None
                )
            else:
                # Save to query history
                save_query_history(
                    session_id=session_id,
                    natural_query=request.query,
                    sql_query=sql_query,
                    query_result=str(results),
                    explanation=explanation,
                    title=title,
                    chart_data=chart_data,
                    chart_config=str(chart_config),
                    username=request.username
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
                    timestamp=datetime.datetime.now().isoformat(),
                    chart_data=chart_data,
                    chart_config=chart_config
                )
                
                response = CheckAndExecuteResponse(
                    status="success",
                    message=f"Query executed successfully. Found {len(results)} results in {processing_duration:.2f}ms.",
                    data=response
                )
            
            # Set the result
            future.set_result(response)
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            if 'future' in locals():
                future.set_exception(e)
        finally:
            is_processing = False
    
    is_processing = False

@app.post("/check-and-execute", response_model=CheckAndExecuteResponse)
async def check_and_execute(request: QueryRequest) -> CheckAndExecuteResponse:
    """Check HR data availability and execute analytics query if data exists using LangChain"""
    logger.info(f"Adding query to queue: {request.query} from user: {request.username}")
    
    # Generate session_id if not provided
    if not request.session_id:
        from query_history import generate_session_id
        request.session_id = generate_session_id()
        logger.info(f"Generated new session_id: {request.session_id}")
    
    # Create a future for this request
    future = asyncio.Future()
    
    # Add to queue
    request_queue.append((request, future))
    
    # Start processing if not already running
    if not is_processing:
        asyncio.create_task(process_request_queue())
    
    # Wait for the result
    try:
        result = await asyncio.wait_for(future, timeout=60.0)  # 60 second timeout
        return result
    except asyncio.TimeoutError:
        return CheckAndExecuteResponse(
            status="timeout",
            message="Request timed out",
            data=None
        )


if __name__ == "__main__":
    import uvicorn
    from config.oracle_config import get_connection_pool
    
    logger.info("Starting server with LangChain support...")
    
    # Initialize connection pool before starting server
    try:
        pool = get_connection_pool()
        logger.info("Oracle connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        logger.warning("Server will start but database operations may be slow")
    
    uvicorn.run(
        "main:app",  # string olarak uygulama yolunu ver
        host="127.0.0.1",
        port=8000,
        log_level="info",  # Changed from debug to info for better performance
        reload=True
    )