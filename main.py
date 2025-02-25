"""
FastAPI application for natural language to SQL conversion
This API provides endpoints:
- /generate-sql: Converts natural language queries to SQL
- /execute-sql: Executes SQL queries against the database
- /sessions: Returns all query sessions
"""
from typing import Dict, List, Any
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils import process_natural_query, execute_sql_query
from query_history import get_all_sessions
from datetime import datetime

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
    title="Txt to SQL API",
    description="API for converting natural language to SQL queries",
    version="1.0.0"
)

"""
Middleware Configuration
----------------------
CORS (Cross-Origin Resource Sharing):
    Enables secure cross-origin requests from frontend applications
    - Origins: Development servers on ports 3000 and 3001
    - Methods: Allows GET, POST, OPTIONS
    - Headers: Allows all headers
    - Credentials: Supports authenticated requests

Logging Middleware:
    Provides request-level logging for monitoring and debugging
    - Captures: HTTP method, URL, response status
    - Tracks: Request timing and error states
    - Purpose: Performance monitoring and error tracking
"""
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend ports
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)

# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Logs HTTP request details and response status
    
    Args:
        request (Request): Incoming HTTP request
        call_next: Next middleware in chain
        
    Returns:
        Response: HTTP response after processing
        
    Logs:
        - Request: Method and URL
        - Response: Status code
        - Errors: Exception details if any
    """
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint that returns API information"""
    logger.info("Root endpoint called")
    return {
        "name": "Text to SQL API",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "This information"},
            {"path": "/sessions", "method": "GET", "description": "Get all query sessions"},
            {"path": "/generate-sql", "method": "POST", "description": "Generate SQL from natural language"},
            {"path": "/execute-sql", "method": "POST", "description": "Execute natural language query"},
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
    """Response model for execute-sql endpoint

    This model contains the complete response including the explanation,
    the SQL query, and its execution results.

    Attributes:
        explanation (str): Detailed explanation of the SQL query generation process
        sql_query (str): The generated and executed SQL query
        results (List[Dict[str, Any]]): Query execution results, where each dictionary
            represents a row with column names as keys and cell values as values.
            Example: [{"StoreID": "STO123", "State": "NY", "ZipCode": 10001}]
        session_id (str): The ID of the query session
        title (str): The title of the query
    """
    explanation: str
    sql_query: str
    results: List[Dict[str, Any]]
    session_id: str
    title: str

class Session(BaseModel):
    """Model for a query session"""
    id: str
    queries: List[Dict[str, Any]]

@app.get("/sessions", response_model=List[Session])
async def get_sessions() -> List[Session]:
    """Get all query sessions with their queries"""
    logger.info("Fetching all sessions")
    try:
        sessions = get_all_sessions()
        logger.info(f"Found {len(sessions)} sessions")
        return sessions
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise

@app.post("/generate-sql", response_model=GenerateSQLResponse)
async def generate_sql(request: QueryRequest) -> GenerateSQLResponse:
    """Generate SQL query from natural language input

    This endpoint takes a natural language query and converts it to SQL using GPT-4o.
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
    explanation, sql_query, _ = process_natural_query(request.query)
    return GenerateSQLResponse(explanation=explanation, sql_query=sql_query)

@app.post("/execute-sql", response_model=ExecuteSQLResponse)
async def execute_sql(request: QueryRequest) -> ExecuteSQLResponse:
    """Generate and execute SQL query from natural language input"""
    logger.info(f"Executing SQL for query: {request.query}")
    try:
        explanation, sql_query, results, session_id, title = process_natural_query(request.query, request.session_id)
        logger.info(f"Query executed successfully, session_id: {session_id}")
        return ExecuteSQLResponse(
            explanation=explanation,
            sql_query=sql_query,
            results=results,
            session_id=session_id,
            title=title
        )
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    ) 