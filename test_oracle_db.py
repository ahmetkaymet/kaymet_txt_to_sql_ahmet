from config.oracle_config import OracleConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    db = OracleConnection()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM user_tables 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        logger.info("\n=== Tables in Database ===")
        for table in tables:
            table_name = table[0]
            # Get row count
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            count = cursor.fetchone()[0]
            logger.info(f"\nTable: {table_name}")
            logger.info(f"Row count: {count}")
            
            # Get sample data
            cursor.execute(f'SELECT * FROM "{table_name}" WHERE ROWNUM <= 5')
            sample_data = cursor.fetchall()
            
            # Get column names
            cursor.execute(f"""
                SELECT column_name 
                FROM user_tab_columns 
                WHERE table_name = :1 
                ORDER BY column_id
            """, (table_name,))
            columns = [row[0] for row in cursor.fetchall()]
            
            logger.info("Columns: " + ", ".join(columns))
            logger.info("Sample data:")
            for row in sample_data:
                logger.info(row)
                
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database()