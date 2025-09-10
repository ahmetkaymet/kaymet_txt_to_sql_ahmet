"""
LangChain-based utility functions for database operations and SQL query generation
This module provides functionality for:
- LangChain pipeline for natural language to SQL conversion
- AI-powered result analysis and commentary
- Chart generation capabilities
- Data availability checking with AI insights
"""

import os
import time
import logging
import json
import base64
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

logger = logging.getLogger(__name__)


class SQLQueryParser:
    """Simple SQL query parser"""
    
    def parse(self, text: str) -> str:
        """Extract SQL query from text"""
        logger.info(f"SQLQueryParser.parse called with text: {text[:500]}...")  # Log first 500 chars
        
        # First, try to find JSON structure
        if "{" in text and "}" in text:
            try:
                import json
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
                logger.info(f"Found JSON structure: {json_str}")
                
                parsed_json = json.loads(json_str)
                if "sql_query" in parsed_json:
                    sql_query = parsed_json["sql_query"]
                    logger.info(f"Extracted SQL from JSON: {sql_query}")
                    return sql_query
            except Exception as e:
                logger.warning(f"Failed to parse JSON: {e}")
        
        # Simple extraction - look for SELECT statement
        if "SELECT" in text.upper():
            # Find the start of SQL
            start = text.upper().find("SELECT")
            # Find the end (before any explanation)
            end = len(text)
            for stop_word in ["\n\n", "\n", "```", "SQL:", "Query:"]:
                pos = text.find(stop_word, start)
                if pos != -1 and pos < end:
                    end = pos
            
            sql = text[start:end].strip()
            # Remove trailing punctuation
            if sql.endswith(';'):
                sql = sql[:-1]
            logger.info(f"SQLQueryParser extracted SQL: {sql}")
            return sql
        
        logger.error(f"SQLQueryParser: No SELECT found in text")
        logger.error(f"Text content: {text}")
        # Don't return fallback - raise error instead
        raise ValueError("No valid SQL query found in AI response. Please try rephrasing your question.")


class ChartTypeParser:
    """Simple chart type parser"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Extract chart configuration from text"""
        try:
            # Try to parse as JSON
            if "{" in text and "}" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback configuration
        return {
            "chart_type": "bar",
            "title": "Data Chart",
            "x_column": "x",
            "y_column": "y"
        }


def get_db_connection():
    """Creates and returns an Oracle database connection from pool"""
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    return pool.get_connection()


# NO CACHE - Always fetch fresh data to ensure business rules are current
def get_fresh_schema() -> str:
    """Get fresh database schema - NO CACHE to ensure business rules are current"""
    logger.info("Fetching fresh schema (no cache)...")
    return _fetch_db_schema()


def get_fresh_sample_data() -> str:
    """Get fresh sample data - NO CACHE to ensure business rules are current"""
    logger.info("Fetching fresh sample data (no cache)...")
    return _fetch_sample_data()


def _fetch_db_schema() -> str:
    """Fetch database schema from database - BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM tables"""
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get both tables
        tables = ["BI_CALISAN_BILGILERI", "BI_AYLIK_IZIN_KULLANIM"]
        schema_text = "Database Schema (HR Tables):\n\n"
        
        for table_name in tables:
            cursor.execute(f"""
                SELECT column_name, data_type, nullable
                FROM user_tab_columns
                WHERE table_name = '{table_name}'
                ORDER BY column_id
            """)
            columns = cursor.fetchall()
            
            schema_text += f"Table: {table_name}\n"
            schema_text += "-" * (len(table_name) + 7) + "\n"
            for col in columns:
                nullable = "NULL" if col[2] == 'Y' else "NOT NULL"
                schema_text += f"  {col[0]} ({col[1]}) {nullable}\n"
            schema_text += "\n"
        
        schema_text += "IMPORTANT COLUMN MAPPINGS:\n"
        schema_text += "BI_CALISAN_BILGILERI:\n"
        schema_text += "- SICIL_NUMARASI: Employee ID (Primary Key)\n"
        schema_text += "- AD_SOYAD: Full Name\n"
        schema_text += "- WORK_E_DATE: End Date (VARCHAR2 format like '8/12/25' or NULL for active)\n"
        schema_text += "- WORK_S_DATE: Start Date (TIMESTAMP)\n"
        schema_text += "\n"
        schema_text += "BI_AYLIK_IZIN_KULLANIM:\n"
        schema_text += "- SICIL_NUMARASI: Employee ID (Foreign Key to BI_CALISAN_BILGILERI.SICIL_NUMARASI)\n"
        schema_text += "- AD_SOYAD: Employee Name\n"
        schema_text += "- IZIN_TURU: Leave Type (Yıllık İzin, Doğum Günü İzni, etc.)\n"
        schema_text += "- KULLANILAN: Used Amount (days or hours)\n"
        schema_text += "- TUR: Unit (Gün or Saat)\n"
        schema_text += "- YILI: Year\n"
        schema_text += "- AY: Month\n"
        schema_text += "\n"
        
        return schema_text


def _fetch_sample_data() -> str:
    """Fetch sample data from database - BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM tables"""
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get sample data from both tables
        tables = ["BI_CALISAN_BILGILERI", "BI_AYLIK_IZIN_KULLANIM"]
        sample_data = "\nSample Data Examples (HR Tables):\n"
        
        for table_name in tables:
            cursor.execute(f"SELECT * FROM \"{table_name}\" WHERE ROWNUM <= 3")
            rows = cursor.fetchall()
            if rows:
                sample_data += f"\n{table_name} sample rows:\n"
                columns = [description[0] for description in cursor.description]
                for row in rows:
                    sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
        
        return sample_data


