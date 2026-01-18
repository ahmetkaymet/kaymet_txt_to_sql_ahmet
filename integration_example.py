"""
Example integration of ACE Core with txt-to-sql project
Demonstrates how to use ACE for learning SQL generation patterns
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ace_core_integration import get_ace_instance, initialize_ace_integration
from langchain_utils import process_natural_query_langchain, execute_sql_query
from crew_ai_utils import QueryType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_with_ace():
    """Example: Using ACE Core with SQL generation"""
    
    print("=" * 80)
    print("ACE Core Integration Example - txt-to-sql Project")
    print("=" * 80)
    
    # Initialize ACE integration
    print("\n1. Initializing ACE integration...")
    ace_sql = initialize_ace_integration(ruleset_dir="ruleset")
    
    stats = ace_sql.get_statistics()
    print(f"   ✓ ACE Framework initialized")
    print(f"   ✓ Manual items: {stats['manual_stats']['total_items']}")
    print(f"   ✓ SQL items: {stats['sql_specific']['sql_items']}")
    print(f"   ✓ Business rules: {stats['sql_specific']['business_rules']}")
    print(f"   ✓ Constraints: {stats['sql_specific']['constraints']}")
    
    # Get context from ACE for SQL generation
    print("\n2. Getting SQL generation context from ACE...")
    query_type = "employee_count"
    context = ace_sql.get_sql_context(query_type=query_type, max_items=15)
    print(f"   ✓ Context retrieved ({len(context)} characters)")
    print(f"   First 300 chars:\n   {context[:300]}...\n")
    
    # Simulate query processing
    print("3. Processing query with ACE context...")
    natural_query = "Toplam çalışan sayısını göster"
    
    # In real usage, you would pass context to LLM
    # For this example, we'll simulate
    print(f"   Query: {natural_query}")
    print(f"   Query Type: {query_type}")
    print(f"   Using ACE context for better SQL generation\n")
    
    # Simulate successful query execution
    print("4. Simulating query execution...")
    generated_sql = "SELECT COUNT(*) FROM BI_CALISAN_BILGILERI WHERE WORK_E_DATE IS NULL"
    executed_sql = generated_sql
    success = True
    execution_feedback = {
        "execution_time_ms": 125,
        "rows_returned": 1,
        "result": {"total_employees": 150}
    }
    
    print(f"   Generated SQL: {generated_sql}")
    print(f"   Execution: {'SUCCESS' if success else 'FAILED'}")
    print(f"   Result: {execution_feedback.get('result', {})}")
    
    # Learn from query using ACE
    print("\n5. Learning from query using ACE...")
    ace_sql.learn_from_query(
        natural_query=natural_query,
        generated_sql=generated_sql,
        executed_sql=executed_sql,
        success=success,
        execution_feedback=execution_feedback,
        query_type=query_type
    )
    
    print("   ✓ Query processed through ACE cycle")
    print("   ✓ Insights extracted and added to manual")
    
    # Check updated statistics
    stats_after = ace_sql.get_statistics()
    print(f"\n6. Updated Statistics:")
    print(f"   Total items: {stats_after['manual_stats']['total_items']}")
    print(f"   Learned patterns: {stats_after['sql_specific']['learned_patterns']}")
    
    # Search for learned patterns
    print("\n7. Searching for learned patterns...")
    patterns = ace_sql.search_sql_patterns("employee")
    print(f"   Found {len(patterns)} patterns related to 'employee'")
    
    # Get learned patterns
    learned = ace_sql.get_learned_patterns(query_type=query_type)
    print(f"   Found {len(learned)} learned patterns for '{query_type}'")
    
    if learned:
        print("\n   Example learned pattern:")
        for pattern in learned[:1]:
            print(f"   - {pattern.content[:100]}...")
            if pattern.metadata:
                print(f"     Confidence: {pattern.metadata.confidence_score:.2f}")
                print(f"     Usage count: {pattern.metadata.usage_count}")
    
    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Integrate ACE into langchain_utils.py")
    print("2. Use get_sql_context() before LLM generation")
    print("3. Use learn_from_query() after query execution")
    print("4. Monitor statistics to track learning progress")


if __name__ == "__main__":
    example_with_ace()
