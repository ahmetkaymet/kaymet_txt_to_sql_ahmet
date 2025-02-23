"""
FastAPI application for natural language to SQL conversion
This API provides two main endpoints:
- /generate-sql: Converts natural language queries to SQL
- /execute-sql: Executes SQL queries against the database
"""
from typing import Dict, List, Any
from fastapi import FastAPI
from pydantic import BaseModel
from utils import process_natural_query, execute_sql_query

# Initialize FastAPI app
app = FastAPI(title="Txt to SQL API")

class QueryRequest(BaseModel):
    """Request model for query endpoints"""
    query: str

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
    """
    explanation: str
    sql_query: str
    results: List[Dict[str, Any]]

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
    explanation, sql_query = process_natural_query(request.query)
    return GenerateSQLResponse(explanation=explanation, sql_query=sql_query)

@app.post("/execute-sql", response_model=ExecuteSQLResponse)
async def execute_sql(request: QueryRequest) -> ExecuteSQLResponse:
    """Generate and execute SQL query from natural language input

    This endpoint:
    1. Converts the natural language query to SQL using GPT-4
    2. Executes the generated SQL query against the database
    3. Returns the explanation, query, and results

    Args:
        request (QueryRequest): Request object containing the natural language query

    Returns:
        ExecuteSQLResponse: Object containing:
            - explanation: Detailed explanation of the SQL generation process
            - sql_query: The generated and executed SQL query
            - results: List of dictionaries containing the query results

    Example:
        Request: {"query": "Show all stores in New York"}
        Response: {
            "explanation": "Converting query for NY stores...",
            "sql_query": "SELECT * FROM Stores WHERE State = 'NY'",
            "results": [
                {"StoreID": "STO123", "State": "NY", "ZipCode": 10001},
                {"StoreID": "STO456", "State": "NY", "ZipCode": 10002}
            ]
        }
    """
    explanation, sql_query = process_natural_query(request.query)
    results = execute_sql_query(sql_query)
    return ExecuteSQLResponse(
        explanation=explanation,
        sql_query=sql_query,
        results=results
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 