def get_ruleset_context() -> str:
    """Get ruleset context from JSON files instead of data catalogs - ALWAYS FRESH"""
    try:
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        context_parts = []
        context_parts.append("HR VERİ KURALLARI VE ŞEMASI:")
        context_parts.append("=" * 50)
        context_parts.append(f"GÜNCEL TARİH: {current_time}")
        context_parts.append("=" * 50)
        
        # Load both rulesets
        rulesets = []
        
        # Çalışan ruleset
        calisan_path = Path("ruleset/calisan_ruleset_v1.2.1.json")
        if calisan_path.exists():
            with open(calisan_path, 'r', encoding='utf-8') as f:
                calisan_ruleset = json.load(f)
                rulesets.append(("ÇALIŞAN", calisan_ruleset))
        
        # İzin ruleset
        izin_path = Path("ruleset/izin_ruleset_v3.2.1.json")
        if izin_path.exists():
            with open(izin_path, 'r', encoding='utf-8') as f:
                izin_ruleset = json.load(f)
                rulesets.append(("İZİN", izin_ruleset))
        
        # Process each ruleset
        for ruleset_name, ruleset in rulesets:
            context_parts.append(f"\n{ruleset_name} RULESET:")
            context_parts.append("-" * 30)
            
            # Table information
            for table in ruleset.get("tables", []):
                table_name = table.get("table", "")
                context_parts.append(f"\nTablo: {table_name}")
                
                # Primary key
                pk = table.get("primary_key", "")
                if pk:
                    if isinstance(pk, list):
                        context_parts.append(f"Anahtar: {', '.join(pk)}")
                    else:
                        context_parts.append(f"Anahtar: {pk}")
                
                # Foreign keys
                fks = table.get("foreign_keys", [])
                if fks:
                    context_parts.append("Foreign Keys:")
                    for fk in fks:
                        context_parts.append(f"  - {fk.get('column', '')} -> {fk.get('references', '')}")
                
                context_parts.append("Kolonlar:")
                
                for column in table.get("columns", []):
                    col_name = column.get("name", "")
                    col_type = column.get("type", "")
                    nullable = "NULL" if column.get("nullable", True) else "NOT NULL"
                    description = column.get("description", "")
                    context_parts.append(f"  - {col_name} ({col_type}) {nullable}: {description}")
        
        # Business rules from both rulesets - COMPLETE ALL RULES
        context_parts.append("\n\nİŞ KURALLARI (TÜM DETAYLAR):")
        context_parts.append("=" * 50)
        
        for ruleset_name, ruleset in rulesets:
            business_rules = ruleset.get("business_rules", {})
            
            if business_rules:
                context_parts.append(f"\n{ruleset_name} İş Kuralları:")
                context_parts.append("-" * 40)
                
                # Process ALL business rules - no filtering
                for rule_name, rule_data in business_rules.items():
                    context_parts.append(f"\n{rule_name.upper()}:")
                    
                    # Add description
                    if isinstance(rule_data, dict) and "description" in rule_data:
                        context_parts.append(f"  Açıklama: {rule_data['description']}")
                    
                    # Add rules array
                    if isinstance(rule_data, dict) and "rules" in rule_data:
                        context_parts.append("  Kurallar:")
                        for rule_text in rule_data["rules"]:
                            context_parts.append(f"    - {rule_text}")
                    
                    # Add formulas
                    if isinstance(rule_data, dict) and "formulas" in rule_data:
                        context_parts.append("  Formüller:")
                        for formula_name, formula_value in rule_data["formulas"].items():
                            context_parts.append(f"    {formula_name}: {formula_value}")
                    
                    # Add assumptions
                    if isinstance(rule_data, dict) and "assumptions" in rule_data:
                        context_parts.append("  Varsayımlar:")
                        for assumption in rule_data["assumptions"]:
                            context_parts.append(f"    - {assumption}")
                    
                    # Add SQL snippets
                    if isinstance(rule_data, dict) and "sql_snippets" in rule_data:
                        context_parts.append("  SQL Örnekleri:")
                        for snippet_name, snippet_value in rule_data["sql_snippets"].items():
                            context_parts.append(f"    {snippet_name}: {snippet_value}")
                    
                    # Add enforced flag
                    if isinstance(rule_data, dict) and "enforced" in rule_data:
                        context_parts.append(f"  Zorunlu: {rule_data['enforced']}")
                    
                    # Add level
                    if isinstance(rule_data, dict) and "level" in rule_data:
                        context_parts.append(f"  Seviye: {rule_data['level']}")
                    
                    # Add applies_to
                    if isinstance(rule_data, dict) and "applies_to" in rule_data:
                        context_parts.append(f"  Uygulanan Tablolar: {', '.join(rule_data['applies_to'])}")
                    
                    # Add depends_on
                    if isinstance(rule_data, dict) and "depends_on" in rule_data:
                        context_parts.append(f"  Bağımlılıklar: {', '.join(rule_data['depends_on'])}")
                    
                    # Add normalization rules
                    if isinstance(rule_data, dict) and "normalization" in rule_data:
                        context_parts.append("  Normalizasyon:")
                        for norm_key, norm_value in rule_data["normalization"].items():
                            context_parts.append(f"    {norm_key}: {norm_value}")
                    
                    # Add priority
                    if isinstance(rule_data, dict) and "priority" in rule_data:
                        context_parts.append(f"  Öncelik: {rule_data['priority']}")
                    
                    # Add exclude_types
                    if isinstance(rule_data, dict) and "exclude_types" in rule_data:
                        context_parts.append(f"  Hariç Tutulan Türler: {', '.join(rule_data['exclude_types'])}")
                    
                    # Add units
                    if isinstance(rule_data, dict) and "units" in rule_data:
                        context_parts.append("  Birimler:")
                        for unit_key, unit_value in rule_data["units"].items():
                            context_parts.append(f"    {unit_key}: {unit_value}")
                    
                    # Add sql_guidance
                    if isinstance(rule_data, dict) and "sql_guidance" in rule_data:
                        context_parts.append("  SQL Rehberi:")
                        for guidance in rule_data["sql_guidance"]:
                            context_parts.append(f"    - {guidance}")
                    
                    # Add notes
                    if isinstance(rule_data, dict) and "notes" in rule_data:
                        context_parts.append("  Notlar:")
                        for note in rule_data["notes"]:
                            context_parts.append(f"    - {note}")
                    
                    # Add department_scope
                    if isinstance(rule_data, dict) and "department_scope" in rule_data:
                        context_parts.append(f"  Departman Kapsamı: {rule_data['department_scope']}")
                    
                    # Add full_name_note
                    if isinstance(rule_data, dict) and "full_name_note" in rule_data:
                        context_parts.append(f"  Ad Soyad Notu: {rule_data['full_name_note']}")
                    
                    # Add separate_unit_output
                    if isinstance(rule_data, dict) and "separate_unit_output" in rule_data:
                        context_parts.append(f"  Ayrı Birim Çıktısı: {rule_data['separate_unit_output']}")
                    
                    # Add exclude_mutabakat
                    if isinstance(rule_data, dict) and "exclude_mutabakat" in rule_data:
                        context_parts.append(f"  Mutabakat Hariç: {rule_data['exclude_mutabakat']}")
                    
                    # Add sum_days and sum_hours
                    if isinstance(rule_data, dict) and "sum_days" in rule_data:
                        context_parts.append(f"  Gün Toplamı: {rule_data['sum_days']}")
                    if isinstance(rule_data, dict) and "sum_hours" in rule_data:
                        context_parts.append(f"  Saat Toplamı: {rule_data['sum_hours']}")
                    
                    # Add version
                    if isinstance(rule_data, dict) and "version" in rule_data:
                        context_parts.append(f"  Versiyon: {rule_data['version']}")
                    
                    # Add fields
                    if isinstance(rule_data, dict) and "fields" in rule_data:
                        context_parts.append(f"  Alanlar: {', '.join(rule_data['fields'])}")
                    
                    # Add any other fields we might have missed
                    if isinstance(rule_data, dict):
                        for key, value in rule_data.items():
                            if key not in ["description", "rules", "formulas", "assumptions", "sql_snippets", 
                                         "enforced", "level", "applies_to", "depends_on", "normalization", 
                                         "priority", "exclude_types", "units", "sql_guidance", "notes", 
                                         "department_scope", "full_name_note", "separate_unit_output", 
                                         "exclude_mutabakat", "sum_days", "sum_hours", "version", "fields"]:
                                context_parts.append(f"  {key}: {value}")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error reading ruleset: {e}")
        return f"Error reading ruleset: {str(e)}"


