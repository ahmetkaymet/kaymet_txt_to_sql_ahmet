/*
Query History Database Schema

This SQL script defines the schema for the query history tracking system.
It creates and configures tables for storing:
- Query history records with session tracking
- Table and column descriptions
- Metadata about queries and their results

Tables:
1. query_history: Stores all query executions with their results
2. table_column_descriptions: Documents the schema structure

Usage:
    sqlite3 query_history.db < query_history_schema.sql
*/

-- Create table_column_descriptions table
/* 
Table: table_column_descriptions
Purpose: Stores metadata about database tables and their columns
Columns:
- table_name: Name of the table being described
- column_name: Name of the column being described
- description: Detailed description of the column's purpose and format
*/
CREATE TABLE IF NOT EXISTS table_column_descriptions (
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (table_name, column_name)
);

-- Create query_history table
/*
Table: query_history
Purpose: Tracks all natural language queries and their SQL translations
Columns:
- id: Unique identifier for each query execution
- session_id: Groups related queries together
- natural_query: The original user input
- sql_query: The generated SQL query
- query_result: JSON string of query results
- timestamp: When the query was executed
*/
CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    natural_query TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    query_result TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Add descriptions for the columns
/*
Column Descriptions:
These INSERT statements document the purpose and format of each column
in the query_history table for future reference and maintenance.
*/
INSERT OR REPLACE INTO table_column_descriptions (table_name, column_name, description) VALUES
    ('query_history', 'id', 'Unique identifier for each query record'),
    ('query_history', 'session_id', 'UUID for grouping related queries'),
    ('query_history', 'natural_query', 'Original natural language query from user'),
    ('query_history', 'sql_query', 'Generated SQL query'),
    ('query_history', 'query_result', 'Query results stored as JSON string'),
    ('query_history', 'timestamp', 'When the query was executed'); 