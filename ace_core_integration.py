"""
ACE Core Integration for txt-to-sql project
Adaptive Context Engineering for SQL generation and ruleset management
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

# Add ACE Core to path (assuming it's installed or in parent directory)
try:
    # Try importing from installed package
    from ace_core import ACEFramework
    from ace_core.metadata import ItemType
except ImportError:
    # Try importing from local capstone project
    capstone_path = Path(__file__).parent.parent / "capstone"
    if capstone_path.exists():
        sys.path.insert(0, str(capstone_path))
        from ace_core import ACEFramework
        from ace_core.metadata import ItemType
    else:
        raise ImportError("ACE Core not found. Install with: pip install git+https://github.com/ahmetererr/ace_lib.git")

logger = logging.getLogger(__name__)


class SQLGenerationACE:
    """
    ACE Core integration for SQL generation
    Learns from queries and maintains ruleset knowledge
    """
    
    def __init__(self, ruleset_dir: str = "ruleset", ace_state_file: str = "ace_sql_state.json"):
        """
        Initialize ACE integration
        
        Args:
            ruleset_dir: Directory containing ruleset JSON files
            ace_state_file: File to save/load ACE state
        """
        self.ruleset_dir = Path(ruleset_dir)
        self.ace_state_file = ace_state_file
        
        # Initialize ACE Framework
        if os.path.exists(ace_state_file):
            logger.info(f"Loading ACE state from {ace_state_file}")
            self.ace = ACEFramework.load_state(ace_state_file, llm_client=None)
        else:
            logger.info("Initializing new ACE Framework")
            self.ace = ACEFramework()
            self._initialize_with_rulesets()
        
        logger.info(f"ACE Framework initialized: {self.ace.framework_id}")
    
    def _initialize_with_rulesets(self):
        """Load initial ruleset rules into ACE Manual"""
        logger.info("Loading rulesets into ACE Manual...")
        
        # Load çalışan ruleset
        calisan_path = self.ruleset_dir / "calisan_ruleset_v1.2.1.json"
        if calisan_path.exists():
            with open(calisan_path, 'r', encoding='utf-8') as f:
                ruleset = json.load(f)
                self._add_ruleset_to_manual(ruleset, "calisan")
        
        # Load izin ruleset
        izin_path = self.ruleset_dir / "izin_ruleset_v3.2.1.json"
        if izin_path.exists():
            with open(izin_path, 'r', encoding='utf-8') as f:
                ruleset = json.load(f)
                self._add_ruleset_to_manual(ruleset, "izin")
        
        logger.info(f"Loaded rulesets into ACE Manual. Total items: {self.ace.manual.get_statistics()['total_items']}")
    
    def _add_ruleset_to_manual(self, ruleset: Dict, ruleset_type: str):
        """Add ruleset rules to ACE Manual"""
        
        # Add table definitions as constraints
        if "tables" in ruleset:
            for table_info in ruleset["tables"]:
                table_name = table_info.get("table", "")
                primary_key = table_info.get("primary_key", "")
                
                # Add table constraint
                self.ace.add_manual_item(
                    content=f"Table {table_name} has primary key: {primary_key}",
                    item_type=ItemType.CONSTRAINT,
                    tags=["sql", "schema", ruleset_type, table_name.lower()],
                    confidence=0.95,
                    created_by="ruleset_loader"
                )
                
                # Add column information
                if "columns" in table_info:
                    for col in table_info["columns"]:
                        col_name = col.get("name", "")
                        col_type = col.get("type", "")
                        col_desc = col.get("description", "")
                        
                        constraint_text = f"Column {table_name}.{col_name} is {col_type}"
                        if col_desc:
                            constraint_text += f" - {col_desc}"
                        
                        self.ace.add_manual_item(
                            content=constraint_text,
                            item_type=ItemType.CONSTRAINT,
                            tags=["sql", "schema", ruleset_type, table_name.lower(), col_name.lower()],
                            confidence=0.95,
                            created_by="ruleset_loader"
                        )
        
        # Add business rules as instructions
        if "business_rules" in ruleset:
            for rule_name, rule_content in ruleset["business_rules"].items():
                if isinstance(rule_content, dict):
                    rule_text = f"{rule_name}: {json.dumps(rule_content, ensure_ascii=False, indent=2)}"
                else:
                    rule_text = f"{rule_name}: {rule_content}"
                
                self.ace.add_manual_item(
                    content=rule_text,
                    item_type=ItemType.INSTRUCTION,
                    tags=["sql", "business_rule", ruleset_type, rule_name],
                    confidence=0.9,
                    created_by="ruleset_loader"
                )
    
    def get_sql_context(self, query_type: Optional[str] = None, max_items: int = 20) -> str:
        """
        Get relevant context from ACE Manual for SQL generation
        
        Args:
            query_type: Type of query (e.g., "employee_count", "department_analysis")
            max_items: Maximum number of manual items to include
            
        Returns:
            Context string for LLM
        """
        # Get relevant items
        items = self.ace.manual.get_active_items()
        
        # Filter by query type tags if provided
        if query_type:
            type_items = [item for item in items 
                         if any(tag in (item.metadata.tags if item.metadata else []) 
                               for tag in [query_type, "sql", "schema"])]
            items = type_items
        
        # Prioritize by usage and confidence
        if items:
            items = sorted(
                items,
                key=lambda x: (
                    x.metadata.confidence_score if x.metadata else 0,
                    x.metadata.usage_count if x.metadata else 0
                ),
                reverse=True
            )
            items = items[:max_items]
        
        # Build context string
        context_parts = ["=== SQL Generation Context ==="]
        context_parts.append(f"Query Type: {query_type or 'general'}")
        context_parts.append("")
        context_parts.append("Relevant Rules and Constraints:")
        
        for item in items:
            item_type = item.metadata.item_type.value if item.metadata else "item"
            tags = ", ".join(item.metadata.tags) if item.metadata else ""
            context_parts.append(f"[{item_type.upper()}] {item.content}")
            if tags:
                context_parts.append(f"  Tags: {tags}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def learn_from_query(self, 
                        natural_query: str,
                        generated_sql: str,
                        executed_sql: Optional[str] = None,
                        success: bool = True,
                        execution_feedback: Optional[Dict] = None,
                        query_type: Optional[str] = None):
        """
        Learn from a query execution using ACE cycle
        
        Args:
            natural_query: Original natural language query
            generated_sql: SQL query generated by LLM
            executed_sql: SQL query that was actually executed (may differ)
            success: Whether query execution was successful
            execution_feedback: Additional feedback (error messages, execution time, etc.)
            query_type: Type of query for categorization
        """
        logger.info(f"Learning from query: {natural_query[:50]}... (success={success})")
        
        # Build execution trace
        generation_trace = {
            "task": f"Generate SQL for: {natural_query}",
            "response": generated_sql,
            "reasoning": f"Generated SQL query based on query type: {query_type}",
            "used_items": [],
            "trace": {
                "query_type": query_type,
                "natural_query": natural_query,
                "generated_sql": generated_sql,
                "executed_sql": executed_sql or generated_sql,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Build execution feedback
        if execution_feedback is None:
            execution_feedback = {}
        
        if not success:
            execution_feedback["error"] = execution_feedback.get("error", "Query execution failed")
        
        # Execute ACE cycle: Reflect and Curate
        insights = self.ace.reflect_only(
            generation_trace=generation_trace,
            execution_feedback=execution_feedback,
            success=success
        )
        
        # Add query type tag to insights
        if query_type:
            for insight in insights:
                insight.tags.append(query_type)
                insight.tags.append("sql_query")
        
        # Curate insights
        if insights:
            curation_result = self.ace.curate_only(insights)
            logger.info(f"Learned {curation_result['summary']['applied']} insights from query")
            
            # Save state after learning
            self.save_state()
    
    def save_state(self):
        """Save ACE state to file"""
        try:
            self.ace.export_state(self.ace_state_file)
            logger.debug(f"ACE state saved to {self.ace_state_file}")
        except Exception as e:
            logger.error(f"Error saving ACE state: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ACE statistics"""
        stats = self.ace.get_statistics()
        
        # Add SQL-specific statistics
        sql_items = self.ace.manual.get_items_by_tag("sql")
        business_rules = self.ace.manual.get_items_by_tag("business_rule")
        constraints = self.ace.manual.get_items_by_type(ItemType.CONSTRAINT)
        
        stats["sql_specific"] = {
            "sql_items": len(sql_items),
            "business_rules": len(business_rules),
            "constraints": len(constraints),
            "learned_patterns": len(self.ace.manual.get_items_by_type(ItemType.INSIGHT))
        }
        
        return stats
    
    def search_sql_patterns(self, query: str) -> List[Any]:
        """Search for SQL-related patterns in manual"""
        return self.ace.search_manual(query, tags=["sql"])
    
    def get_learned_patterns(self, query_type: Optional[str] = None) -> List[Any]:
        """Get learned SQL patterns"""
        items = self.ace.manual.get_items_by_type(ItemType.INSIGHT)
        
        if query_type:
            items = [item for item in items 
                    if query_type in (item.metadata.tags if item.metadata else [])]
        
        return items


# Global instance
_ace_instance: Optional[SQLGenerationACE] = None


def get_ace_instance(ruleset_dir: str = "ruleset") -> SQLGenerationACE:
    """Get or create ACE instance"""
    global _ace_instance
    if _ace_instance is None:
        _ace_instance = SQLGenerationACE(ruleset_dir=ruleset_dir)
    return _ace_instance


def initialize_ace_integration(ruleset_dir: str = "ruleset") -> SQLGenerationACE:
    """Initialize ACE integration"""
    global _ace_instance
    _ace_instance = SQLGenerationACE(ruleset_dir=ruleset_dir)
    return _ace_instance