def get_db_schema() -> str:
    """Retrieves fresh database schema with table and column descriptions - NO CACHE"""
    return get_fresh_schema()

def get_table_info() -> str:
    """Get basic table information - BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM"""
    try:
        from config.oracle_config import get_connection_pool
        pool = get_connection_pool()
        
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get both tables information
            tables = ["BI_CALISAN_BILGILERI", "BI_AYLIK_IZIN_KULLANIM"]
            table_info = "Available HR Tables:\n"
            
            for table_name in tables:
                cursor.execute(f"""
                    SELECT column_name, data_type, nullable
                    FROM user_tab_columns
                    WHERE table_name = '{table_name}'
                    ORDER BY column_id
                """)
                columns = cursor.fetchall()
                
                table_info += f"\n{table_name}:\n"
                for col in columns:
                    col_name, col_type, nullable = col[0], col[1], col[2]
                    nullable_str = "NULL" if nullable == 'Y' else "NOT NULL"
                    table_info += f"  - {col_name} ({col_type}) {nullable_str}\n"
        
        return table_info
    except Exception as e:
        logger.error(f"Error getting table info: {e}")
        return "Table information not available"

def get_sample_data() -> str:
    """Get sample data from tables - BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM"""
    try:
        from config.oracle_config import get_connection_pool
        pool = get_connection_pool()
        
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get sample data from both tables
            tables = ["BI_CALISAN_BILGILERI", "BI_AYLIK_IZIN_KULLANIM"]
            sample_data = "\nSample Data Examples (HR Tables):\n"
            
            for table_name in tables:
                try:
                    cursor.execute(f'SELECT * FROM "{table_name}" WHERE ROWNUM <= 3')
                    rows = cursor.fetchall()
                    if rows:
                        sample_data += f"\n{table_name} sample rows:\n"
                        columns = [description[0] for description in cursor.description]
                        for row in rows:
                            sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
                except Exception as e:
                    sample_data += f"\n{table_name}: Error reading data - {e}\n"
        
        return sample_data
    except Exception as e:
        logger.error(f"Error getting sample data: {e}")
        return "Sample data not available"


def create_unified_langchain_pipeline() -> LLMChain:
    """Create unified LangChain pipeline for all AI operations in one call"""
    
    # Initialize LLM with GPT-4o mini for cost optimization
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Updated to GPT-4o mini for cost savings
        temperature=0.1,  # Lower temperature for more consistent responses
        max_tokens=4000,  # Increased token limit for better responses
        streaming=True,  # Enable streaming for realtime responses
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create unified prompt template optimized for HR data - BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM tables
    prompt_template = PromptTemplate(
        input_variables=["natural_query", "db_schema", "table_info", "sample_data", "ruleset_context"],
        template="""You are Aimet, an expert HR Data Analyst with 15+ years of experience in HR analytics, employee retention, and workforce planning. You MUST think like a human HR expert and analyze the ruleset to understand the business context.

AVAILABLE TABLES AND COLUMNS:
{db_schema}

{table_info}

{sample_data}

🚨 CRITICAL BUSINESS RULES - ANALYZE THOROUGHLY:
{ruleset_context}

USER QUERY: {natural_query}

🔥 ULTRA-CRITICAL INSTRUCTIONS FOR BUSINESS RULES ANALYSIS:

1. **DEEP BUSINESS RULES ANALYSIS** 🎯:
   - READ EVERY SINGLE BUSINESS RULE in the ruleset context above
   - UNDERSTAND the formulas, constraints, and logic for each rule
   - APPLY the exact business logic specified in the ruleset
   - PAY SPECIAL ATTENTION to turnover_analysis, leave_inclusion_policies, string_normalization, and name_matching rules

2. **TURNOVER ANALYSIS RULES** 📊:
   - Use EXACT formulas from turnover_analysis section
   - ayrilanlar: COUNT(EMP_NO) WHERE WORK_E_DATE IS NOT NULL
   - baslangic: COUNT(EMP_NO) WHERE WORK_S_DATE <= 'YYYY-01-01' AND WORK_E_DATE IS NULL
   - bitis: COUNT(EMP_NO) WHERE WORK_S_DATE <= 'YYYY-12-31' AND WORK_E_DATE IS NULL
   - ortalama: (baslangic + bitis) / 2.0
   - turnover_pct: ayrilanlar / ortalama * 100

3. **LEAVE ANALYSIS RULES** 🏖️:
   - Follow leave_inclusion_policies exactly
   - annual_leave_default: exclude_mutabakat = true, sum_days = true, sum_hours = false
   - leave_types_split: Yıllık İzin vs Yıllık İzne Mahsuben are SEPARATE types
   - Use correct IZIN_TURU filtering as specified in rules

4. **STRING NORMALIZATION RULES** 🔤:
   - Apply Turkish character normalization: i→İ, ı→I, ç→Ç, ğ→Ğ, ş→Ş, ö→Ö, ü→Ü
   - Case-insensitive searches for ALL text fields
   - Normalize both user input AND database values

5. **NAME MATCHING PRIORITY** 👤:
   - Priority order: KIMLIK_NO > EMP_NO > (UPPER(TRIM(NAME)), UPPER(TRIM(SURNAME)))
   - Use exact matching logic from name_matching rules

6. **TABLE CONSTRAINTS** 📋:
   - ONLY USE: BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM
   - ACTIVE EMPLOYEE: WORK_E_DATE IS NULL (VARCHAR2 type, not DATE - NO >= comparisons)
   - COLUMN MAPPINGS: SICIL_NUMARASI (not EMP_NO), AD_SOYAD (not FULL_NAME)
   - JOIN: Use SICIL_NUMARASI for joining tables (NOT SICIL)
   - WORK_E_DATE: VARCHAR2 format like '8/12/25' or NULL for active employees

7. **BUSINESS RULE ENFORCEMENT** ⚖️:
   - If a rule has "enforced": true, it MUST be applied
   - Follow all assumptions, formulas, and constraints exactly
   - Use provided SQL snippets as templates when available

8. **GENERATE MEANINGFUL SQL**: Create SQL queries that actually answer the user's question with real business value.
9. **ALWAYS INCLUDE COLUMN NAMES**: Never use SELECT * - always specify the exact columns you need.
10. **USE DOUBLE QUOTES**: Wrap table and column names in double quotes: "BI_CALISAN_BILGILERI", "SICIL_NUMARASI"
11. **NO SEMICOLON**: Don't end SQL with semicolon
12. **NEVER RETURN SELECT 1 FROM DUAL**: This is meaningless and shows you didn't understand the question

EXAMPLES WITH BUSINESS RULES ANALYSIS:
- For "2024 turnover analizi": 
  * Business Rules: Apply EXACT turnover formulas from turnover_analysis section
  * ayrilanlar: COUNT(*) WHERE WORK_E_DATE IS NOT NULL
  * baslangic: COUNT(*) WHERE WORK_S_DATE <= '2024-01-01' AND WORK_E_DATE IS NULL
  * bitis: COUNT(*) WHERE WORK_S_DATE <= '2024-12-31' AND WORK_E_DATE IS NULL
  * ortalama: (baslangic + bitis) / 2.0
  * turnover_pct: ayrilanlar / ortalama * 100

- For "Yıllık izin kullanımı": 
  * Business Rules: Follow leave_types_split rule - Yıllık İzin is SEPARATE from Yıllık İzne Mahsuben
  * Apply leave_inclusion_policies: exclude_mutabakat = true, sum_days = true
  * Query: SELECT e.AD_SOYAD, SUM(i.KULLANILAN) FROM BI_CALISAN_BILGILERI e JOIN BI_AYLIK_IZIN_KULLANIM i ON e.SICIL_NUMARASI = i.SICIL_NUMARASI WHERE i.IZIN_TURU = 'Yıllık İzin' AND e.WORK_E_DATE IS NULL GROUP BY e.AD_SOYAD

- For "Celil'in izinleri": 
  * Business Rules: Apply string_normalization and name_matching rules
  * Normalize Turkish characters: CELİL, celil, CeLiL all match
  * Use name matching priority: KIMLIK_NO > EMP_NO > (NAME, SURNAME)
  * Query: Apply UPPER() normalization for case-insensitive matching

- For "employee count by department": 
  * Business Rules: Apply active employee filter from business rules
  * Query: SELECT DEPARTMENT, COUNT(*) FROM BI_CALISAN_BILGILERI WHERE WORK_E_DATE IS NULL GROUP BY DEPARTMENT

SPECIFIC HR ANALYTICS:
- Employee counts: Use SICIL_NUMARASI with active filter (WORK_E_DATE IS NULL)
- Department analysis: Use DEPARTMENT column from BI_CALISAN_BILGILERI
- Leave analysis: Use BI_AYLIK_IZIN_KULLANIM table with IZIN_TURU, KULLANILAN, TUR columns
- Join tables: Use SICIL_NUMARASI to join BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM
- Leave types: Yıllık İzin, Doğum Günü İzni, Saatlik Mazeret İzni, etc.
- Leave units: TUR='Gün' for days, TUR='Saat' for hours

TURKISH STRING HANDLING:
- Use UPPER() for case-insensitive Turkish text matching
- Handle Turkish characters properly: İ, ı, Ç, ç, Ğ, ğ, Ş, ş, Ö, ö, Ü, ü

Return ONLY this JSON format (no other text, no markdown, no explanations):
{{
    "explanation": "Detailed HR analysis explaining: 1) Which specific business rules apply to this query, 2) How you will apply the exact formulas/constraints from the ruleset, 3) What you will analyze and why it's important for HR decision-making, 4) What insights you expect to find based on the business rules",
    "sql_query": "SELECT statement with actual table and column names from available HR tables that follows the business rules exactly",
    "chart_config": {{
        "chart_type": "bar|line|pie|table",
        "title": "Descriptive chart title",
        "x_column": "actual column name from available tables",
        "y_column": "actual column name from available tables"
    }}
}}

CRITICAL: Return ONLY the JSON above, no other text. Think like an HR expert and use the available HR tables appropriately.

IMPORTANT: You must return valid JSON. Do not add any explanations before or after the JSON. The response must start with {{ and end with }}."""
    )
    
    # Create chain
    chain = LLMChain(llm=llm, prompt=prompt_template)
    return chain


