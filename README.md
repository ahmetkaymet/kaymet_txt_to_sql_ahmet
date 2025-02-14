# Natural Language to SQL API

This API converts natural language queries to SQL and executes them against a SQLite database.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

3. Start the API server:
```bash
python main.py
```

## API Endpoints

### 1. Generate SQL Query
```
POST /generate-sql
```
Convert natural language to SQL query.

Example request:
```json
{
    "query": "Show me all women's products"
}
```

Example response:
```json
{
    "query": "SELECT * FROM Products WHERE Category1 = 'Women'"
}
```

### 2. Execute SQL Query
```
POST /execute-sql
```
Execute a SQL query and get results.

Example request:
```json
{
    "query": "SELECT * FROM Products WHERE Category1 = 'women'"
}
```

Example response:
```json
{
    "results": [
        {
            "ProductID": "PRO1O036364",
            "Name": "Glyph",
            "Category1": "Women",
            "Category2": "Boots"
        }
    ]
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:
- 400: Bad Request (invalid input)
- 500: Internal Server Error (query generation/execution failed)

## Logging

All operations are logged to `sql_operations.log` for debugging and monitoring. 
