from config.oracle_config import OracleConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_oracle_connection():
    try:
        db = OracleConnection()
        conn = db.connect()
        
        if conn:
            logger.info("Successfully connected to Oracle Database!")
            
            # Test a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT SYSDATE FROM DUAL")
            result = cursor.fetchone()
            logger.info(f"Current database time: {result[0]}")
            
            db.close()
            return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_oracle_connection()