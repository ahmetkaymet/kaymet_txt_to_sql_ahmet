"""
CrewAI-based Thought of Chain implementation for HR Analytics
This module provides CrewAI-based multi-agent system for natural language to SQL conversion
with business rules enforcement and intent detection.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Query type classification"""
    EMPLOYEE_COUNT = "employee_count"
    DEPARTMENT_ANALYSIS = "department_analysis"
    LEAVE_ANALYSIS = "leave_analysis"
    TURNOVER_ANALYSIS = "turnover_analysis"
    PERSON_LOOKUP = "person_lookup"
    EDUCATION_ANALYSIS = "education_analysis"
    GENDER_ANALYSIS = "gender_analysis"
    SERVICE_ANALYSIS = "service_analysis"
    GENERAL_ANALYSIS = "general_analysis"

@dataclass
class QueryContext:
    """Context information for query processing"""
    natural_query: str
    query_type: QueryType
    detected_intent: Optional[str] = None
    target_tables: List[str] = None
    target_columns: List[str] = None
    business_rules: List[str] = None
    sql_query: Optional[str] = None
    explanation: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None

class RulesetManager:
    """Manages ruleset loading and business rules extraction"""
    
    def __init__(self):
        self.calisan_ruleset = None
        self.izin_ruleset = None
        self._load_rulesets()
    
    def _load_rulesets(self):
        """Load ruleset files"""
        try:
            # Load çalışan ruleset
            calisan_path = Path("ruleset/calisan_ruleset_v1.2.1.json")
            if calisan_path.exists():
                with open(calisan_path, 'r', encoding='utf-8') as f:
                    self.calisan_ruleset = json.load(f)
            
            # Load izin ruleset
            izin_path = Path("ruleset/izin_ruleset_v3.2.1.json")
            if izin_path.exists():
                with open(izin_path, 'r', encoding='utf-8') as f:
                    self.izin_ruleset = json.load(f)
                    
            logger.info("Rulesets loaded successfully")
        except Exception as e:
            logger.error(f"Error loading rulesets: {e}")
    
    def get_business_rules_for_query(self, query_type: QueryType) -> List[Dict[str, Any]]:
        """Get relevant business rules for query type"""
        rules = []
        
        if self.calisan_ruleset:
            business_rules = self.calisan_ruleset.get("business_rules", {})
            
            # Add rules based on query type
            if query_type in [QueryType.EMPLOYEE_COUNT, QueryType.DEPARTMENT_ANALYSIS]:
                if "active_employee_definition" in business_rules:
                    rules.append(business_rules["active_employee_definition"])
                if "string_normalization" in business_rules:
                    rules.append(business_rules["string_normalization"])
            
            if query_type == QueryType.TURNOVER_ANALYSIS:
                if "turnover_analysis" in business_rules:
                    rules.append(business_rules["turnover_analysis"])
            
            if query_type == QueryType.PERSON_LOOKUP:
                if "name_based_lookup_join" in business_rules:
                    rules.append(business_rules["name_based_lookup_join"])
                if "identity_matching" in business_rules:
                    rules.append(business_rules["identity_matching"])
        
        if self.izin_ruleset and query_type == QueryType.LEAVE_ANALYSIS:
            business_rules = self.izin_ruleset.get("business_rules", {})
            if "leave_usage" in business_rules:
                rules.append(business_rules["leave_usage"])
            if "leave_types_split" in business_rules:
                rules.append(business_rules["leave_types_split"])
            if "leave_inclusion_policies" in business_rules:
                rules.append(business_rules["leave_inclusion_policies"])
        
        return rules
    
    def get_table_schemas_info(self) -> str:
        """Get comprehensive table schemas from rulesets"""
        schema_info = []
        
        # Add çalışan table schema
        if self.calisan_ruleset and 'tables' in self.calisan_ruleset:
            for table in self.calisan_ruleset['tables']:
                table_name = table.get('table', 'Unknown')
                primary_key = table.get('primary_key', 'None')
                columns = table.get('columns', [])
                
                schema_info.append(f"Table: {table_name}")
                schema_info.append(f"Primary Key: {primary_key}")
                schema_info.append("Columns:")
                for col in columns:
                    col_name = col.get('name', 'Unknown')
                    col_type = col.get('type', 'Unknown')
                    col_desc = col.get('description', 'No description')
                    schema_info.append(f"  - {col_name} ({col_type}): {col_desc}")
                schema_info.append("")
        
        # Add izin table schema
        if self.izin_ruleset and 'tables' in self.izin_ruleset:
            for table in self.izin_ruleset['tables']:
                table_name = table.get('table', 'Unknown')
                primary_key = table.get('primary_key', 'None')
                foreign_keys = table.get('foreign_keys', [])
                columns = table.get('columns', [])
                
                schema_info.append(f"Table: {table_name}")
                schema_info.append(f"Primary Key: {primary_key}")
                if foreign_keys:
                    schema_info.append("Foreign Keys:")
                    for fk in foreign_keys:
                        fk_col = fk.get('column', 'Unknown')
                        fk_ref = fk.get('references', 'Unknown')
                        fk_notes = fk.get('notes', '')
                        schema_info.append(f"  - {fk_col} -> {fk_ref} ({fk_notes})")
                schema_info.append("Columns:")
                for col in columns:
                    col_name = col.get('name', 'Unknown')
                    col_type = col.get('type', 'Unknown')
                    col_desc = col.get('description', 'No description')
                    examples = col.get('examples', [])
                    if examples:
                        col_desc += f" (Examples: {', '.join(map(str, examples[:3]))})"
                    schema_info.append(f"  - {col_name} ({col_type}): {col_desc}")
                schema_info.append("")
        
        return "\n".join(schema_info)
    
    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get table schema from rulesets"""
        if table_name == "BI_CALISAN_BILGILERI" and self.calisan_ruleset:
            tables = self.calisan_ruleset.get("tables", [])
            for table in tables:
                if table.get("table") == table_name:
                    return table
        
        if table_name == "BI_AYLIK_IZIN_KULLANIM" and self.izin_ruleset:
            tables = self.izin_ruleset.get("tables", [])
            for table in tables:
                if table.get("table") == table_name:
                    return table
        
        return None

class MainRouter:
    """Main router that classifies queries and coordinates crews"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.ruleset_manager = RulesetManager()
    
    def classify_query(self, natural_query: str) -> QueryType:
        """Classify the natural language query"""
        
        classification_prompt = PromptTemplate(
            input_variables=["query"],
            template="""
            You are an expert HR data analyst. Classify the following natural language query into one of these categories:
            
            - employee_count: Questions about counting employees (e.g., "How many employees?", "Employee count by department")
            - department_analysis: Questions about department distribution or analysis
            - leave_analysis: Questions about leave usage, vacation, time off
            - turnover_analysis: Questions about employee turnover, attrition, exit rates
            - person_lookup: Questions about specific person/employee information
            - education_analysis: Questions about education levels, qualifications
            - gender_analysis: Questions about gender distribution
            - service_analysis: Questions about years of service, tenure
            - general_analysis: Other general HR analytics questions
            
            Query: {query}
            
            Return ONLY the category name, nothing else.
            """
        )
        
        chain = classification_prompt | self.llm
        result = chain.invoke({"query": natural_query})
        
        # Handle AIMessage object
        if hasattr(result, 'content'):
            result_text = result.content
        else:
            result_text = str(result)
        
        try:
            return QueryType(result_text.strip().lower())
        except ValueError:
            logger.warning(f"Unknown query type: {result_text}, defaulting to general_analysis")
            return QueryType.GENERAL_ANALYSIS
    
    def create_query_context(self, natural_query: str) -> QueryContext:
        """Create query context with classification"""
        query_type = self.classify_query(natural_query)
        
        return QueryContext(
            natural_query=natural_query,
            query_type=query_type,
            target_tables=[],
            target_columns=[],
            business_rules=[]
        )

