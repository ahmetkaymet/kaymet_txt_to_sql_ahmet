-- Create table_column_descriptions table first
CREATE TABLE IF NOT EXISTS table_column_descriptions (
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (table_name, column_name)
);

-- Create query_history table
CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    natural_query TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    query_result TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Add descriptions for the columns
INSERT OR REPLACE INTO table_column_descriptions (table_name, column_name, description) VALUES
    ('query_history', 'id', 'Unique identifier for each query record'),
    ('query_history', 'session_id', 'Unique identifier for each query session'),
    ('query_history', 'natural_query', 'The original natural language query from the user'),
    ('query_history', 'sql_query', 'The generated SQL query'),
    ('query_history', 'query_result', 'The results of the query execution in JSON format'),
    ('query_history', 'timestamp', 'When the query was executed'); 