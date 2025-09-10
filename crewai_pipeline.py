"""
Optional CrewAI-based orchestration for NL -> SQL -> validation -> chart config

This module exposes a single entry point:

    run_crewai_pipeline(natural_query, db_schema, table_info, sample_data, catalog_context, catalog_summary)

It attempts to use CrewAI if installed. If CrewAI is not available or any
runtime error occurs, it falls back to a single-step LLM call that mirrors
the unified LangChain prompt logic to preserve behavior and output contract.

Output contract matches `generate_unified_ai_response`:
    (explanation: str, sql_query: str, chart_config: Dict[str, Any], data_availability: Dict[str, Any])
"""

import os
import json
import logging
import re
import difflib
from typing import Dict, Any, Tuple, List

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def _build_context(db_schema: str, table_info: str, sample_data: str, catalog_context: str, catalog_summary: str) -> str:
    """Builds the full context string consumed by agents/tasks."""
    parts = [
        "AVAILABLE TABLES AND COLUMNS:",
        db_schema or "",
        table_info or "",
        sample_data or "",
        "\nDATA CATALOGS SUMMARY:",
        catalog_summary or "",
        "\nDATA CATALOGS DETAIL:",
        catalog_context or "",
    ]
    return "\n\n".join(parts)


def _parse_table_info_to_map(table_info: str) -> Dict[str, List[str]]:
    """Parse `table_info` text into {TABLE_NAME: [COL1, COL2, ...]} (all uppercase)."""
    mapping: Dict[str, List[str]] = {}
    if not table_info:
        return mapping
    for line in table_info.splitlines():
        # Example: EMPLOYEE_DATA table has ONLY these columns: COL1, COL2, COL3
        if "table has ONLY these columns:" in line:
            try:
                parts = line.split(" table has ONLY these columns:")
                table = parts[0].strip().upper()
                cols = [c.strip().upper() for c in parts[1].split(',') if c.strip()]
                if table and cols:
                    mapping[table] = cols
            except Exception:
                continue
    return mapping


def _extract_tables_from_sql(sql: str) -> List[str]:
    """Extract table names from SQL by looking at FROM and JOIN clauses (quoted identifiers)."""
    if not sql:
        return []
    tables: List[str] = []
    patterns = [
        r'FROM\s+"([^"]+)"',
        r'JOIN\s+"([^"]+)"',
        r'FROM\s+([A-Z0-9_$#]+)',
        r'JOIN\s+([A-Z0-9_$#]+)'
    ]
    upper_sql = sql.upper()
    for pat in patterns:
        for m in re.finditer(pat, upper_sql, flags=re.IGNORECASE):
            name = m.group(1).strip().upper()
            # strip potential alias suffixes if unquoted pattern matched
            name = re.split(r'\s+', name)[0]
            if name not in tables:
                tables.append(name)
    return tables


def _extract_columns_from_sql(sql: str) -> List[str]:
    """Extract quoted column identifiers from SQL SELECT/GROUP BY clauses naively."""
    if not sql:
        return []
    cols = set()
    sql_upper = sql.upper()
    
    # Skip SELECT aliases - they are not actual columns
    # Remove AS clauses to avoid extracting aliases as columns
    sql_without_aliases = re.sub(r'\s+AS\s+"[^"]+"', '', sql_upper)
    
    # Capture quoted identifiers "IDENT" but exclude SELECT aliases
    for m in re.finditer(r'"([A-Z0-9_$#]+)"', sql_without_aliases):
        ident = m.group(1)
        # Skip common alias patterns
        if not any(alias_pattern in ident for alias_pattern in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'EMPLOYEE_COUNT', 'TOTAL']):
            cols.add(ident)
    return list(cols)