class TableAnalysisCrew:
    """Crew responsible for determining which tables and columns to use"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.ruleset_manager = RulesetManager()
    
    def create_agent(self) -> Agent:
        """Create table analysis agent"""
        return Agent(
            role="HR Database Schema Expert",
            goal="Determine the most appropriate tables and columns for HR analytics queries",
            backstory=f"""You are an expert HR database analyst with deep knowledge of HR data structures and Oracle SQL syntax.
            You understand the relationships between employee data, leave data, and organizational structures.
            You always choose the most efficient and accurate tables and columns for any HR query.
            
            COMPLETE TABLE SCHEMAS FROM RULESET:
            {self.ruleset_manager.get_table_schemas_info()}
            
            CRITICAL REQUIREMENTS:
            - Current year: {datetime.now().year} (NOT hardcoded, use dynamic)
            - Date format: TO_DATE('01-JAN-{datetime.now().year}', 'DD-MON-YYYY')
            - NEVER use semicolon (;) at end of SQL
            - Use YILI = {datetime.now().year} for current year filtering in BI_AYLIK_IZIN_KULLANIM
            - String matching: Use UPPER() and TRIM() for Turkish characters""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_task(self, context: QueryContext) -> Task:
        """Create table analysis task"""
        
        # Get available tables from rulesets
        available_tables = []
        if self.ruleset_manager.calisan_ruleset:
            tables = self.ruleset_manager.calisan_ruleset.get("tables", [])
            for table in tables:
                available_tables.append(f"- {table.get('table')}: {table.get('columns', [])}")
        
        if self.ruleset_manager.izin_ruleset:
            tables = self.ruleset_manager.izin_ruleset.get("tables", [])
            for table in tables:
                available_tables.append(f"- {table.get('table')}: {table.get('columns', [])}")
        
        return Task(
            description=f"""
            Analyze the following HR query and determine which tables and columns should be used:
            
            Query: {context.natural_query}
            Query Type: {context.query_type.value}
            
            Available Tables and Columns:
            {chr(10).join(available_tables)}
            
            Based on the query type and available schema, determine:
            1. Which table(s) should be used
            2. Which specific columns are needed
            3. Any joins that might be required
            
            Return your analysis in JSON format:
            {{
                "target_tables": ["table1", "table2"],
                "target_columns": ["column1", "column2"],
                "joins_required": ["table1.column = table2.column"],
                "reasoning": "Explanation of your choices"
            }}
            """,
            agent=self.create_agent(),
            expected_output="JSON object with table and column analysis"
        )

