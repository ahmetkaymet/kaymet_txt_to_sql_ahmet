import os
import oracledb
from dotenv import load_dotenv
import logging
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)
load_dotenv()

class OracleConnectionPool:
    """Oracle database connection pool for better performance"""
    
    def __init__(self, pool_size=20):  # Increased from 10 to 20 - 2x faster
        # Enable thin mode
        oracledb.thin = True
        self.pool = None
        self.pool_size = pool_size
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool with static IP only (no cloud wallet)"""
        try:
            # Statik IP ile bağlantı için özel DSN oluştur
            static_ip = os.getenv("ORACLE_STATIC_IP")
            port = os.getenv("ORACLE_PORT", "1521")
            service_name = os.getenv("ORACLE_SERVICE_NAME")
            sid = os.getenv("ORACLE_SID")
            
            if not static_ip:
                raise ValueError("ORACLE_STATIC_IP environment variable tanımlanmamış! Cloud wallet kullanılamaz.")
            
            if not service_name and not sid:
                raise ValueError("ORACLE_SERVICE_NAME veya ORACLE_SID environment variable'ı tanımlanmamış!")
            
            # Statik IP ile özel DSN oluştur
            if service_name:
                custom_dsn = f"(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcp)(port={port})(host={static_ip}))(connect_data=(service_name={service_name})))"
            else:
                custom_dsn = f"(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcp)(port={port})(host={static_ip}))(connect_data=(sid={sid})))"
            
            logger.info(f"Using static IP connection: {static_ip}:{port}")
            
            self.pool = oracledb.create_pool(
                user=os.getenv("ORACLE_USER"),
                password=os.getenv("ORACLE_PASSWORD"),
                dsn=custom_dsn,
                min=5,  # Increased from 2 to 5 - faster startup
                max=self.pool_size, 
                increment=2,  # Increased from 1 to 2 - faster scaling
                # Cloud wallet ayarları tamamen kaldırıldı - sadece statik IP
            )
            logger.info(f"Oracle connection pool initialized with static IP {static_ip}:{port}")
                
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        if not self.pool:
            self._initialize_pool()
        
        connection = None
        try:
            connection = self.pool.acquire()
            yield connection
        except Exception as e:
            logger.error(f"Error with connection from pool: {e}")
            raise
        finally:
            if connection:
                try:
                    self.pool.release(connection)
                except Exception as e:
                    logger.error(f"Error releasing connection: {e}")
    
    def close_pool(self):
        """Close the connection pool"""
        if self.pool:
            try:
                self.pool.close()
                self.pool = None
                logger.info("Oracle connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

# Global connection pool instance
_connection_pool = None

def get_connection_pool():
    """Get or create the global connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = OracleConnectionPool()
    return _connection_pool

def get_db_connection():
    """Get a database connection from the pool (backward compatibility)"""
    pool = get_connection_pool()
    return pool.get_connection()

class OracleConnection:
    """Legacy OracleConnection class for backward compatibility"""
    def __init__(self):
        # Enable thin mode
        oracledb.thin = True
        self.connection = None

    def connect(self):
        try:
            if not self.connection:
                # Statik IP ile bağlantı kontrolü
                static_ip = os.getenv("ORACLE_STATIC_IP")
                port = os.getenv("ORACLE_PORT", "1521")
                service_name = os.getenv("ORACLE_SERVICE_NAME")
                sid = os.getenv("ORACLE_SID")
                
                if not static_ip:
                    raise ValueError("ORACLE_STATIC_IP environment variable tanımlanmamış! Cloud wallet kullanılamaz.")
                
                if not service_name and not sid:
                    raise ValueError("ORACLE_SERVICE_NAME veya ORACLE_SID environment variable'ı tanımlanmamış!")
                
                # Statik IP ile özel DSN oluştur
                if service_name:
                    custom_dsn = f"(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcp)(port={port})(host={static_ip}))(connect_data=(service_name={service_name})))"
                else:
                    custom_dsn = f"(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcp)(port={port})(host={static_ip}))(connect_data=(sid={sid})))"
                
                logger.info(f"Connecting directly to {static_ip}:{port}")
                
                self.connection = oracledb.connect(
                    user=os.getenv("ORACLE_USER"),
                    password=os.getenv("ORACLE_PASSWORD"),
                    dsn=custom_dsn
                    # Cloud wallet ayarları tamamen kaldırıldı - sadece statik IP
                )
                logger.info(f"Direct connection successful to {static_ip}:{port}")
                    
            return self.connection
        except oracledb.Error as e:
            logger.error(f"Oracle connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    def close(self):
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
            except oracledb.Error as e:
                logger.error(f"Error closing connection: {e}")

    def execute_query(self, query: str, params=None):
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except oracledb.Error as e:
            logger.error(f"Query execution error: {e}")
            raise