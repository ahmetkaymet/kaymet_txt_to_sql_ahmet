import os
import oracledb
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()

class OracleConnection:
    def __init__(self):
        # Enable thin mode
        oracledb.thin = True
        self.tns_admin = os.getenv("TNS_ADMIN")
        # Wallet location is the same as TNS_ADMIN for Oracle Cloud wallets
        self.wallet_location = self.tns_admin
        self.connection = None

    def connect(self):
        try:
            if not self.connection:
                self.connection = oracledb.connect(
                    user=os.getenv("ORACLE_USER"),
                    password=os.getenv("ORACLE_PASSWORD"),
                    dsn=os.getenv("ORACLE_DSN"),
                    config_dir=self.tns_admin,
                    wallet_location=self.wallet_location,
                    wallet_password=os.getenv("WALLET_PASSWORD")
                )
            return self.connection
        except oracledb.Error as e:
            logger.error(f"Oracle connection error: {e}")
            logger.error(f"TNS_ADMIN: {self.tns_admin}")
            logger.error(f"Wallet location: {self.wallet_location}")
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