class BusinessRulesCrew:
    """Crew responsible for applying business rules from rulesets"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.ruleset_manager = RulesetManager()
    
    def create_agent(self) -> Agent:
        """Create business rules agent"""
        return Agent(
            role="HR Business Rules Expert",
            goal="Apply HR business rules and constraints to ensure accurate and compliant data analysis",
            backstory="""You are an expert HR business analyst with deep knowledge of HR policies, 
            employment laws, and business rules. You ensure all HR analytics follow proper business logic,
            data privacy rules, and organizational policies. You never compromise on data accuracy and compliance.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_task(self, context: QueryContext) -> Task:
        """Create business rules task"""
        
        # Get relevant business rules
        business_rules = self.ruleset_manager.get_business_rules_for_query(context.query_type)
        
        rules_text = ""
        for rule in business_rules:
            rules_text += f"\nRule: {rule.get('description', 'No description')}\n"
            if 'rules' in rule:
                for r in rule['rules']:
                    rules_text += f"  - {r}\n"
            if 'formulas' in rule:
                for name, formula in rule['formulas'].items():
                    rules_text += f"  {name}: {formula}\n"
            if 'sql_snippets' in rule:
                for name, sql in rule['sql_snippets'].items():
                    rules_text += f"  {name}: {sql}\n"
        
        return Task(
            description=f"""
            Apply HR business rules to the following query context:
            
            Query: {context.natural_query}
            Query Type: {context.query_type.value}
            Target Tables: {context.target_tables}
            Target Columns: {context.target_columns}
            
            Relevant Business Rules:
            {rules_text}
            
            Based on the business rules above, determine:
            1. Which business rules apply to this query
            2. How to modify the query to comply with these rules
            3. Any additional constraints or filters needed
            4. Data privacy and security considerations
            
            Return your analysis in JSON format:
            {{
                "applicable_rules": ["rule1", "rule2"],
                "required_filters": ["filter1", "filter2"],
                "constraints": ["constraint1", "constraint2"],
                "sql_modifications": "Specific SQL modifications needed",
                "compliance_notes": "Any compliance or privacy considerations"
            }}
            """,
            agent=self.create_agent(),
            expected_output="JSON object with business rules analysis"
        )

