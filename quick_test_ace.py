#!/usr/bin/env python3
"""
Quick test script for ACE Core integration with txt-to-sql
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ace_integration():
    """Test ACE Core integration"""
    
    print("=" * 80)
    print("ACE Core Integration Test - txt-to-sql Project")
    print("=" * 80)
    
    try:
        # Try importing ACE integration
        from ace_core_integration import initialize_ace_integration, get_ace_instance
        print("✓ ACE Core integration module loaded")
    except ImportError as e:
        print(f"✗ ACE Core integration failed: {e}")
        print("\nTo fix:")
        print("1. Install ACE Core: pip install git+https://github.com/ahmetererr/ace_lib.git")
        print("2. Or add capstone path to PYTHONPATH")
        return False
    
    try:
        # Initialize ACE
        print("\n1. Initializing ACE...")
        ace_sql = initialize_ace_integration(ruleset_dir="ruleset")
        print(f"   ✓ ACE Framework ID: {ace_sql.ace.framework_id[:12]}...")
        
        # Get statistics
        print("\n2. Getting statistics...")
        stats = ace_sql.get_statistics()
        print(f"   ✓ Total manual items: {stats['manual_stats']['total_items']}")
        print(f"   ✓ SQL items: {stats['sql_specific']['sql_items']}")
        print(f"   ✓ Business rules: {stats['sql_specific']['business_rules']}")
        print(f"   ✓ Constraints: {stats['sql_specific']['constraints']}")
        
        # Test context generation
        print("\n3. Testing context generation...")
        context = ace_sql.get_sql_context(query_type="employee_count", max_items=10)
        print(f"   ✓ Context generated: {len(context)} characters")
        print(f"   Preview:\n   {context[:200]}...")
        
        # Test learning
        print("\n4. Testing learning mechanism...")
        ace_sql.learn_from_query(
            natural_query="Toplam çalışan sayısı",
            generated_sql="SELECT COUNT(*) FROM BI_CALISAN_BILGILERI WHERE WORK_E_DATE IS NULL",
            executed_sql="SELECT COUNT(*) FROM BI_CALISAN_BILGILERI WHERE WORK_E_DATE IS NULL",
            success=True,
            execution_feedback={"rows_returned": 150},
            query_type="employee_count"
        )
        print("   ✓ Query learned successfully")
        
        # Check updated stats
        stats_after = ace_sql.get_statistics()
        print(f"\n5. Updated statistics:")
        print(f"   ✓ Total items: {stats_after['manual_stats']['total_items']}")
        print(f"   ✓ Learned patterns: {stats_after['sql_specific']['learned_patterns']}")
        
        # Test search
        print("\n6. Testing pattern search...")
        patterns = ace_sql.search_sql_patterns("employee")
        print(f"   ✓ Found {len(patterns)} patterns for 'employee'")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Integrate into langchain_utils.py (see INTEGRATION_GUIDE.md)")
        print("2. Use in main.py endpoints")
        print("3. Monitor learning progress")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ace_integration()
    sys.exit(0 if success else 1)