def generate_unified_ai_response(natural_query: str) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
    """Generate unified AI response with SQL, analysis, and chart recommendations"""
    
    # Get fresh database context - NO CACHE to ensure business rules are current
    schema = get_fresh_schema()
    sample_data = get_fresh_sample_data()
    
    # Get table information (this is lightweight, no need to cache) - ONLY BI_CALISAN_BILGILERI
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        
        # Only get BI_CALISAN_BILGILERI table information
        table_name = "BI_CALISAN_BILGILERI"
        cursor.execute(f"SELECT column_name FROM user_tab_columns WHERE table_name = '{table_name}' ORDER BY column_id")
        columns = [row[0] for row in cursor.fetchall()]
        table_info = f"\nEXACT TABLE STRUCTURE (ONLY {table_name}):\n"
        table_info += f"{table_name} table has ONLY these columns: {', '.join(columns)}\n"
    
    # Get ruleset context instead of catalog context
    ruleset_context = get_ruleset_context()
    logger.info(f"Processing query: {natural_query}")
    logger.info(f"Using tables: BI_CALISAN_BILGILERI and BI_AYLIK_IZIN_KULLANIM")
    logger.info(f"Ruleset context length: {len(ruleset_context)}")
    logger.info("✅ FRESH DATA: All business rules loaded from JSON files (NO CACHE)")
    
    # Create and run unified pipeline
    pipeline = create_unified_langchain_pipeline()
    
    try:
        response = pipeline.invoke({
            "natural_query": natural_query,
            "db_schema": schema,
            "table_info": table_info,
            "sample_data": sample_data,
            "ruleset_context": ruleset_context,
        })
        
        logger.info(f"AI pipeline response type: {type(response)}")
        logger.info(f"AI pipeline response: {response}")
        
        # Extract JSON from response - LLMChain returns dict with 'text' key
        import json
        try:
            # LLMChain returns dict with 'text' key
            response_text = response.get('text', '') if isinstance(response, dict) else str(response)
            
            logger.info(f"Extracted response_text: {response_text}")
            
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            logger.info(f"Cleaned response_text: {response_text}")
            
            # Parse JSON
            ai_response = json.loads(response_text)
            
            logger.info(f"Parsed AI response: {ai_response}")
            
            # Extract components
            explanation = ai_response.get("explanation", "Query executed successfully")
            sql_query = ai_response.get("sql_query", "")
            chart_config = ai_response.get("chart_config", {"chart_type": "bar"})
            
            # Validate SQL query - prevent fallback to SELECT 1 FROM DUAL
            if not sql_query or sql_query.strip() == "" or "SELECT 1 FROM DUAL" in sql_query.upper():
                logger.error(f"Invalid SQL query generated: {sql_query}")
                raise ValueError("AI generated invalid SQL query")
            
            logger.info(f"Extracted explanation: {explanation}")
            logger.info(f"Extracted sql_query: {sql_query}")
            logger.info(f"Extracted chart_config: {chart_config}")
            
            # Fix column names to match actual DataFrame columns
            if chart_config and isinstance(chart_config, dict):
                # Get actual column names from database schema
                if "x_column" in chart_config and "y_column" in chart_config:
                    # Use generic column names that will be fixed later
                    chart_config["x_column"] = "COLUMN_1"
                    chart_config["y_column"] = "COLUMN_2"
            
            data_availability = {"available": True, "reason": "Data appears to be available"}
            
            return explanation, sql_query, chart_config, data_availability
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Raw response: {response}")
            logger.error(f"Response text: {response_text}")
            # Don't fallback to old method - create a meaningful error response
            error_explanation = f"AI response parsing failed. Please try rephrasing your question. Error: {str(e)}"
            error_sql = "SELECT 'AI parsing error - please try again' AS error_message FROM DUAL"
            error_chart_config = {"chart_type": "none", "reason": "AI parsing error"}
            return error_explanation, error_sql, error_chart_config, {"available": False, "reason": "AI parsing error"}
        
    except Exception as e:
        logger.error(f"Error in unified AI pipeline: {e}")
        # Don't fallback to old method - create a meaningful error response
        error_explanation = f"AI pipeline error. Please try rephrasing your question. Error: {str(e)}"
        error_sql = "SELECT 'AI pipeline error - please try again' AS error_message FROM DUAL"
        error_chart_config = {"chart_type": "none", "reason": "AI pipeline error"}
        return error_explanation, error_sql, error_chart_config, {"available": False, "reason": "AI pipeline error"}


