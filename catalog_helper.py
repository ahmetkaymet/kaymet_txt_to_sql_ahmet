"""
Data Catalog Helper
------------------
Simple helper to read data catalogs and provide context to AI
"""

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
        for csv_file in catalog_dir.glob("*.csv"):
            table_name = _extract_table_name(csv_file.name)
            try:
                # Try different encodings with semicolon separator
                df = pd.read_csv(csv_file, sep=';', encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_file, sep=';', encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(csv_file, sep=';', encoding='cp1252')
            
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
    name = filename.replace(" data catalog.csv", "").replace(" data catalog.csv", "")
    name = name.replace("employe", "employee")  # Fix typo
    name = name.replace("engagments", "engagements")  # Fix typo
    return name.lower().replace(" ", "_")

def get_table_schemas() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get structured schema information for all tables
    """
    catalog_dir = Path("DATA CATALOGS")
    schemas = {}
    
    try:
        for csv_file in catalog_dir.glob("*.csv"):
            table_name = _extract_table_name(csv_file.name)
            try:
                # Try different encodings with semicolon separator
                df = pd.read_csv(csv_file, sep=';', encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_file, sep=';', encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(csv_file, sep=';', encoding='cp1252')
            
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
    
    summary_parts.append("Available HR Data Tables:")
    summary_parts.append("=" * 30)
    
    for table_name, columns in schemas.items():
        summary_parts.append(f"\n{table_name.upper()}:")
        summary_parts.append(f"  - {len(columns)} columns")
        
        # Show key columns
        key_columns = [col["name"] for col in columns if "id" in col["name"].lower() or "name" in col["name"].lower()]
        if key_columns:
            summary_parts.append(f"  - Key columns: {', '.join(key_columns[:3])}")
    
    return "\n".join(summary_parts)
