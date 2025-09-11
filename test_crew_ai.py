"""
Test script for CrewAI implementation
This script tests the CrewAI multi-agent system for HR analytics
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_crew_ai_system():
    """Test the CrewAI system with sample queries"""
    
    try:
        from crew_ai_utils import process_query_with_crew_ai
        
        # Test queries
        test_queries = [
            "Kaç çalışan var?",
            "Departmanlara göre çalışan sayısı",
            "Yıllık izin kullanımı",
            "2024 turnover analizi",
            "Celil'in izinleri"
        ]
        
        print("🚀 Testing CrewAI Multi-Agent System")
        print("=" * 50)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test {i}: {query}")
            print("-" * 30)
            
            try:
                explanation, sql_query, chart_config, data_availability = process_query_with_crew_ai(query)
                
                print(f"✅ Explanation: {explanation[:200]}...")
                print(f"🔍 SQL Query: {sql_query}")
                print(f"📊 Chart Config: {chart_config}")
                print(f"📈 Data Available: {data_availability}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n🎉 CrewAI testing completed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure CrewAI is installed: pip install crewai")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_ruleset_manager():
    """Test the ruleset manager"""
    
    try:
        from crew_ai_utils import RulesetManager, QueryType
        
        print("\n🔧 Testing Ruleset Manager")
        print("=" * 30)
        
        ruleset_manager = RulesetManager()
        
        # Test business rules extraction
        for query_type in QueryType:
            rules = ruleset_manager.get_business_rules_for_query(query_type)
            print(f"📋 {query_type.value}: {len(rules)} rules found")
        
        # Test table schema
        calisan_schema = ruleset_manager.get_table_schema("BI_CALISAN_BILGILERI")
        if calisan_schema:
            print(f"📊 BI_CALISAN_BILGILERI schema loaded: {len(calisan_schema.get('columns', []))} columns")
        
        izin_schema = ruleset_manager.get_table_schema("BI_AYLIK_IZIN_KULLANIM")
        if izin_schema:
            print(f"📊 BI_AYLIK_IZIN_KULLANIM schema loaded: {len(izin_schema.get('columns', []))} columns")
        
        print("✅ Ruleset Manager test completed!")
        
    except Exception as e:
        print(f"❌ Ruleset Manager error: {e}")

def test_main_router():
    """Test the main router classification"""
    
    try:
        from crew_ai_utils import MainRouter
        
        print("\n🎯 Testing Main Router")
        print("=" * 25)
        
        router = MainRouter()
        
        test_queries = [
            "Kaç çalışan var?",
            "Departmanlara göre dağılım",
            "Yıllık izin kullanımı",
            "Turnover analizi",
            "Celil'in bilgileri"
        ]
        
        for query in test_queries:
            query_type = router.classify_query(query)
            print(f"📝 '{query}' -> {query_type.value}")
        
        print("✅ Main Router test completed!")
        
    except Exception as e:
        print(f"❌ Main Router error: {e}")

if __name__ == "__main__":
    print("🧪 CrewAI System Test Suite")
    print("=" * 40)
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in .env file")
        sys.exit(1)
    
    # Run tests
    test_ruleset_manager()
    test_main_router()
    test_crew_ai_system()
    
    print("\n🏁 All tests completed!")
