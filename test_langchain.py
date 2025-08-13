#!/usr/bin/env python3
"""
Test script for LangChain functionality
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_langchain_imports():
    """Test if LangChain modules can be imported"""
    try:
        from langchain_utils import (
            create_langchain_pipeline,
            generate_sql_with_langchain,
            analyze_results_with_ai,
            detect_chart_type,
            check_data_availability_with_ai
        )
        print("✅ LangChain imports successful")
        return True
    except ImportError as e:
        print(f"❌ LangChain import failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    try:
        from langchain_utils import get_db_connection, get_db_schema
        conn = get_db_connection()
        schema = get_db_schema()
        print("✅ Database connection successful")
        print(f"Schema length: {len(schema)} characters")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_sql_generation():
    """Test SQL generation with LangChain"""
    try:
        from langchain_utils import generate_sql_with_langchain
        
        # Test query
        test_query = "Show me all stores in New York"
        print(f"Testing SQL generation for: {test_query}")
        
        explanation, sql_query, _ = generate_sql_with_langchain(test_query)
        print(f"✅ SQL generation successful")
        print(f"Generated SQL: {sql_query}")
        print(f"Explanation length: {len(explanation)} characters")
        return True
    except Exception as e:
        print(f"❌ SQL generation failed: {e}")
        return False

def test_data_availability_check():
    """Test data availability checking"""
    try:
        from langchain_utils import check_data_availability_with_ai
        
        # Test query
        test_query = "Show me all stores in New York"
        print(f"Testing data availability for: {test_query}")
        
        is_available, message = check_data_availability_with_ai(test_query)
        print(f"✅ Data availability check successful")
        print(f"Data available: {is_available}")
        print(f"Message: {message}")
        return True
    except Exception as e:
        print(f"❌ Data availability check failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing LangChain Integration")
    print("=" * 50)
    
    tests = [
        ("LangChain Imports", test_langchain_imports),
        ("Database Connection", test_database_connection),
        ("SQL Generation", test_sql_generation),
        ("Data Availability Check", test_data_availability_check),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! LangChain integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