def _validate_and_autofix_sql(sql: str, schema_map: Dict[str, List[str]]) -> Tuple[str, bool, str]:
    """Validate SQL against schema. Try to auto-fix table names using fuzzy matching.

    Returns: (possibly_fixed_sql, is_valid, reason)
    """
    if not sql:
        return sql, False, "Empty SQL"

    # Basic safety rules
    if any(cmd in sql.upper() for cmd in ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "CREATE"]):
        return sql, False, "Data modification operations are not allowed"
    if "SELECT 1 FROM DUAL" in sql.upper():
        return sql, False, "Meaningless SQL"

    tables_in_sql = _extract_tables_from_sql(sql)
    if not tables_in_sql:
        return sql, False, "No tables detected in SQL"

    allowed_tables = list(schema_map.keys())
    unknown = [t for t in tables_in_sql if t not in schema_map]

    fixed_sql = sql
    fix_applied = False
    for t in unknown:
        candidates = difflib.get_close_matches(t, allowed_tables, n=1, cutoff=0.6)
        if candidates:
            best = candidates[0]
            # Replace occurrences of wrong table (quoted and unquoted)
            fixed_sql = re.sub(rf'"{re.escape(t)}"', f'"{best}"', fixed_sql, flags=re.IGNORECASE)
            fixed_sql = re.sub(rf'(?<!\")\b{re.escape(t)}\b(?!\")', f'"{best}"', fixed_sql, flags=re.IGNORECASE)
            fix_applied = True

    if fix_applied:
        tables_in_sql = _extract_tables_from_sql(fixed_sql)
        unknown = [t for t in tables_in_sql if t not in schema_map]

    if unknown:
        return fixed_sql, False, f"Unknown tables: {', '.join(unknown)}"

    # Column-level validation: try to fuzzy-map columns to the union of columns of referenced tables
    union_columns: List[str] = []
    for t in tables_in_sql:
        union_columns.extend(schema_map.get(t, []))
    union_columns = list(sorted(set(union_columns)))

    cols_in_sql = _extract_columns_from_sql(fixed_sql)
    # Detect SELECT aliases like: ... AS "ALIAS"
    alias_cols = set()
    try:
        alias_cols = set(re.findall(r'AS\s+"([A-Z0-9_$#]+)"', fixed_sql.upper()))
    except Exception:
        alias_cols = set()
    # Heuristic: ignore columns that match table names or are aliases; focus on real identifiers
    candidate_cols = [c for c in cols_in_sql if c not in tables_in_sql and c not in alias_cols]
    bad_cols = [c for c in candidate_cols if c not in union_columns]

    for c in bad_cols:
        candidates = difflib.get_close_matches(c, union_columns, n=1, cutoff=0.6)
        if candidates:
            best = candidates[0]
            fixed_sql = re.sub(rf'"{re.escape(c)}"', f'"{best}"', fixed_sql, flags=re.IGNORECASE)
            # update list
    # Recompute after replacements
    cols_in_sql = _extract_columns_from_sql(fixed_sql)
    candidate_cols = [c for c in cols_in_sql if c not in tables_in_sql]
    bad_cols = [c for c in candidate_cols if c not in union_columns]
    if bad_cols:
        return fixed_sql, False, f"Unknown columns: {', '.join(bad_cols)}"

    return fixed_sql, True, "OK"


