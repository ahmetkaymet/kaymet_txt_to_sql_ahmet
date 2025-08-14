from config.oracle_config import OracleConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_schema_operations():
    try:
        db = OracleConnection()
        conn = db.connect()
        
        if conn:
            cursor = conn.cursor()
            
            # Test listing all tables
            logger.info("Fetching all user tables...")
            cursor.execute("""
                SELECT table_name 
                FROM user_tables 
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            logger.info("Available tables:")
            for table in tables:
                logger.info(f"- {table[0]}")
            
            # Test listing columns of a specific table
            if tables:
                sample_table = tables[0][0]
                logger.info(f"\nFetching columns for table {sample_table}...")
                cursor.execute(f"""
                    SELECT column_name, data_type, nullable
                    FROM user_tab_columns
                    WHERE table_name = '{sample_table}'
                    ORDER BY column_id
                """)
                columns = cursor.fetchall()
                logger.info(f"Columns in {sample_table}:")
                for col in columns:
                    logger.info(f"- {col[0]} ({col[1]}) {'NULL' if col[2] == 'Y' else 'NOT NULL'}")
            
            db.close()
            return True
            
    except Exception as e:
        logger.error(f"Schema test failed: {e}")
        return False

if __name__ == "__main__":
    test_schema_operations()