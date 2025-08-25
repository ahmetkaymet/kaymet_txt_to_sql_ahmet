"""
Simple Query History Module
This module provides basic functionality for storing and retrieving query history using SQLite.
"""

import sqlite3
import logging
import json
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "query_history.db"
SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.json")

def generate_session_id() -> str:
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_history_db():
    """Create the query history table if it doesn't exist"""
    try:
        with get_db_connection() as conn:
            # Create the table if it doesn't exist
            conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                natural_query TEXT NOT NULL,
                sql_query TEXT NOT NULL,
                explanation TEXT,
                query_result TEXT,
                chart_data TEXT,
                chart_config TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                title TEXT
            )
            """)
            
            # Add new columns if they don't exist
            try:
                conn.execute("ALTER TABLE query_history ADD COLUMN chart_data TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                conn.execute("ALTER TABLE query_history ADD COLUMN chart_config TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                conn.execute("ALTER TABLE query_history ADD COLUMN username TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            conn.commit()
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def get_all_sessions() -> List[Dict[str, Any]]:
    """Get all query sessions from SQLite database"""
    try:
        # Önce veritabanı bağlantısını kur
        initialize_history_db()
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # Sütun adlarıyla erişim için
            cursor = conn.cursor()
            
            # Tablo şemasını kontrol et ve güvenli şekilde kolonları sorgula
            cursor.execute("PRAGMA table_info(query_history)")
            columns = [column[1] for column in cursor.fetchall()]
            logger.info(f"Table columns: {columns}")
            
            # Tabloda hangi kolonların olduğunu kontrol et
            has_explanation = 'explanation' in columns
            has_title = 'title' in columns 
            time_column = 'created_at' if 'created_at' in columns else 'timestamp'
            
            # Önce tüm benzersiz session_id'leri alalım
            cursor.execute(f"""
                SELECT DISTINCT session_id 
                FROM query_history 
                ORDER BY {time_column} DESC
            """)
            session_ids = cursor.fetchall()
            
            logger.info(f"Found {len(session_ids)} unique session IDs")
            
            sessions = []
            for row in session_ids:
                session_id = row['session_id']
                
                # Dinamik olarak mevcut kolonları seç
                select_cols = ["id", "natural_query", "sql_query"]
                if has_explanation:
                    select_cols.append("explanation")
                select_cols.extend(["query_result", time_column])
                if has_title:
                    select_cols.append("title")
                
                # Add chart columns if they exist
                try:
                    cursor.execute("PRAGMA table_info(query_history)")
                    all_columns = [column[1] for column in cursor.fetchall()]
                    if 'chart_data' in all_columns:
                        select_cols.append("chart_data")
                    if 'chart_config' in all_columns:
                        select_cols.append("chart_config")
                except:
                    pass
                
                col_str = ", ".join(select_cols)
                
                # Her session için ilgili sorguları alalım
                cursor.execute(f"""
                    SELECT {col_str}
                    FROM query_history 
                    WHERE session_id = ?
                    ORDER BY {time_column} DESC
                """, (session_id,))
                
                queries = []
                for row in cursor.fetchall():
                    # Güvenli şekilde query_result'ı değerlendir
                    try:
                        results = eval(row['query_result']) if row['query_result'] else []
                    except:
                        # Hatalı JSON varsa boş liste döndür
                        results = []
                    
                    query = {
                        "id": row['id'],
                        "natural_query": row['natural_query'],
                        "sql_query": row['sql_query'],
                        "results": results,
                        "timestamp": row[time_column]
                    }
                    
                    # Opsiyonel alanları ekle
                    if has_explanation:
                        query["explanation"] = row['explanation']
                    else:
                        query["explanation"] = "No explanation available"
                        
                    if has_title:
                        query["title"] = row['title'] or "Untitled Query"
                    else:
                        query["title"] = "Untitled Query"
                    
                    # Chart verilerini ekle
                    if 'chart_data' in columns and row['chart_data']:
                        query["chart_data"] = row['chart_data']
                    
                    if 'chart_config' in columns and row['chart_config']:
                        try:
                            query["chart_config"] = eval(row['chart_config']) if row['chart_config'] else {}
                        except:
                            query["chart_config"] = {}
                    
                    # Username ekle - güvenli şekilde
                    try:
                        if 'username' in columns and row['username']:
                            query["username"] = row['username']
                        else:
                            query["username"] = "unknown"
                    except (KeyError, IndexError):
                        query["username"] = "unknown"
                    
                    queries.append(query)
                
                if queries:  # Sorgu varsa session'ı ekle
                    sessions.append({
                        "id": session_id,
                        "queries": queries
                    })
                
            logger.info(f"Retrieved {len(sessions)} sessions from database")
            return sessions
            
    except Exception as e:
        logger.error(f"Error getting sessions from database: {e}", exc_info=True)
        return []

def save_query_history(session_id: str, natural_query: str, sql_query: str, query_result: str, explanation: str = None, title: str = None, chart_data: str = None, chart_config: str = None, username: str = None) -> bool:
    """Save a query to the history database with duplicate prevention"""
    try:
        initialize_history_db()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if this exact query already exists for this session
            cursor.execute("""
                SELECT id FROM query_history 
                WHERE session_id = ? AND natural_query = ? AND sql_query = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (session_id, natural_query, sql_query))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record instead of creating duplicate
                logger.info(f"Updating existing query record {existing['id']} instead of creating duplicate")
                cursor.execute("""
                    UPDATE query_history 
                    SET query_result = ?, explanation = ?, title = ?, chart_data = ?, chart_config = ?, username = ?, timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (query_result, explanation, title, chart_data, chart_config, username, existing['id']))
            else:
                # Insert new record
                logger.info(f"Inserting new query record for session {session_id}")
                cursor.execute("""
                    INSERT INTO query_history (session_id, natural_query, sql_query, query_result, explanation, title, chart_data, chart_config, username)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, natural_query, sql_query, query_result, explanation, title, chart_data, chart_config, username))
            
            conn.commit()
            logger.info(f"Query saved successfully for session: {session_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error saving query history: {e}")
        return False

# Initialize database when module is imported
initialize_history_db() 
