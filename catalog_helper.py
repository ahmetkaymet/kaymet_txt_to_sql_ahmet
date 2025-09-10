import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

def get_catalog_context() -> str:
    """
    Read all data catalogs and return a formatted context string
    for AI to understand the available data structure
    """
    catalog_dir = Path("DATA CATALOGS")
    context_parts = []
    
    try:
        # Read both CSV and Excel catalog files (exclude temporary files)
        for catalog_file in catalog_dir.glob("*_catalog.*"):
            if catalog_file.name.startswith('~$'):
                continue
            table_name = _extract_table_name(catalog_file.name)
            try:
                if catalog_file.suffix.lower() == '.csv':
                    # Try different encodings with semicolon separator
                    try:
                        df = pd.read_csv(catalog_file, sep=';', encoding='utf-8')
                    except UnicodeDecodeError:
                        try:
                            df = pd.read_csv(catalog_file, sep=';', encoding='latin-1')
                        except UnicodeDecodeError:
                            df = pd.read_csv(catalog_file, sep=';', encoding='cp1252')
                elif catalog_file.suffix.lower() in ['.xlsx', '.xls']:
                    df = pd.read_excel(catalog_file)
                else:
                    continue
            except Exception as e:
                print(f"Error reading {catalog_file}: {e}")
                continue
            
            context_parts.append(f"Table: {table_name}")
            context_parts.append("Columns:")
            
            for _, row in df.iterrows():
                field_name = row.get("Field Name", "")
                data_type = row.get("Data Type", "")
                description = row.get("Description", "")
                example = row.get("Example", "")
                nullable = row.get("Nullable", "Yes")
                
                if pd.notna(field_name):
                    context_parts.append(f"  - {field_name} ({data_type}): {description}")
                    if pd.notna(example):
                        context_parts.append(f"    Example: {example}")
                    context_parts.append(f"    Nullable: {nullable}")
            
            context_parts.append("")  # Empty line between tables
        
        return "\n".join(context_parts)
        
    except Exception as e:
        return f"Error reading catalogs: {str(e)}"

def _extract_table_name(filename: str) -> str:
    """Extract table name from filename"""
    # Remove _catalog suffix and file extension
    name = filename.replace("_catalog.xlsx", "").replace("_catalog.csv", "").replace("_catalog.xls", "")
    name = name.replace(" data catalog.csv", "").replace(" data catalog.csv", "")
    name = name.replace("employe", "employee")  # Fix typo
    name = name.replace("engagments", "engagements")  # Fix typo
    return name.upper().replace(" ", "_")

def get_table_schemas() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get structured schema information for all tables
    """
    catalog_dir = Path("DATA CATALOGS")
    schemas = {}
    
    try:
        # Read both CSV and Excel catalog files (exclude temporary files)
        for catalog_file in catalog_dir.glob("*_catalog.*"):
            if catalog_file.name.startswith('~$'):
                continue
            table_name = _extract_table_name(catalog_file.name)
            try:
                if catalog_file.suffix.lower() == '.csv':
                    # Try different encodings with semicolon separator
                    try:
                        df = pd.read_csv(catalog_file, sep=';', encoding='utf-8')
                    except UnicodeDecodeError:
                        try:
                            df = pd.read_csv(catalog_file, sep=';', encoding='latin-1')
                        except UnicodeDecodeError:
                            df = pd.read_csv(catalog_file, sep=';', encoding='cp1252')
                elif catalog_file.suffix.lower() in ['.xlsx', '.xls']:
                    df = pd.read_excel(catalog_file)
                else:
                    continue
            except Exception as e:
                print(f"Error reading {catalog_file}: {e}")
                continue
            
            columns = []
            for _, row in df.iterrows():
                if pd.notna(row.get("Field Name")):
                    column_info = {
                        "name": row["Field Name"],
                        "data_type": row.get("Data Type", ""),
                        "description": row.get("Description", ""),
                        "example": row.get("Example", ""),
                        "nullable": row.get("Nullable", "Yes") == "Yes"
                    }
                    columns.append(column_info)
            
            schemas[table_name] = columns
    
    except Exception as e:
        print(f"Error reading schemas: {e}")
    
    return schemas

def get_catalog_summary() -> str:
    """
    Get a brief summary of available data for AI context
    """
    schemas = get_table_schemas()
    summary_parts = []
    
    for table_name, columns in schemas.items():
        summary_parts.append(f"{table_name}: {len(columns)} columns")
        # Add key column names for context
        key_columns = [col["name"] for col in columns[:5]]  # First 5 columns
        summary_parts.append(f"  Key columns: {', '.join(key_columns)}")
    
    return "\n".join(summary_parts)