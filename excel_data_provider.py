import pandas as pd
import os
import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from contextlib import contextmanager
import sqlite3
from io import StringIO

logger = logging.getLogger(__name__)

class ExcelDataProvider:
    """Excel/CSV data provider to replace Oracle database"""
    
    def __init__(self, data_dir: str = "/Users/ahmet/Desktop/DATA", catalog_dir: str = "DATA CATALOGS"):
        self.data_dir = data_dir
        self.catalog_dir = catalog_dir
        self.data_cache = {}
        self.schema_cache = {}
        self._initialize_data()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def cursor(self):
        """Compatibility method for database cursor interface"""
        return self
    
    def _fetch_sample_data(self):
        """Fetch sample data from Excel files"""
        tables = self.get_tables()
        sample_data = "\nSample Data Examples:\n"
        for table in tables:
            sample_data += self.get_sample_data(table, limit=3)
        return sample_data
    
    def _initialize_data(self):
        """Initialize data by loading all Excel/CSV files"""
        try:
            # Load all Excel data files (skip CSV files as they might be catalogs)
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.xlsx') and not filename.startswith('~$'):
                    table_name = self._get_table_name(filename)
                    self._load_table_data(table_name, filename)
            
            logger.info(f"Loaded {len(self.data_cache)} tables from {self.data_dir}")
        except Exception as e:
            logger.error(f"Error initializing data: {e}")
    
    def _get_table_name(self, filename: str) -> str:
        """Extract table name from filename"""
        name = os.path.splitext(filename)[0]
        return name.upper()
    
    def _load_table_data(self, table_name: str, filename: str):
        """Load data from Excel/CSV file"""
        try:
            file_path = os.path.join(self.data_dir, filename)
            
            if filename.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                return
            
            # Convert column names to uppercase for consistency
            df.columns = [col.upper() for col in df.columns]
            
            # Store in cache
            self.data_cache[table_name] = df
            
            # Cache schema info
            self.schema_cache[table_name] = list(df.columns)
            
            logger.info(f"Loaded table {table_name} with {len(df)} rows and {len(df.columns)} columns")
            
        except Exception as e:
            logger.error(f"Error loading table {table_name} from {filename}: {e}")
    
    def get_tables(self) -> List[str]:
        """Get list of available table names"""
        return list(self.data_cache.keys())
    
    def get_table_schema(self, table_name: str) -> List[str]:
        """Get column names for a table"""
        return self.schema_cache.get(table_name.upper(), [])
    
    def get_sample_data(self, table_name: str, limit: int = 3) -> str:
        """Get sample data from table"""
        table_name = table_name.upper()
        if table_name not in self.data_cache:
            return f"Table {table_name} not found"
        
        df = self.data_cache[table_name]
        sample_df = df.head(limit)
        
        result = f"\nSample data from {table_name}:\n"
        result += sample_df.to_string(index=False)
        return result
    
    def get_table_info(self) -> str:
        """Get complete table structure information"""
        result = "\nEXACT TABLE STRUCTURE:\n"
        
        for table_name, columns in self.schema_cache.items():
            result += f"{table_name} table has ONLY these columns: {', '.join(columns)}\n"
        
        return result
    
    def execute_query(self, sql_query: str) -> Tuple[List[Dict], str]:
        """Execute SQL query on Excel data using pandas"""
        try:
            # Parse SQL and convert to pandas operations
            result_df = self._sql_to_pandas(sql_query)
            
            # Convert to list of dictionaries
            result_data = result_df.to_dict('records')
            
            return result_data, "Query executed successfully"
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return [], str(e)
    
    def _sql_to_pandas(self, sql_query: str) -> pd.DataFrame:
        """Convert SQL query to pandas operations"""
        sql_upper = sql_query.upper().strip()
        
        # Remove semicolon if present
        if sql_upper.endswith(';'):
            sql_upper = sql_upper[:-1]
        
        # Check if this is a JOIN query
        if 'JOIN' in sql_upper:
            return self._handle_join_query(sql_query)
        
        # Parse SELECT statement
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM\s+"?([A-Z0-9_$#]+)"?', sql_upper, re.IGNORECASE)
        if not select_match:
            raise ValueError("Invalid SELECT statement")
        
        select_clause = select_match.group(1)
        table_name = select_match.group(2).upper()
        
        if table_name not in self.data_cache:
            raise ValueError(f"Table {table_name} not found")
        
        df = self.data_cache[table_name].copy()
        
        # Handle WHERE clause
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|$)', sql_upper, re.IGNORECASE)
        if where_match:
            where_condition = where_match.group(1)
            df = self._apply_where_condition(df, where_condition)
        
        # Handle GROUP BY clause
        group_by_match = re.search(r'GROUP\s+BY\s+(.+?)(?:\s+ORDER\s+BY|$)', sql_upper, re.IGNORECASE)
        if group_by_match:
            group_columns = [col.strip().strip('"') for col in group_by_match.group(1).split(',')]
            df = self._apply_group_by(df, select_clause, group_columns)
        else:
            # Handle simple SELECT without GROUP BY
            df = self._apply_select_clause(df, select_clause)
        
        # Handle ORDER BY clause
        order_by_match = re.search(r'ORDER\s+BY\s+(.+?)$', sql_upper, re.IGNORECASE)
        if order_by_match:
            order_columns = [col.strip().strip('"') for col in order_by_match.group(1).split(',')]
            df = df.sort_values(by=order_columns)
        
        return df
    
    def _handle_join_query(self, sql_query: str) -> pd.DataFrame:
        """Handle JOIN queries by converting to pandas merge operations"""
        sql_upper = sql_query.upper().strip()
        
        # Parse JOIN query: SELECT ... FROM table1 JOIN table2 ON condition WHERE ... GROUP BY ...
        # Example: SELECT BI_CALISAN_BILGILERI.GENDER, COUNT(*) AS WEEKEND_COUNT FROM BI_PDKS JOIN BI_CALISAN_BILGILERI ON BI_PDKS.SICIL_NUMARASI = BI_CALISAN_BILGILERI.SICIL_NUMARASI WHERE BI_PDKS.IS_WEEKEND = 'True' GROUP BY BI_CALISAN_BILGILERI.GENDER
        
        # Extract SELECT clause
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql_upper, re.IGNORECASE)
        if not select_match:
            raise ValueError("Invalid SELECT statement in JOIN query")
        select_clause = select_match.group(1)
        
        # Extract FROM table
        from_match = re.search(r'FROM\s+"?([A-Z0-9_$#]+)"?', sql_upper, re.IGNORECASE)
        if not from_match:
            raise ValueError("Invalid FROM clause in JOIN query")
        from_table = from_match.group(1).upper()
        
        # Extract JOIN table
        join_match = re.search(r'JOIN\s+"?([A-Z0-9_$#]+)"?', sql_upper, re.IGNORECASE)
        if not join_match:
            raise ValueError("Invalid JOIN clause")
        join_table = join_match.group(1).upper()
        
        # Extract ON condition
        on_match = re.search(r'ON\s+(.+?)(?:\s+WHERE|\s+GROUP\s+BY|\s+ORDER\s+BY|$)', sql_upper, re.IGNORECASE)
        if not on_match:
            raise ValueError("Invalid ON clause in JOIN query")
        on_condition = on_match.group(1)
        
        # Parse ON condition to get join columns
        # Example: BI_PDKS.SICIL_NUMARASI = BI_CALISAN_BILGILERI.SICIL_NUMARASI
        on_parts = on_condition.split('=')
        if len(on_parts) != 2:
            raise ValueError("Invalid ON condition format")
        
        left_join_col = on_parts[0].strip().split('.')[-1]  # Get column name after table prefix
        right_join_col = on_parts[1].strip().split('.')[-1]  # Get column name after table prefix
        
        # Get dataframes
        if from_table not in self.data_cache:
            raise ValueError(f"Table {from_table} not found")
        if join_table not in self.data_cache:
            raise ValueError(f"Table {join_table} not found")
        
        df1 = self.data_cache[from_table].copy()
        df2 = self.data_cache[join_table].copy()
        
        # Perform JOIN (merge)
        merged_df = pd.merge(df1, df2, left_on=left_join_col, right_on=right_join_col, how='inner')
        
        # Handle WHERE clause
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|$)', sql_upper, re.IGNORECASE)
        if where_match:
            where_condition = where_match.group(1)
            merged_df = self._apply_where_condition(merged_df, where_condition)
        
        # Handle GROUP BY clause
        group_by_match = re.search(r'GROUP\s+BY\s+(.+?)(?:\s+ORDER\s+BY|$)', sql_upper, re.IGNORECASE)
        if group_by_match:
            group_columns = [col.strip().split('.')[-1] for col in group_by_match.group(1).split(',')]  # Remove table prefix
            merged_df = self._apply_group_by(merged_df, select_clause, group_columns)
        else:
            # Handle simple SELECT without GROUP BY
            merged_df = self._apply_select_clause(merged_df, select_clause)
        
        # Handle ORDER BY clause
        order_by_match = re.search(r'ORDER\s+BY\s+(.+?)$', sql_upper, re.IGNORECASE)
        if order_by_match:
            order_columns = [col.strip().split('.')[-1] for col in order_by_match.group(1).split(',')]  # Remove table prefix
            # Check if columns exist before sorting
            existing_columns = [col for col in order_columns if col in merged_df.columns]
            if existing_columns:
                merged_df = merged_df.sort_values(by=existing_columns)
        
        return merged_df
    
    def _apply_where_condition(self, df: pd.DataFrame, condition: str) -> pd.DataFrame:
        """Apply WHERE condition to dataframe"""
        # Simple WHERE condition parsing
        # Handle IS NOT NULL
        if 'IS NOT NULL' in condition.upper():
            column = condition.split()[0].strip('"')
            return df[df[column].notna()]
        elif 'IS NULL' in condition.upper():
            column = condition.split()[0].strip('"')
            return df[df[column].isna()]
        
        # Handle basic comparisons with regex for better parsing
        import re
        
        # Pattern to match column = 'value' or column = "value" (with or without table prefix)
        # Handle both TABLE.COLUMN = 'value' and COLUMN = 'value'
        eq_pattern = r'([A-Z0-9_$#]+\.)?([A-Z0-9_$#]+)\s*=\s*[\'"]([^\'"]+)[\'"]'
        match = re.search(eq_pattern, condition, re.IGNORECASE)
        if match:
            table_prefix = match.group(1)
            column = match.group(2)
            value = match.group(3)
            
            # Remove table prefix if present
            if table_prefix:
                column = column
            
            # Handle boolean columns
            if column in df.columns and df[column].dtype == 'bool':
                # Convert string 'True'/'False' to boolean
                if value.upper() == 'TRUE':
                    return df[df[column] == True]
                elif value.upper() == 'FALSE':
                    return df[df[column] == False]
                else:
                    return df[df[column] == value]
            # Case-insensitive comparison for string columns
            elif column in df.columns and df[column].dtype == 'object':
                return df[df[column].str.upper() == value.upper()]
            else:
                return df[df[column] == value]
        
        # Fallback to simple split for other operators
        for op in ['>=', '<=', '!=', '=', '>', '<']:
            if op in condition:
                # Use regex to split more safely
                pattern = f'(.+?){re.escape(op)}(.+)'
                match = re.match(pattern, condition)
                if match:
                    column = match.group(1).strip().strip('"')
                    value = match.group(2).strip().strip("'\"")
                    
                    # Try to convert value to appropriate type
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass  # Keep as string
                    
                    if op == '=':
                        return df[df[column] == value]
                    elif op == '!=':
                        return df[df[column] != value]
                    elif op == '>':
                        return df[df[column] > value]
                    elif op == '<':
                        return df[df[column] < value]
                    elif op == '>=':
                        return df[df[column] >= value]
                    elif op == '<=':
                        return df[df[column] <= value]
        
        return df
    
    def _apply_group_by(self, df: pd.DataFrame, select_clause: str, group_columns: List[str]) -> pd.DataFrame:
        """Apply GROUP BY and aggregation"""
        # Parse SELECT clause for aggregations
        select_parts = [part.strip() for part in select_clause.split(',')]
        
        agg_dict = {}
        select_columns = []
        
        for part in select_parts:
            part_upper = part.upper()
            
            if 'COUNT(*)' in part_upper:
                agg_dict['EMPLOYEE_COUNT'] = 'size'
                select_columns.append('EMPLOYEE_COUNT')
            elif 'COUNT(' in part_upper:
                # Handle COUNT(CASE WHEN ...) expressions
                if 'CASE WHEN' in part_upper:
                    # Extract alias from AS clause
                    if ' AS ' in part_upper:
                        alias = part_upper.split(' AS ')[1].strip().strip('"')
                        select_columns.append(alias)
                        # We'll calculate this manually after grouping
                else:
                    # Extract column name from COUNT(column)
                    col_match = re.search(r'COUNT\("?([A-Z0-9_$#]+)"?\)', part_upper)
                    if col_match:
                        col_name = col_match.group(1)
                        agg_dict[f'{col_name}_COUNT'] = (col_name, 'count')
                        select_columns.append(f'{col_name}_COUNT')
            elif 'AVG(' in part_upper:
                col_match = re.search(r'AVG\("?([A-Z0-9_$#]+)"?\)', part_upper)
                if col_match:
                    col_name = col_match.group(1)
                    agg_dict[f'{col_name}_AVG'] = (col_name, 'mean')
                    select_columns.append(f'{col_name}_AVG')
            elif 'SUM(' in part_upper:
                col_match = re.search(r'SUM\("?([A-Z0-9_$#]+)"?\)', part_upper)
                if col_match:
                    col_name = col_match.group(1)
                    agg_dict[f'{col_name}_SUM'] = (col_name, 'sum')
                    select_columns.append(f'{col_name}_SUM')
            elif 'MAX(' in part_upper:
                col_match = re.search(r'MAX\("?([A-Z0-9_$#]+)"?\)', part_upper)
                if col_match:
                    col_name = col_match.group(1)
                    agg_dict[f'{col_name}_MAX'] = (col_name, 'max')
                    select_columns.append(f'{col_name}_MAX')
            elif 'MIN(' in part_upper:
                col_match = re.search(r'MIN\("?([A-Z0-9_$#]+)"?\)', part_upper)
                if col_match:
                    col_name = col_match.group(1)
                    agg_dict[f'{col_name}_MIN'] = (col_name, 'min')
                    select_columns.append(f'{col_name}_MIN')
            elif 'ROUND(' in part_upper and 'CASE' in part_upper:
                # Handle complex expressions like ROUND(COUNT(CASE WHEN ...) * 100.0 / COUNT(*), 2) AS WEEKEND_WORK_PERCENTAGE
                # Extract alias from AS clause
                if ' AS ' in part_upper:
                    alias = part_upper.split(' AS ')[1].strip().strip('"')
                    # For now, we'll calculate this manually after grouping
                    select_columns.append(alias)
            elif 'ROUND(' in part_upper:
                # Handle ROUND(...) expressions
                if ' AS ' in part_upper:
                    alias = part_upper.split(' AS ')[1].strip().strip('"')
                    select_columns.append(alias)
                # Skip this part as it's already handled
                continue
            else:
                # Regular column
                col_name = part.strip().strip('"')
                if col_name in df.columns:
                    select_columns.append(col_name)
        
        # Group by specified columns
        grouped = df.groupby(group_columns)
        
        # Apply aggregations
        if agg_dict:
            # Handle special case for COUNT(*)
            if 'EMPLOYEE_COUNT' in agg_dict:
                result = grouped.size().reset_index(name='EMPLOYEE_COUNT')
            else:
                result = grouped.agg(agg_dict)
                result.columns = [col[0] if isinstance(col, tuple) else col for col in result.columns]
                result = result.reset_index()
        else:
            result = grouped.first().reset_index()
        
        # Handle complex calculated columns
        if 'WEEKEND_WORK_COUNT' in select_columns:
            # Calculate weekend work count using CASE WHEN logic
            weekend_mask = df['IS_WEEKEND'] == True
            weekend_counts = df[weekend_mask].groupby(group_columns).size()
            result['WEEKEND_WORK_COUNT'] = result['GENDER'].map(weekend_counts).fillna(0).astype(int)
        
        if 'TOTAL_WORK_DAYS' in select_columns:
            # Calculate total work days
            total_counts = df.groupby(group_columns).size()
            result['TOTAL_WORK_DAYS'] = result['GENDER'].map(total_counts).fillna(0).astype(int)
        
        if 'WEEKEND_WORK_PERCENTAGE' in select_columns:
            # Calculate weekend work percentage
            if 'WEEKEND_WORK_COUNT' in result.columns and 'TOTAL_WORK_DAYS' in result.columns:
                result['WEEKEND_WORK_PERCENTAGE'] = round(result['WEEKEND_WORK_COUNT'] * 100.0 / result['TOTAL_WORK_DAYS'], 2)
            elif 'WEEKEND_WORK_COUNT' in result.columns and 'EMPLOYEE_COUNT' in result.columns:
                result['WEEKEND_WORK_PERCENTAGE'] = round(result['WEEKEND_WORK_COUNT'] * 100.0 / result['EMPLOYEE_COUNT'], 2)
        
        return result
    
    def _apply_select_clause(self, df: pd.DataFrame, select_clause: str) -> pd.DataFrame:
        """Apply SELECT clause without GROUP BY"""
        select_parts = [part.strip() for part in select_clause.split(',')]
        selected_columns = []
        
        for part in select_parts:
            part_upper = part.upper()
            
            # Handle COUNT(*) and COUNT(column) without GROUP BY
            if 'COUNT(' in part_upper:
                # Return count as a single row
                count_value = len(df)
                # Extract alias from AS clause
                if ' AS ' in part_upper:
                    alias = part_upper.split(' AS ')[1].strip().strip('"')
                else:
                    alias = 'count'
                return pd.DataFrame({alias: [count_value]})
            
            # Remove AS aliases for regular columns
            if ' AS ' in part.upper():
                part = part.split(' AS ')[0].strip()
            
            col_name = part.strip().strip('"')
            if col_name in df.columns:
                selected_columns.append(col_name)
        
        if selected_columns:
            return df[selected_columns]
        else:
            return df
    
    def get_catalog_info(self, table_name: str) -> str:
        """Get catalog information for a table"""
        catalog_file = f"{table_name}_catalog.xlsx"
        catalog_path = os.path.join(self.catalog_dir, catalog_file)
        
        if not os.path.exists(catalog_path):
            return f"Catalog file {catalog_file} not found"
        
        try:
            catalog_df = pd.read_excel(catalog_path)
            return catalog_df.to_string(index=False)
        except Exception as e:
            return f"Error reading catalog {catalog_file}: {e}"

# Global instance
_excel_provider = None

def get_excel_provider() -> ExcelDataProvider:
    """Get or create global Excel data provider"""
    global _excel_provider
    if _excel_provider is None:
        _excel_provider = ExcelDataProvider()
    return _excel_provider

def get_db_connection():
    """Compatibility function - returns Excel provider context manager"""
    return get_excel_provider()
