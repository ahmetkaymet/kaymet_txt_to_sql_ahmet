import sqlite3
import logging
from config.oracle_config import OracleConnection
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sqlite_schema():
    """Get table schemas from SQLite database"""
    with sqlite3.connect("data.db") as sqlite_conn:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
        return cursor.fetchall()

def sqlite_to_oracle_type(sqlite_type):
    """Convert SQLite data types to Oracle data types"""
    type_mapping = {
        'INTEGER': 'NUMBER',
        'REAL': 'FLOAT',
        'TEXT': 'VARCHAR2(4000)',
        'BLOB': 'BLOB',
        'VARCHAR': 'VARCHAR2(4000)',
        'BOOLEAN': 'NUMBER(1)',
        'DATETIME': 'DATE'
    }
    return type_mapping.get(sqlite_type.upper(), 'VARCHAR2(4000)')

def create_oracle_tables(oracle_conn, schema):
    """Create tables in Oracle database"""
    cursor = oracle_conn.cursor()
    
    # First verify and drop all existing tables
    tables_to_process = [(name, stmt) for name, stmt in schema if not name.startswith('sqlite_')]
    
    # Drop all tables first
    for table_name, _ in reversed(tables_to_process):
        table_upper = table_name.upper()
        try:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM user_tables 
                WHERE table_name = :1
            """, (table_upper,))
            
            if cursor.fetchone()[0] > 0:
                # Table exists, try to drop it with force
                cursor.execute(f"""
                    BEGIN
                        FOR c IN (SELECT constraint_name FROM user_constraints WHERE table_name = '{table_upper}')
                        LOOP
                            EXECUTE IMMEDIATE 'ALTER TABLE "{table_upper}" DROP CONSTRAINT ' || c.constraint_name || ' CASCADE';
                        END LOOP;
                        
                        EXECUTE IMMEDIATE 'DROP TABLE "{table_upper}" CASCADE CONSTRAINTS PURGE';
                    EXCEPTION
                        WHEN OTHERS THEN
                            NULL;
                    END;
                """)
                oracle_conn.commit()
                logger.info(f"Forcefully dropped table {table_name}")
                
                # Double check table is gone
                cursor.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = :1", (table_upper,))
                if cursor.fetchone()[0] > 0:
                    raise Exception(f"Failed to drop table {table_name}")
        except Exception as e:
            logger.warning(f"Error during table drop for {table_name}: {e}")
    
    # Now create all tables
    for table_name, create_stmt in tables_to_process:
        try:
            # Convert SQLite CREATE statement to Oracle format
            create_stmt = create_stmt.replace('AUTOINCREMENT', 'GENERATED ALWAYS AS IDENTITY')
            create_stmt = create_stmt.replace('INTEGER PRIMARY KEY', 'NUMBER PRIMARY KEY')
            create_stmt = create_stmt.replace('TEXT', 'VARCHAR2(4000)')
            create_stmt = create_stmt.replace('DATETIME', 'DATE')
                
            # Add quotes around table name and uppercase it
            # Add quotes around identifiers to preserve case
            create_stmt = create_stmt.replace(f'CREATE TABLE {table_name}', 
                                           f'CREATE TABLE "{table_name.upper()}"')
            # Add quotes around column names
            for line in create_stmt.split('\n'):
                if '"' not in line and '(' not in line and ')' not in line:
                    column_name = line.strip().split()[0]
                    create_stmt = create_stmt.replace(f'\n{column_name} ', f'\n"{column_name}" ')
            
            # Execute the create statement
            cursor.execute(create_stmt)
            oracle_conn.commit()
            logger.info(f"Created table {table_name}")
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            logger.error(f"Statement was: {create_stmt}")
            raise

def migrate_data(sqlite_conn, oracle_conn, table_name):
    """Migrate data from SQLite to Oracle"""
    sqlite_cursor = sqlite_conn.cursor()
    oracle_cursor = oracle_conn.cursor()
    
    try:
        # Verify table exists in Oracle
        cursor_tables = oracle_cursor.execute("""
            SELECT table_name 
            FROM user_tables 
            WHERE UPPER(table_name) = :1
        """, (table_name.upper(),))
        
        table_exists = cursor_tables.fetchone()
        if not table_exists:
            logger.error(f"Table {table_name} does not exist in Oracle")
            return
            
        actual_table_name = table_exists[0]  # Get the actual table name with correct case
            
        # Get Oracle column names to maintain case sensitivity
        oracle_cursor.execute(f"""
            SELECT column_name 
            FROM user_tab_columns 
            WHERE table_name = :1 
            ORDER BY column_id
        """, (actual_table_name,))
        columns = [row[0] for row in oracle_cursor.fetchall()]
        
        # Map SQLite columns to Oracle columns
        sqlite_cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sqlite_columns = [description[0] for description in sqlite_cursor.description]
        column_map = {sc.upper(): oc for sc, oc in zip(sqlite_columns, columns)}
        
        # Get all data
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if rows:
            # Prepare insert statement with quoted identifiers
            placeholders = ','.join([':' + str(i+1) for i in range(len(columns))])
            columns_quoted = [f'"{col}"' for col in columns]
            insert_sql = f'INSERT INTO "{actual_table_name}" ({",".join(columns_quoted)}) VALUES ({placeholders})'
            
            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                oracle_cursor.executemany(insert_sql, batch)
                oracle_conn.commit()
                logger.info(f"Inserted {len(batch)} rows into {table_name}")
                
    except Exception as e:
        logger.error(f"Error migrating data for table {table_name}: {e}")

def verify_table_dropped(cursor, table_name: str) -> bool:
    """Verify that a table has been completely dropped"""
    cursor.execute("""
        SELECT COUNT(*) 
        FROM user_tables 
        WHERE table_name = :1
    """, (table_name.upper(),))
    return cursor.fetchone()[0] == 0

def force_drop_all_tables(oracle_conn):
    """Force drop all user tables regardless of dependencies"""
    cursor = oracle_conn.cursor()
    try:
        # Get all user tables
        cursor.execute("SELECT table_name FROM user_tables")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            try:
                # Disable all constraints first
                cursor.execute(f"""
                    BEGIN
                        -- Disable foreign key constraints
                        FOR c IN (SELECT constraint_name FROM user_constraints 
                                WHERE table_name = '{table_name}' 
                                AND constraint_type = 'R')
                        LOOP
                            EXECUTE IMMEDIATE 'ALTER TABLE "{table_name}" DISABLE CONSTRAINT ' || c.constraint_name;
                        END LOOP;
                        
                        -- Drop all constraints
                        FOR c IN (SELECT constraint_name FROM user_constraints 
                                WHERE table_name = '{table_name}')
                        LOOP
                            EXECUTE IMMEDIATE 'ALTER TABLE "{table_name}" DROP CONSTRAINT ' || c.constraint_name || ' CASCADE';
                        END LOOP;
                        
                        -- Drop the table
                        EXECUTE IMMEDIATE 'DROP TABLE "{table_name}" CASCADE CONSTRAINTS PURGE';
                    EXCEPTION
                        WHEN OTHERS THEN
                            NULL;
                    END;
                """)
                oracle_conn.commit()
                logger.info(f"Dropped table {table_name}")
            except Exception as e:
                logger.warning(f"Could not drop table {table_name}: {e}")
    except Exception as e:
        logger.error(f"Error in force_drop_all_tables: {e}")
        raise

def main():
    try:
        # Get SQLite schema
        schema = get_sqlite_schema()
        
        # Connect to Oracle
        oracle_db = OracleConnection()
        oracle_conn = oracle_db.connect()
        
        # First, force drop all existing tables
        logger.info("Dropping all existing tables...")
        force_drop_all_tables(oracle_conn)
        
        # Verify all tables are dropped
        cursor = oracle_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_tables")
        table_count = cursor.fetchone()[0]
        if table_count > 0:
            raise Exception(f"Failed to drop all tables. {table_count} tables still exist.")
        
        # Create tables in Oracle
        create_oracle_tables(oracle_conn, schema)
        
        # Migrate data
        with sqlite3.connect("data.db") as sqlite_conn:
            for table_name, _ in schema:
                if not table_name.startswith('sqlite_'):
                    migrate_data(sqlite_conn, oracle_conn, table_name)
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        if 'oracle_db' in locals():
            oracle_db.close()

if __name__ == "__main__":
    main()