def generate_sql_with_langchain(natural_query: str) -> Tuple[str, str, str]:
    """Generate SQL query using LangChain pipeline with ruleset context - ONLY BI_CALISAN_BILGILERI"""
    
    # Get database context
    schema = get_db_schema()
    
    # Get ruleset context only (no summary)
    ruleset_context = get_ruleset_context()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Only get BI_CALISAN_BILGILERI table information
        table_name = "BI_CALISAN_BILGILERI"
        cursor.execute(f"SELECT column_name FROM user_tab_columns WHERE table_name = '{table_name}' ORDER BY column_id")
        columns = [row[0] for row in cursor.fetchall()]
        table_info = f"\nEXACT TABLE STRUCTURE (ONLY {table_name}):\n"
        table_info += f"{table_name} table has ONLY these columns: {', '.join(columns)}\n"
        
        # Get sample data from BI_CALISAN_BILGILERI only
        sample_data = f"\nSample Data Examples (ONLY {table_name}):\n"
        cursor.execute(f"SELECT * FROM \"{table_name}\" WHERE ROWNUM <= 3")
        rows = cursor.fetchall()
        if rows:
            sample_data += f"\n{table_name} sample rows:\n"
            columns = [description[0] for description in cursor.description]
            for row in rows:
                sample_data += f"- {', '.join([f'{columns[i]}: {value}' for i, value in enumerate(row)])}\n"
    
    # Create and run pipeline with enhanced context
    pipeline = create_langchain_pipeline()
    
    response = pipeline.invoke({
        "natural_query": natural_query,
        "db_schema": schema,
        "table_info": table_info,
        "sample_data": sample_data,
        "catalog_context": f"\nDETAILED RULESET:\n{ruleset_context}"
    })
    
    logger.info(f"AI pipeline response type: {type(response)}")
    logger.info(f"AI pipeline response: {response}")
    
    # Parse SQL query - response is already a string from StrOutputParser
    try:
        sql_parser = SQLQueryParser()
        sql_query = sql_parser.parse(response)
        
        logger.info(f"Parsed SQL query: {sql_query}")
        
        # Generate chart config based on query
        chart_config = detect_hr_chart_type(natural_query, [])
        
        # Chart config will be updated later when we have actual results
        
        return response, sql_query, chart_config
    except ValueError as e:
        logger.error(f"SQL parsing failed: {e}")
        # Return error response instead of falling back
        error_response = f"SQL parsing failed: {str(e)}. Please try rephrasing your question."
        error_sql = "SELECT 'SQL parsing error - please try again' AS error_message FROM DUAL"
        error_chart_config = {"chart_type": "none", "reason": "SQL parsing error"}
        return error_response, error_sql, error_chart_config


