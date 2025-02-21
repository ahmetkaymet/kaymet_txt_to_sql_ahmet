"""
FastAPI application for natural language to SQL conversion
This API provides two main endpoints:
- /generate-sql: Converts natural language queries to SQL
- /execute-sql: Executes SQL queries against the database
"""
from typing import Dict, List, Any
from fastapi import FastAPI
from pydantic import BaseModel
from utils import process_natural_query

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
    """
    explanation, sql_query = process_natural_query(request.query)
    return {"explanation": explanation, "query": sql_query}

@app.post("/execute-sql")
async def execute_sql(request: QueryRequest) -> Dict[str, Any | List[Dict[str, Any]]]:
    """
    Generate and execute SQL query from natural language input
    Args:
        request: QueryRequest object containing the natural language query
    Returns:
        Dictionary containing the generated SQL query and its results
    """
    explanation, results = process_natural_query(request.query)
    return {
        "explanation": explanation,
        "results": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 