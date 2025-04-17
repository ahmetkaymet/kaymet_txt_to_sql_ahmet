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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            title TEXT
        )
        """)
        conn.commit()

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

def save_query_history(
    session_id: str,
    natural_query: str,
    sql_query: str,
    explanation: str,
    query_result: List[Dict[str, Any]],
    title: str
) -> None:
    """Save query history to SQLite database"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Tablonun şemasını kontrol et
            cursor.execute("PRAGMA table_info(query_history)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Tablo yoksa, en baştan oluştur
            if not columns:
                logger.info("Creating query_history table")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS query_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        natural_query TEXT NOT NULL,
                        sql_query TEXT NOT NULL,
                        explanation TEXT,
                        query_result TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        title TEXT
                    )
                """)
                # Şema güncellendikten sonra kolonları tekrar al
                cursor.execute("PRAGMA table_info(query_history)")
                columns = [column[1] for column in cursor.fetchall()]
            
            # Mevcut sütunlara göre sorgu oluştur
            insert_cols = ["session_id", "natural_query", "sql_query"]
            values = [session_id, natural_query, sql_query]
            
            if "explanation" in columns:
                insert_cols.append("explanation")
                values.append(explanation)
                
            insert_cols.append("query_result")
            values.append(str(query_result))
                
            if "title" in columns:
                insert_cols.append("title")
                values.append(title)
            
            # Sorguyu dinamik olarak oluştur
            cols_str = ", ".join(insert_cols)
            placeholders = ", ".join(["?" for _ in insert_cols])
            
            query = f"""
                INSERT INTO query_history (
                    {cols_str}
                ) VALUES ({placeholders})
            """
            
            logger.info(f"Saving query history with columns: {insert_cols}")
            cursor.execute(query, values)
            
            conn.commit()
            logger.info(f"Query saved successfully for session: {session_id}")
            
    except Exception as e:
        logger.error(f"Error saving query history: {e}", exc_info=True)
        raise

# Initialize database when module is imported
initialize_history_db() 