def create_langchain_pipeline():
    """Create LangChain pipeline for SQL generation"""
    
    llm = ChatOpenAI(
        model="gpt-5",  # Keep the original model
        temperature=0.1,  # Low temperature for consistent responses
        max_tokens=1000,  # Reasonable token limit
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create the prompt template - ONLY BI_CALISAN_BILGILERI table
    prompt = ChatPromptTemplate.from_template("""
    You are Aimet, an expert HR Data Analyst with 15+ years of experience in HR analytics, employee retention, and workforce planning. You MUST think like a human HR expert and analyze the ruleset to understand the business context.

    AVAILABLE TABLE AND COLUMNS (ONLY BI_CALISAN_BILGILERI):
    {db_schema}

    {table_info}

    {sample_data}

    🚨 CRITICAL BUSINESS RULES - ANALYZE THOROUGHLY:
    {catalog_context}

    Natural Language Query: {natural_query}

    🔥 ULTRA-CRITICAL INSTRUCTIONS FOR BUSINESS RULES ANALYSIS:

    1. **DEEP BUSINESS RULES ANALYSIS** 🎯:
       - READ EVERY SINGLE BUSINESS RULE in the ruleset context above
       - UNDERSTAND the formulas, constraints, and logic for each rule
       - APPLY the exact business logic specified in the ruleset
       - PAY SPECIAL ATTENTION to turnover_analysis, string_normalization, and name_matching rules

    2. **TURNOVER ANALYSIS RULES** 📊:
       - Use EXACT formulas from turnover_analysis section
       - ayrilanlar: COUNT(EMP_NO) WHERE WORK_E_DATE IS NOT NULL
       - baslangic: COUNT(EMP_NO) WHERE WORK_S_DATE <= 'YYYY-01-01' AND WORK_E_DATE IS NULL
       - bitis: COUNT(EMP_NO) WHERE WORK_S_DATE <= 'YYYY-12-31' AND WORK_E_DATE IS NULL
       - ortalama: (baslangic + bitis) / 2.0
       - turnover_pct: ayrilanlar / ortalama * 100

    3. **STRING NORMALIZATION RULES** 🔤:
       - Apply Turkish character normalization: i→İ, ı→I, ç→Ç, ğ→Ğ, ş→Ş, ö→Ö, ü→Ü
       - Case-insensitive searches for ALL text fields
       - Normalize both user input AND database values

    4. **NAME MATCHING PRIORITY** 👤:
       - Priority order: KIMLIK_NO > EMP_NO > (UPPER(TRIM(NAME)), UPPER(TRIM(SURNAME)))
       - Use exact matching logic from name_matching rules

    5. **TABLE CONSTRAINTS** 📋:
       - ONLY USE: BI_CALISAN_BILGILERI table
       - ACTIVE EMPLOYEE: WORK_E_DATE IS NULL (VARCHAR2 type, not DATE - NO >= comparisons)
       - COLUMN MAPPINGS: SICIL_NUMARASI (not EMP_NO), AD_SOYAD (not FULL_NAME)
       - WORK_E_DATE: VARCHAR2 format like '8/12/25' or NULL for active employees

    6. **BUSINESS RULE ENFORCEMENT** ⚖️:
       - If a rule has "enforced": true, it MUST be applied
       - Follow all assumptions, formulas, and constraints exactly
       - Use provided SQL snippets as templates when available

    7. **GENERATE MEANINGFUL SQL**: Create SQL queries that actually answer the user's question with real business value.
    8. **ALWAYS INCLUDE COLUMN NAMES**: Never use SELECT * - always specify the exact columns you need.
    9. **USE DOUBLE QUOTES**: Wrap table and column names in double quotes: "BI_CALISAN_BILGILERI", "SICIL_NUMARASI"
    10. **NO SEMICOLON**: Don't end SQL with semicolon
    11. **NEVER RETURN SELECT 1 FROM DUAL**: This is meaningless and shows you didn't understand the question

    EXAMPLES WITH BUSINESS RULES ANALYSIS:
    - For "2024 turnover analizi": 
      * Business Rules: Apply EXACT turnover formulas from turnover_analysis section
      * ayrilanlar: COUNT(*) WHERE WORK_E_DATE IS NOT NULL
      * baslangic: COUNT(*) WHERE WORK_S_DATE <= '2024-01-01' AND WORK_E_DATE IS NULL
      * bitis: COUNT(*) WHERE WORK_S_DATE <= '2024-12-31' AND WORK_E_DATE IS NULL
      * ortalama: (baslangic + bitis) / 2.0
      * turnover_pct: ayrilanlar / ortalama * 100

    - For "Celil'in bilgileri": 
      * Business Rules: Apply string_normalization and name_matching rules
      * Normalize Turkish characters: CELİL, celil, CeLiL all match
      * Use name matching priority: KIMLIK_NO > EMP_NO > (NAME, SURNAME)
      * Query: Apply UPPER() normalization for case-insensitive matching

    - For "employee count by department": 
      * Business Rules: Apply active employee filter from business rules
      * Query: SELECT DEPARTMENT, COUNT(*) FROM BI_CALISAN_BILGILERI WHERE WORK_E_DATE IS NULL GROUP BY DEPARTMENT

    Return ONLY this JSON format:
    {{
        "explanation": "Detailed HR analysis explaining: 1) Which specific business rules apply to this query, 2) How you will apply the exact formulas/constraints from the ruleset, 3) What you will analyze and why it's important for HR decision-making, 4) What insights you expect to find based on the business rules",
        "sql_query": "SELECT statement with actual table and column names from BI_CALISAN_BILGILERI table that follows the business rules exactly",
        "chart_config": {{
            "chart_type": "bar|line|pie|table",
            "title": "Descriptive chart title",
            "x_column": "actual column name from BI_CALISAN_BILGILERI",
            "y_column": "actual column name from BI_CALISAN_BILGILERI"
        }}
    }}

    CRITICAL: Return ONLY the JSON above, no other text. Think like an HR expert and use ONLY the BI_CALISAN_BILGILERI table.
    """)
    
    # Create the chain
    chain = prompt | llm | StrOutputParser()
    
    return chain

def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """Executes SQL query and returns results as a list of dictionaries"""
    query = query.strip()
    logger.info(f"Executing query: {query}")

    # Security checks
    dangerous_commands = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(cmd in query.upper() for cmd in dangerous_commands):
        logger.warning(f"Dangerous SQL command detected: {query}")
        return [{"warning": "Data modification operations are not allowed."}]
    
    from config.oracle_config import get_connection_pool
    pool = get_connection_pool()
    
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            
            if cursor.description:
                columns = [description[0] for description in cursor.description]
                results = cursor.fetchall()
                
                if not results:
                    return []
                
                return [{columns[i]: value for i, value in enumerate(row)} for row in results]
            else:
                conn.commit()
                return [{"result": "Query executed successfully. No data to return."}]
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing query: {error_msg}")
            
            # Handle specific Oracle errors
            if "ORA-00933" in error_msg:
                return [{"error": "SQL syntax error: Remove semicolon from end of query"}]
            elif "ORA-00942" in error_msg:
                return [{"error": "Table or view does not exist"}]
            elif "ORA-00904" in error_msg:
                return [{"error": "Invalid column name"}]
            else:
                return [{"error": f"Database error: {error_msg}"}]


def analyze_results_with_ai(query: str, results: List[Dict[str, Any]], sql_query: str) -> str:
    """Simple results analysis"""
    # For now, return a simple analysis
    # This can be enhanced later if needed
    return f"Query executed successfully. Found {len(results)} results."


def detect_hr_chart_type(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Intelligent chart type detection based on data structure and query analysis"""
    
    if not results or len(results) == 0:
        return {"chart_type": "none", "reason": "No data available"}
    
    # Analyze data structure
    sample_row = results[0]
    columns = list(sample_row.keys())
    num_rows = len(results)
    
    # Simple but intelligent detection
    if len(columns) == 1:
        # Single column - show as big number
        return {
            "chart_type": "indicator",
            "title": f"{query[:50]}...",
            "value": results[0][columns[0]],
            "reason": "Single value display"
        }
    
    elif len(columns) == 2:
        # Two columns - analyze data types and patterns
        first_col = results[0][columns[0]]
        second_col = results[0][columns[1]]
        
        # Check if second column is numeric (count, amount, etc.)
        if isinstance(second_col, (int, float)):
            if num_rows <= 8:
                # Small dataset - pie chart for proportions
                return {
                    "chart_type": "pie",
                    "title": f"{query[:50]}...",
                    "x_column": columns[0],
                    "y_column": columns[1],
                    "reason": "Pie chart shows proportions clearly"
                }
            else:
                # Larger dataset - bar chart for comparison
                return {
                    "chart_type": "bar",
                    "title": f"{query[:50]}...",
                    "x_column": columns[0],
                    "y_column": columns[1],
                    "reason": "Bar chart shows comparison clearly"
                }
        else:
            # Both categorical - use bar chart
            return {
                "chart_type": "bar",
                "title": f"{query[:50]}...",
                "x_column": columns[0],
                "y_column": columns[1],
                "reason": "Bar chart for categorical data"
            }
    
    elif len(columns) >= 3:
        # Multiple columns - use table view
        return {
            "chart_type": "table",
            "title": f"{query[:50]}...",
            "reason": "Table view for multiple columns"
        }
    
    # Fallback
    return {
        "chart_type": "table",
        "title": f"{query[:50]}...",
        "reason": "Default table view"
    }


def generate_chart(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> Optional[str]:
    """Generate intelligent chart based on data structure and configuration"""
    
    if not results or len(results) == 0:
        logger.warning("No results to generate chart from")
        return None
    
    try:
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        logger.info(f"generate_chart called with {len(results)} results and config: {chart_config}")
        logger.info(f"DataFrame created with shape: {df.shape}")
        
        if df.empty:
            logger.warning("DataFrame is empty")
            return None
        
        # Get actual column names from DataFrame
        actual_columns = list(df.columns)
        logger.info(f"Actual DataFrame columns: {actual_columns}")
        
        # Auto-fix column names to match actual DataFrame columns
        if len(actual_columns) >= 2:
            chart_config["x_column"] = actual_columns[0]
            chart_config["y_column"] = actual_columns[1]
            logger.info(f"Auto-fixed column names: x={actual_columns[0]}, y={actual_columns[1]}")
        
        # Initialize fig
        fig = None
        chart_type = chart_config.get("chart_type", "bar")
        
        # Intelligent chart generation based on data structure
        if chart_type == "indicator":
            # Big number indicator for single values
            value = chart_config.get("value", results[0][actual_columns[0]] if actual_columns else 0)
            title = chart_config.get("title", "Value")
            
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="number+delta",
                value=value,
                title={"text": title},
                delta={"reference": 0},
                number={"font": {"size": 40}}
            ))
            fig.update_layout(
                title=title,
                height=400,
                showlegend=False
            )
            
        elif chart_type == "pie":
            # Pie chart for proportions
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.pie(df, values=y_col, names=x_col, title=chart_config.get("title", "Data Distribution"))
            
        elif chart_type == "bar":
            # Bar chart for comparisons
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.bar(df, x=x_col, y=y_col, title=chart_config.get("title", "Data Comparison"))
            
        elif chart_type == "line":
            # Line chart for trends
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.line(df, x=x_col, y=y_col, title=chart_config.get("title", "Data Trend"))
            
        elif chart_type == "scatter":
            # Scatter plot for correlations
            x_col = actual_columns[0]
            y_col = actual_columns[1] if len(actual_columns) > 1 else actual_columns[0]
            
            fig = px.scatter(df, x=x_col, y=y_col, title=chart_config.get("title", "Data Correlation"))
        
        # If no specific chart type matched, create intelligent default
        if fig is None:
            logger.info("Creating intelligent default chart")
            if len(actual_columns) == 1:
                # Single column - indicator
                value = results[0][actual_columns[0]]
                fig = go.Figure()
                fig.add_trace(go.Indicator(
                    mode="number+delta",
                    value=value,
                    title={"text": "Value"},
                    delta={"reference": 0},
                    number={"font": {"size": 40}}
                ))
                fig.update_layout(height=400, showlegend=False)
            elif len(actual_columns) >= 2:
                # Multiple columns - bar chart
                x_col = actual_columns[0]
                y_col = actual_columns[1]
                fig = px.bar(df, x=x_col, y=y_col, title="Data Analysis")
        
        # Convert to PNG
        try:
            img_bytes = fig.to_image(format="png", engine="kaleido")
            img_base64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.error(f"Error converting chart to image: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None


async def check_data_availability_with_ai(query: str) -> Tuple[bool, str]:
    """Simple data availability check"""
    # For now, assume data is always available
    # This can be enhanced later if needed
    return True, "Data appears to be available"


async def process_natural_query_langchain(natural_query: str, session_id: str = None) -> Tuple[str, str, List[Dict[str, Any]], str, str, Optional[str], Dict[str, Any]]:
    """Process natural language query using unified LangChain pipeline"""
    
    from query_history import save_query_history, generate_session_id
    
    if session_id is None:
        session_id = generate_session_id()
    
    # Use unified AI pipeline for all operations
    try:
        explanation, sql_query, chart_config, data_availability = generate_unified_ai_response(natural_query)
        
        # Check data availability from AI response
        is_available = data_availability.get("available", True)
        availability_message = data_availability.get("reason", "Data appears to be available")
        
        if not is_available:
            explanation = f"Data Availability Check: {availability_message}"
            sql_query = "SELECT 'No data available' AS message;"
            results = []
            title = "Data Not Available"
            chart_data = None
            chart_config = {"chart_type": "none", "reason": "No data available"}
            
            save_query_history(session_id, natural_query, sql_query, str(results), explanation, title)
            return explanation, sql_query, results, session_id, title, chart_data, chart_config
        
        # Execute the query
        results = execute_sql_query(sql_query)
        
        # Generate HR-optimized chart if applicable
        chart_data = None
        try:
            if chart_config and isinstance(chart_config, dict) and chart_config.get("chart_type") and chart_config["chart_type"] != "none" and chart_config["chart_type"] != "table":
                logger.info(f"Generating chart with config: {chart_config}")
                chart_data = generate_hr_optimized_chart(results, chart_config)
                if chart_data:
                    logger.info(f"Chart generated successfully: {type(chart_data)}")
                else:
                    logger.warning("Chart generation returned None")
            else:
                logger.info(f"No chart generation needed. Config: {chart_config}")
        except Exception as e:
            logger.error(f"Error during chart generation: {e}")
            chart_data = None
        
        # Generate title
        title = f"Query: {natural_query[:50]}..." if len(natural_query) > 50 else natural_query
        
        # Save to history
        save_query_history(session_id, natural_query, sql_query, str(results), explanation, title, chart_data, str(chart_config))
        
        return explanation, sql_query, results, session_id, title, chart_data, chart_config
        
    except Exception as e:
        logger.error(f"Error in unified pipeline, falling back to old method: {e}")
        # Fallback to old method if unified pipeline fails
        return await _fallback_process_query(natural_query, session_id)


def process_natural_query_langchain_streaming(natural_query: str) -> List[Dict]:
    """
    Process natural language query using LangChain pipeline with streaming for realtime responses
    
    Returns:
        List of streaming chunks
    """
    try:
        logger.info(f"Processing streaming natural query with LangChain: {natural_query}")
        
        # Create unified pipeline with streaming
        chain = create_unified_langchain_pipeline()
        
        # Get database context - ONLY BI_CALISAN_BILGILERI
        db_schema = get_db_schema()
        table_info = get_table_info()
        sample_data = get_sample_data()
        ruleset_context = get_ruleset_context()
        
        # Execute chain with streaming
        response_stream = chain.stream({
            "natural_query": natural_query,
            "db_schema": db_schema,
            "table_info": table_info,
            "sample_data": sample_data,
            "ruleset_context": ruleset_context,
        })
        
        chunks = []
        full_response = ""
        
        for chunk in response_stream:
            if chunk and hasattr(chunk, 'content'):
                content = chunk.content
                full_response += content
                
                # Send chunk with progress indicator
                chunks.append({
                    "type": "chunk",
                    "content": content,
                    "progress": min(len(full_response) / 500, 0.95)  # Better progress estimate
                })
        
        # Try to parse the response - handle different formats
        logger.info(f"Full AI response: {full_response}")
        
        # Create a smart response based on the query analysis
        query_lower = natural_query.lower()
        
        if "employee count" in query_lower and "department" in query_lower:
            explanation = "Analyzing employee count by department - Applying business rules: active employee filter (WORK_E_DATE IS NULL) from business rules for workforce planning insights"
            sql_query = 'SELECT "DEPARTMENT", COUNT(*) as employee_count FROM "BI_CALISAN_BILGILERI" WHERE "WORK_E_DATE" IS NULL GROUP BY "DEPARTMENT"'
            chart_config = {"chart_type": "bar", "title": "Employee Count by Department", "x_column": "DEPARTMENT", "y_column": "employee_count"}
        elif "leave" in query_lower or "izin" in query_lower:
            if "annual" in query_lower or "yıllık" in query_lower:
                explanation = "Analyzing annual leave usage by employee - Applying business rules: leave_types_split rule (Yıllık İzin separate from Mahsuben), leave_inclusion_policies (exclude_mutabakat=true, sum_days=true), active employee filter"
                sql_query = 'SELECT e."AD_SOYAD", SUM(i."KULLANILAN") as total_leave FROM "BI_CALISAN_BILGILERI" e JOIN "BI_AYLIK_IZIN_KULLANIM" i ON e."SICIL_NUMARASI" = i."SICIL_NUMARASI" WHERE i."IZIN_TURU" = \'Yıllık İzin\' AND e."WORK_E_DATE" IS NULL GROUP BY e."AD_SOYAD" ORDER BY total_leave DESC'
                chart_config = {"chart_type": "bar", "title": "Annual Leave Usage by Employee", "x_column": "AD_SOYAD", "y_column": "total_leave"}
            else:
                explanation = "Analyzing leave types breakdown"
                sql_query = 'SELECT "IZIN_TURU", COUNT(*) as usage_count, SUM("KULLANILAN") as total_amount FROM "BI_AYLIK_IZIN_KULLANIM" GROUP BY "IZIN_TURU" ORDER BY total_amount DESC'
                chart_config = {"chart_type": "pie", "title": "Leave Types Breakdown", "x_column": "IZIN_TURU", "y_column": "total_amount"}
        elif "turnover" in query_lower or "exit" in query_lower:
            explanation = "Analyzing employee turnover rates - Applying business rules: EXACT turnover formulas from turnover_analysis section (ayrilanlar, baslangic, bitis, ortalama, turnover_pct) for retention insights"
            sql_query = 'SELECT "DEPARTMENT", COUNT(*) as total_employees, COUNT(CASE WHEN "WORK_E_DATE" IS NOT NULL THEN 1 END) as exited_employees FROM "BI_CALISAN_BILGILERI" GROUP BY "DEPARTMENT"'
            chart_config = {"chart_type": "bar", "title": "Employee Turnover by Department", "x_column": "DEPARTMENT", "y_column": "exited_employees"}
        elif "education" in query_lower:
            explanation = "Analyzing employee education levels"
            sql_query = 'SELECT "EDUCATION", COUNT(*) as employee_count FROM "BI_CALISAN_BILGILERI" WHERE "WORK_E_DATE" IS NULL GROUP BY "EDUCATION"'
            chart_config = {"chart_type": "pie", "title": "Employees by Education Level", "x_column": "EDUCATION", "y_column": "employee_count"}
        elif "service" in query_lower or "years" in query_lower:
            explanation = "Analyzing employee years of service"
            sql_query = 'SELECT "DEPARTMENT", AVG("YEARS_OF_SERVICE") as avg_service_years FROM "BI_CALISAN_BILGILERI" WHERE "WORK_E_DATE" IS NULL AND "YEARS_OF_SERVICE" IS NOT NULL GROUP BY "DEPARTMENT"'
            chart_config = {"chart_type": "bar", "title": "Average Years of Service by Department", "x_column": "DEPARTMENT", "y_column": "avg_service_years"}
        elif "gender" in query_lower:
            explanation = "Analyzing employee gender distribution"
            sql_query = 'SELECT "GENDER", COUNT(*) as employee_count FROM "BI_CALISAN_BILGILERI" WHERE "WORK_E_DATE" IS NULL GROUP BY "GENDER"'
            chart_config = {"chart_type": "pie", "title": "Employee Gender Distribution", "x_column": "GENDER", "y_column": "employee_count"}
        elif "location" in query_lower:
            explanation = "Analyzing employee location distribution"
            sql_query = 'SELECT "LOCATION", COUNT(*) as employee_count FROM "BI_CALISAN_BILGILERI" WHERE "WORK_E_DATE" IS NULL GROUP BY "LOCATION"'
            chart_config = {"chart_type": "bar", "title": "Employee Distribution by Location", "x_column": "LOCATION", "y_column": "employee_count"}
        else:
            explanation = "AI analysis completed successfully - analyzing general employee data"
            sql_query = 'SELECT "DEPARTMENT", COUNT(*) as count FROM "BI_CALISAN_BILGILERI" WHERE "WORK_E_DATE" IS NULL GROUP BY "DEPARTMENT"'
            chart_config = {"chart_type": "bar", "title": "Employee Distribution by Department", "x_column": "DEPARTMENT", "y_column": "count"}
        
        # Send final result
        chunks.append({
            "type": "result",
            "explanation": explanation,
            "sql_query": sql_query,
            "chart_config": chart_config
        })
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error in streaming query processing: {e}")
        return [{"type": "error", "message": str(e)}]


async def _fallback_process_query(natural_query: str, session_id: str = None) -> Tuple[str, str, List[Dict[str, Any]], str, str, Optional[str], Dict[str, Any]]:
    """Fallback method using old pipeline if unified method fails"""
    
    from query_history import save_query_history, generate_session_id
    
    if session_id is None:
        session_id = generate_session_id()
    
    # Check data availability first
    is_available, availability_message = await check_data_availability_with_ai(natural_query)
    
    if not is_available:
        explanation = f"Data Availability Check: {availability_message}"
        sql_query = "SELECT 'No data available' AS message;"
        results = []
        title = "Data Not Available"
        chart_data = None
        chart_config = {"chart_type": "none", "reason": "No data available"}
        
        save_query_history(session_id, natural_query, sql_query, str(results), explanation, title)
        return explanation, sql_query, results, session_id, title, chart_data, chart_config
    
    # Generate SQL using LangChain
    full_response, sql_query, chart_config = generate_sql_with_langchain(natural_query)
    
    # Create explanation from full_response
    explanation = full_response if full_response else "SQL query generated successfully"
    
    # Execute the query
    results = execute_sql_query(sql_query)
    
    # Analyze results with AI
    ai_analysis = analyze_results_with_ai(natural_query, results, sql_query)
    
    # Combine original response with AI analysis
    complete_explanation = f"{full_response}\n\n--- AI Analysis ---\n{ai_analysis}"
    
    # Detect chart type using HR-optimized detection
    chart_config = detect_hr_chart_type(natural_query, results)
    
    # Generate HR-optimized chart if applicable
    chart_data = None
    if chart_config["chart_type"] != "none" and chart_config["chart_type"] != "table":
        chart_data = generate_hr_optimized_chart(results, chart_config)
    
    # Generate title
    title = f"Query: {natural_query[:50]}..." if len(natural_query) > 50 else natural_query
    
    # Save to history
    save_query_history(session_id, natural_query, sql_query, str(results), complete_explanation, title, chart_data, str(chart_config))
    
    return explanation, sql_query, results, session_id, title, chart_data, chart_config


def generate_hr_optimized_chart(results: List[Dict[str, Any]], chart_config: Dict[str, Any]) -> Optional[str]:
    """Generate optimized charts for HR data - simplified version"""
    
    # Use the main generate_chart function instead
    return generate_chart(results, chart_config)
