# Natural Language to SQL Converter

A modern web application that converts natural language queries into SQL and executes them against a database. The application features a chat-like interface for querying data and viewing results in real-time.

## Features

- **Natural Language Processing**: Convert plain English queries into SQL
- **Real-time Query Execution**: Execute generated SQL queries and see results instantly
- **Session Management**: Group related queries into sessions for better organization
- **Query History**: Browse through past queries and their results
- **Detailed Explanations**: Get comprehensive explanations of how each query is processed
- **Modern UI**: Clean, responsive interface with dark mode support
- **Error Handling**: Robust error handling with informative messages

## Architecture

The application consists of two main components:

### Backend (Python/FastAPI)
- Natural language processing using GPT models
- SQL query generation and validation
- Database operations and query execution
- Session and history management
- RESTful API endpoints

### Frontend (Next.js/React)
- Modern, responsive UI built with Chakra UI
- Real-time query processing
- Session management interface
- Query history visualization
- Error handling and user feedback

## Setup

### Backend Setup

1. Install Python dependencies:
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

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

## Database Schema

The application works with a SQLite database containing the following tables:

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

## API Endpoints

### 1. Generate SQL Query
```
POST /generate-sql
```
Convert natural language to SQL query.

### 2. Execute SQL Query
```
POST /execute-sql
```
Execute a SQL query and get results.

### 3. Get Sessions
```
GET /sessions
```
Retrieve all query sessions with their history.

## Example Queries

Here are some example queries you can try:

1. "Show me all women's products"
2. "What are the total sales in New York stores?"
3. "List all stores in California with their zip codes"
4. "Show me the top 5 selling products in the last month"
5. "What is the average price of men's shoes?"

## Error Handling

The application includes comprehensive error handling:

- Input validation
- SQL query validation
- Database connection errors
- API rate limiting
- Network connectivity issues

## Logging

All operations are logged for monitoring and debugging:

- Query processing steps
- SQL generation details
- Execution results
- Error states
- Performance metrics

## Security

The application implements several security measures:

- SQL injection prevention
- Input sanitization
- Query validation
- Rate limiting
- CORS protection

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