class IntentDetectionCrew:
    """Crew responsible for detecting user intent and clarifying ambiguous queries"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def create_agent(self) -> Agent:
        """Create intent detection agent"""
        return Agent(
            role="HR Query Intent Specialist",
            goal="Detect user intent and clarify ambiguous HR queries to ensure accurate results",
            backstory="""You are an expert in understanding HR-related queries and user intentions.
            You excel at identifying what users really want to know from their HR data questions.
            You always ask for clarification when queries are ambiguous to ensure 99% accuracy.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_task(self, context: QueryContext) -> Task:
        """Create intent detection task"""
        
        return Task(
            description=f"""
            Analyze the following HR query to detect user intent and identify any ambiguities:
            
            Query: {context.natural_query}
            Query Type: {context.query_type.value}
            
            Common HR intents include:
            - employee_counts: Counting employees, headcount analysis
            - department_distribution: Department-wise employee distribution
            - education_breakdown: Education level analysis
            - leave_usage: Leave/vacation usage patterns
            - leave_leaders: Top leave users
            - turnover_analysis: Employee turnover and attrition
            - hiring_and_attrition: Recruitment and exit patterns
            - person_lookup: Finding specific employee information
            
            Analyze the query and determine:
            1. What is the primary intent?
            2. Are there any ambiguities that need clarification?
            3. What specific information is the user seeking?
            4. Are there any missing parameters (time period, department, etc.)?
            
            Return your analysis in JSON format:
            {{
                "detected_intent": "primary_intent_name",
                "confidence": 0.95,
                "ambiguities": ["ambiguity1", "ambiguity2"],
                "missing_parameters": ["param1", "param2"],
                "clarification_questions": ["question1", "question2"],
                "refined_query": "Clarified version of the query"
            }}
            """,
            agent=self.create_agent(),
            expected_output="JSON object with intent analysis"
        )

class ResponseGeneratorCrew:
    """Crew responsible for generating final SQL and response"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.ruleset_manager = RulesetManager()
    
    def create_agent(self) -> Agent:
        """Create response generator agent"""
        return Agent(
            role="HR SQL Query Generator",
            goal="Generate accurate, efficient, and compliant SQL queries for HR analytics",
            backstory=f"""You are an expert SQL developer specializing in HR analytics and Oracle SQL syntax.
            You create optimized, secure, and business-rule-compliant SQL queries.
            You always follow best practices for data privacy and query performance.
            
            COMPLETE TABLE SCHEMAS FROM RULESET:
            {self.ruleset_manager.get_table_schemas_info()}
            
            CRITICAL REQUIREMENTS:
            - Current year: {datetime.now().year} (NOT hardcoded, use dynamic)
            - Date format: TO_DATE('01-JAN-{datetime.now().year}', 'DD-MON-YYYY')
            - NEVER use semicolon (;) at end of SQL
            - Use YILI = {datetime.now().year} for current year filtering in BI_AYLIK_IZIN_KULLANIM
            - String matching: Use UPPER() and TRIM() for Turkish characters""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_task(self, context: QueryContext, table_analysis: str, business_rules: str, intent_analysis: str) -> Task:
        """Create response generator task"""
        
        return Task(
            description=f"""
            Generate the final SQL query and response based on the analysis from all crews:
            
            Original Query: {context.natural_query}
            Query Type: {context.query_type.value}
            
            Table Analysis Results:
            {table_analysis}
            
            Business Rules Analysis:
            {business_rules}
            
            Intent Analysis:
            {intent_analysis}
            
            Generate:
            1. A complete, executable Oracle SQL query (use {datetime.now().year} for current year, use YILI = {datetime.now().year} for BI_AYLIK_IZIN_KULLANIM table, NEVER use semicolon at the end)
            2. A detailed explanation of the query
            3. Chart configuration for visualization
            4. Any important notes or warnings
            
            CRITICAL: Use the EXACT table and column names from the ruleset schemas above. 
            Pay special attention to foreign key relationships and column descriptions.
            
            Return your response in JSON format:
            {{
                "sql_query": "Complete SQL query",
                "explanation": "Detailed explanation of the query and analysis",
                "chart_config": {{
                    "chart_type": "bar|line|pie|table",
                    "title": "Chart title",
                    "x_column": "x-axis column",
                    "y_column": "y-axis column"
                }},
                "notes": ["note1", "note2"],
                "warnings": ["warning1", "warning2"]
            }}
            """,
            agent=self.create_agent(),
            expected_output="JSON object with complete SQL query and response"
        )