def _apply_intent_postprocess(natural_query: str, sql_query: str, chart_config: Dict[str, Any], schema_map: Dict[str, List[str]]) -> Tuple[str, Dict[str, Any]]:
    """Lightweight intent-aware adjustments. Prefer COUNT when user asks for counts.

    Heuristics only. Keeps grouping column if present (e.g., "DEPARTMENTTYPE").
    """
    try:
        nq = (natural_query or "").lower()
        wants_count = any(k in nq for k in [
            "count", "how many", "number of", "adet", "sayısı", "sayi", "kaç"
        ])
        if not wants_count or not sql_query:
            return sql_query, chart_config

        upper_sql = sql_query.upper()
        # Identify grouping dimension from GROUP BY or first selected column (no dataset-specific names)
        group_dim = None
        m_gb = re.search(r'GROUP\s+BY\s+"([A-Z0-9_$#]+)"', upper_sql)
        if m_gb:
            group_dim = f'"{m_gb.group(1)}"'
        else:
            m_sel = re.search(r'SELECT\s+"([A-Z0-9_$#]+)"', upper_sql)
            if m_sel:
                group_dim = f'"{m_sel.group(1)}"'

        # Identify source table dynamically (no hardcoded table names)
        tables = _extract_tables_from_sql(sql_query)
        if tables:
            source_table = f'"{tables[0]}"'
        elif len(schema_map) == 1:
            source_table = f'"{next(iter(schema_map.keys()))}"'
        else:
            source_table = None

        if group_dim:
            # Replace second expression with COUNT(*) as EMPLOYEE_COUNT
            fixed = re.sub(
                rf'SELECT\s+{re.escape(group_dim)}\s*,\s*.+?\s+FROM',
                f'SELECT {group_dim}, COUNT(*) AS EMPLOYEE_COUNT FROM',
                sql_query,
                flags=re.IGNORECASE | re.DOTALL,
            )
            # Ensure GROUP BY includes the group_dim
            if re.search(r'GROUP\s+BY', fixed, flags=re.IGNORECASE):
                # leave as-is
                pass
            else:
                fixed += f' GROUP BY {group_dim}'

            # Update chart config
            group_dim_clean = group_dim.replace('"', '')
            new_cfg = dict(chart_config or {})
            new_cfg.setdefault("chart_type", "bar")
            new_cfg["title"] = new_cfg.get("title") or f"Count by {group_dim_clean}"
            new_cfg["x_column"] = group_dim_clean
            new_cfg["y_column"] = "EMPLOYEE_COUNT"
            return fixed, new_cfg
        else:
            # No group; simple total count if we can infer a table safely
            if source_table:
                fixed = f'SELECT COUNT(*) AS EMPLOYEE_COUNT FROM {source_table}'
                new_cfg = dict(chart_config or {})
                new_cfg["chart_type"] = "indicator"
                new_cfg["title"] = new_cfg.get("title") or "Total Count"
                return fixed, new_cfg
            # If we cannot infer a table, keep original SQL/config (avoid hardcoded fallbacks)
            return sql_query, chart_config
    except Exception:
        return sql_query, chart_config


def _fallback_single_step(natural_query: str, db_schema: str, table_info: str, sample_data: str, catalog_context: str, catalog_summary: str) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
    """Fallback: single LLM call returning the same JSON contract."""
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        max_tokens=4000,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Enhanced prompt with data catalog access and primary key information
    prompt = f"""
You are Aimet, an expert HR Data Analyst. You have FULL ACCESS to all data catalogs and table schemas.

USER QUERY: {{natural_query}}

DATABASE SCHEMA INFORMATION:
- You have access to 4 tables: BI_PDKS, BI_CALISAN_BILGILERI, BI_HARCIRAH_AYRINTILI_SUREC, BI_AYLIK_IZIN_KULLANIM
- SICIL_NUMARASI is the PRIMARY KEY that connects all tables
- Each table has SICIL_NUMARASI as the common identifier

TABLE STRUCTURE:
- BI_PDKS: Contains work data (IS_WEEKEND, WORK_DATE, ENTRY_TIME, EXIT_TIME, etc.) - NO GENDER column
- BI_CALISAN_BILGILERI: Contains personal data (GENDER, AD_SOYAD, DEPARTMENT, etc.) - NO IS_WEEKEND column
- BI_HARCIRAH_AYRINTILI_SUREC: Contains travel expense data
- BI_AYLIK_IZIN_KULLANIM: Contains leave data

CRITICAL JOIN RULES:
- If you need GENDER data, you MUST use BI_CALISAN_BILGILERI table
- If you need IS_WEEKEND data, you MUST use BI_PDKS table
- If you need BOTH GENDER and IS_WEEKEND, you MUST JOIN these tables on SICIL_NUMARASI

CRITICAL INSTRUCTIONS:
1. READ THE USER'S QUERY CAREFULLY - Do not assume what they want
2. ANALYZE EACH WORD in the query to understand the exact request
3. GENERATE SQL based on the ACTUAL query, not examples
4. If user asks about "işten çıkışları" (departures), look for termination/exit data
5. If user asks about "hafta sonu" (weekend), look for weekend work data
6. If user asks about "cinsiyet" (gender), use BI_CALISAN_BILGILERI table
7. If user asks about "departman" (department), use DEPARTMENT column
8. ALWAYS use JOINs when data from multiple tables is needed
9. For "korelasyon" queries, include PERCENTAGE calculations
10. NEVER use hardcoded examples - generate fresh SQL for each query

AVAILABLE TABLES AND COLUMNS:
{{context}}

Return ONLY this JSON format:
{{
    "explanation": "Brief explanation of the analysis",
    "sql_query": "SELECT statement with proper JOINs if needed",
    "chart_config": {{
        "chart_type": "bar",
        "title": "Chart title",
        "x_column": "column_name",
        "y_column": "column_name"
    }}
}}
"""

    full_context = _build_context(db_schema, table_info, sample_data, catalog_context, catalog_summary)
    rendered = prompt.replace("{{context}}", full_context).replace("{{natural_query}}", natural_query)

    response = llm.invoke(rendered)
    text = getattr(response, "content", str(response)).strip()
    # Clean common wrappers
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        parsed = json.loads(text)
    except Exception as e:
        logger.error(f"CrewAI fallback JSON parse failed: {e}\nRaw: {text}")
        # Provide meaningful error contract
        return (
            "AI response parsing failed in fallback pipeline.",
            "SELECT COUNT(*) as error_count FROM BI_CALISAN_BILGILERI WHERE 1=0",
            {"chart_type": "none", "reason": "AI parsing error"},
            {"available": False, "reason": "AI parsing error"}
        )

    explanation = parsed.get("explanation", "Query executed successfully")
    sql_query = parsed.get("sql_query", "")
    chart_config = parsed.get("chart_config", {"chart_type": "bar"})

    # Validate against schema map derived from table_info
    schema_map = _parse_table_info_to_map(table_info)
    sql_query, valid, reason = _validate_and_autofix_sql(sql_query, schema_map)
    if not valid:
        return (
            f"AI generated invalid SQL: {reason}",
            "SELECT COUNT(*) as error_count FROM BI_CALISAN_BILGILERI WHERE 1=0",
            {"chart_type": "none", "reason": reason},
            {"available": False, "reason": reason}
        )

    # Intent-aware postprocess (prefer COUNT when asked)
    sql_query, chart_config = _apply_intent_postprocess(natural_query, sql_query, chart_config, schema_map)

    if not sql_query or "SELECT 1 FROM DUAL" in sql_query.upper():
        return (
            "AI generated invalid SQL query.",
            "SELECT COUNT(*) as error_count FROM BI_CALISAN_BILGILERI WHERE 1=0",
            {"chart_type": "none", "reason": "Invalid SQL"},
            {"available": False, "reason": "Invalid SQL"}
        )

    return explanation, sql_query, chart_config, {"available": True, "reason": "Data appears to be available"}


