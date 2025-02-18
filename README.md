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

## Database Schema

The database consists of three main tables with the following structure and descriptions:

### Products Table
| Column    | Description |
|-----------|-------------|
| ProductID | PK - Unique product identifier |
| Name      | Product name |
| Category1 | Main category (Kids/Men/Women) - Case sensitive |
| Category2 | Sub-category |

### Transactions Table
| Column           | Description |
|------------------|-------------|
| StoreID         | PK - Store identifier |
| ProductID       | FK - References Products(ProductID) |
| Quantity        | Number of items sold |
| PricePerQuantity| Price per unit |
| Timestamp       | Format: YYYY-MM-DD-HH-MM-SS |

### Stores Table
| Column   | Description |
|----------|-------------|
| StoreID  | PK - Store ID (starts with STO) |
| State    | US State abbreviation (2 letters) |
| ZipCode  | US ZIP code |

### Viewing Table Descriptions in SQLite
You can view these table and column descriptions directly in the database using SQLite commands:

1. To view all table and column descriptions:
```bash
sqlite3 data.db "SELECT * FROM table_column_descriptions;"
```

2. To view descriptions for a specific table (e.g., Products):
```bash
sqlite3 data.db "SELECT * FROM table_column_descriptions WHERE table_name = 'Products';"
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
    "query": "SELECT * FROM Products WHERE Category1 = 'women'"
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