class CrewAIOrchestrator:
    """Main orchestrator that coordinates all crews"""
    
    def __init__(self):
        self.main_router = MainRouter()
        self.table_crew = TableAnalysisCrew()
        self.business_rules_crew = BusinessRulesCrew()
        self.intent_crew = IntentDetectionCrew()
        self.response_crew = ResponseGeneratorCrew()
    
    def get_current_year(self) -> int:
        """Get current year dynamically"""
        return datetime.now().year
    
    def process_query(self, natural_query: str) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """Process natural language query using CrewAI thought of chain"""
        
        logger.info(f"Processing query with CrewAI: {natural_query}")
        
        # Step 1: Create query context
        context = self.main_router.create_query_context(natural_query)
        
        # Step 2: Create tasks for parallel execution
        table_task = self.table_crew.create_task(context)
        business_rules_task = self.business_rules_crew.create_task(context)
        intent_task = self.intent_crew.create_task(context)
        
        # Step 3: Execute table analysis and business rules in parallel
        table_crew = Crew(
            agents=[self.table_crew.create_agent()],
            tasks=[table_task],
            process=Process.sequential,
            verbose=True
        )
        
        business_rules_crew = Crew(
            agents=[self.business_rules_crew.create_agent()],
            tasks=[business_rules_task],
            process=Process.sequential,
            verbose=True
        )
        
        intent_crew = Crew(
            agents=[self.intent_crew.create_agent()],
            tasks=[intent_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Execute crews in parallel
        logger.info("Executing table analysis, business rules, and intent detection crews...")
        table_result = table_crew.kickoff()
        business_rules_result = business_rules_crew.kickoff()
        intent_result = intent_crew.kickoff()
        
        # Step 4: Generate final response
        response_task = self.response_crew.create_task(
            context, 
            str(table_result), 
            str(business_rules_result), 
            str(intent_result)
        )
        
        response_crew = Crew(
            agents=[self.response_crew.create_agent()],
            tasks=[response_task],
            process=Process.sequential,
            verbose=True
        )
        
        logger.info("Generating final response...")
        final_result = response_crew.kickoff()
        
        # Parse final result
        try:
            import json
            
            # Handle different result types from CrewAI
            if hasattr(final_result, 'raw'):
                result_text = final_result.raw
            elif hasattr(final_result, 'content'):
                result_text = final_result.content
            else:
                result_text = str(final_result)
            
            logger.info(f"Final result text: {result_text}")
            
            # Try to extract JSON from the result
            if "{" in result_text and "}" in result_text:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                json_str = result_text[json_start:json_end]
                result_data = json.loads(json_str)
            else:
                # If no JSON found, create a basic response
                result_data = {
                    "explanation": f"CrewAI processed query: {natural_query}",
                    "sql_query": "SELECT 'CrewAI processing completed' AS message FROM DUAL",
                    "chart_config": {"chart_type": "bar", "title": "CrewAI Result"}
                }
            
            explanation = result_data.get("explanation", "Query processed successfully")
            sql_query = result_data.get("sql_query", "")
            chart_config = result_data.get("chart_config", {"chart_type": "bar"})
            data_availability = {"available": True, "reason": "Data appears to be available"}
            
            logger.info("CrewAI processing completed successfully")
            return explanation, sql_query, chart_config, data_availability
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing CrewAI result: {e}")
            logger.error(f"Raw result: {final_result}")
            # Fallback response
            return (
                "CrewAI processing completed but result parsing failed",
                "SELECT 'CrewAI processing error - please try again' AS message FROM DUAL",
                {"chart_type": "none", "reason": "Processing error"},
                {"available": False, "reason": "Processing error"}
            )

def create_crew_ai_pipeline():
    """Create CrewAI pipeline for HR analytics"""
    return CrewAIOrchestrator()

def process_query_with_crew_ai(natural_query: str) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
    """Process natural language query using CrewAI"""
    orchestrator = create_crew_ai_pipeline()
    return orchestrator.process_query(natural_query)