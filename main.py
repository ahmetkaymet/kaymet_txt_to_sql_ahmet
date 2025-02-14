"""
FastAPI application for natural language to SQL conversion
This API provides two main endpoints:
- /generate-sql: Converts natural language queries to SQL
- /execute-sql: Executes SQL queries against the database
"""
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from utils import generate_sql_query, execute_sql_query

# Initialize FastAPI app
app = FastAPI(title="Txt to SQL API")

class QueryRequest(BaseModel):
    """Request model for query endpoints"""
    query: str

@app.post("/generate-sql")
async def generate_sql(request: QueryRequest) -> Dict[str, str]:
    """
    Generate SQL query from natural language input
    Args:
        request: QueryRequest object containing the natural language query
    Returns:
        Dictionary containing the generated SQL query
    Raises:
        HTTPException: If query generation fails
    """
    try:
        sql_query = generate_sql_query(request.query)
        return {"query": sql_query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/execute-sql")
async def execute_sql(request: QueryRequest) -> Dict[str, List[Dict[str, Any]]]:
    """
    Execute SQL query and return results
    Args:
        request: QueryRequest object containing the SQL query
    Returns:
        Dictionary containing the query results
    Raises:
        HTTPException: If query execution fails
    """
    try:
        results = execute_sql_query(request.query)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 