def run_crewai_pipeline(
    natural_query: str,
    db_schema: str,
    table_info: str,
    sample_data: str,
    catalog_context: str,
    catalog_summary: str
) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
    """Run the CrewAI-based pipeline if available; otherwise fallback.

    Returns (explanation, sql_query, chart_config, data_availability)
    """
    # Force fallback to single-step for debugging JOIN issues
    logger.info("Forcing fallback to single-step for debugging JOIN issues.")
    return _fallback_single_step(natural_query, db_schema, table_info, sample_data, catalog_context, catalog_summary)
    
    try:
        # Lazy import so that the project runs without CrewAI installed
        from crewai import Agent, Task, Crew, Process
    except Exception as e:
        logger.warning(f"CrewAI not available or failed to import: {e}. Falling back to single-step.")
        return _fallback_single_step(natural_query, db_schema, table_info, sample_data, catalog_context, catalog_summary)

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        max_tokens=4000,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    full_context = _build_context(db_schema, table_info, sample_data, catalog_context, catalog_summary)

    catalog_analyst = Agent(
        role="Catalog Analyst",
        goal="Understand available HR data and summarize relevant tables/columns for the user's query.",
        backstory="Experienced HR data analyst specializing in data catalogs and schema comprehension.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )

    sql_architect = Agent(
        role="SQL Architect",
        goal="Design valid Oracle SQL that answers the user's HR analytics question using only existing tables/columns.",
        backstory="Senior analytics engineer with deep SQL expertise.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )

    validator = Agent(
        role="SQL Validator",
        goal="Validate and, if necessary, minimally fix the JSON {explanation, sql_query, chart_config} according to rules.",
        backstory="Quality engineer ensuring safety and schema adherence.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )

    schema_map = _parse_table_info_to_map(table_info)
    allowed_tables_list = ", ".join(schema_map.keys()) if schema_map else ""

    analysis_task = Task(
        description=(
            "Summarize what parts of the context are relevant to the user's question.\n"
            "Focus on table and column names likely needed. Return a concise paragraph."
        ),
        agent=catalog_analyst,
        expected_output="A short relevance summary.",
        context={"context": full_context, "natural_query": natural_query},
    )

    sql_task = Task(
        description=(
            "Using the relevance summary and full context, produce ONLY this JSON (no markdown):\n"
            "{\n  \"explanation\": \"...\",\n  \"sql_query\": \"...\",\n  \"chart_config\": {\n    \"chart_type\": \"bar|line|pie|table\",\n    \"title\": \"...\",\n    \"x_column\": \"...\",\n    \"y_column\": \"...\"\n  }\n}\n\n"
            "Rules: use double quotes for identifiers, no semicolon, never SELECT 1 FROM DUAL, use only existing tables/columns, avoid SELECT *.\n"
            f"Allowed tables: {allowed_tables_list}\n"
            "CRITICAL JOIN RULES:\n"
            "- BI_PDKS: Contains work data (IS_WEEKEND, WORK_DATE, ENTRY_TIME, EXIT_TIME, etc.) - NO GENDER column\n"
            "- BI_CALISAN_BILGILERI: Contains personal data (GENDER, AD_SOYAD, DEPARTMENT, etc.) - NO IS_WEEKEND column\n"
            "- BI_HARCIRAH_AYRINTILI_SUREC: Contains travel expense data\n"
            "- BI_AYLIK_IZIN_KULLANIM: Contains leave data\n"
            "- SICIL_NUMARASI is the PRIMARY KEY that connects all tables\n"
            "- If you need GENDER data, you MUST use BI_CALISAN_BILGILERI table\n"
            "- If you need IS_WEEKEND data, you MUST use BI_PDKS table\n"
            "- If you need BOTH GENDER and IS_WEEKEND, you MUST JOIN these tables on SICIL_NUMARASI\n"
            "EXAMPLE FOR 'hafta sonu çalışma oranları cinsiyetlere göre':\n"
            "SELECT BI_CALISAN_BILGILERI.GENDER, COUNT(*) AS WEEKEND_COUNT \n"
            "FROM BI_PDKS \n"
            "JOIN BI_CALISAN_BILGILERI ON BI_PDKS.SICIL_NUMARASI = BI_CALISAN_BILGILERI.SICIL_NUMARASI \n"
            "WHERE BI_PDKS.IS_WEEKEND = 'True' \n"
            "GROUP BY BI_CALISAN_BILGILERI.GENDER"
        ),
        agent=sql_architect,
        expected_output="Strict JSON with explanation, sql_query, chart_config.",
    )

    validate_task = Task(
        description=(
            "Validate the previous JSON against rules. If any violation, fix minimally and return the corrected JSON only.\n"
            f"Ensure all referenced tables belong to this set: {allowed_tables_list}."
        ),
        agent=validator,
        expected_output="Final strict JSON with explanation, sql_query, chart_config.",
    )

    crew = Crew(
        agents=[catalog_analyst, sql_architect, validator],
        tasks=[analysis_task, sql_task, validate_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        result = crew.kickoff(inputs={"context": full_context, "natural_query": natural_query})
        text = str(result).strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        parsed = json.loads(text)
        explanation = parsed.get("explanation", "Query executed successfully")
        sql_query = parsed.get("sql_query", "")
        chart_config = parsed.get("chart_config", {"chart_type": "bar"})

        # Schema-aware validation and auto-fix
        sql_query, valid, reason = _validate_and_autofix_sql(sql_query, schema_map)
        if not valid:
            raise ValueError(f"SQL failed validation: {reason}")

        # Intent-aware postprocess (prefer COUNT when asked)
        sql_query, chart_config = _apply_intent_postprocess(natural_query, sql_query, chart_config, schema_map)

        return explanation, sql_query, chart_config, {"available": True, "reason": "Data appears to be available"}
    except Exception as e:
        logger.error(f"CrewAI pipeline failed: {e}. Falling back to single-step.")
        return _fallback_single_step(natural_query, db_schema, table_info, sample_data, catalog_context, catalog_summary)


