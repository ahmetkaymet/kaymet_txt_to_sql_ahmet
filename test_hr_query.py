#!/usr/bin/env python3
"""
Test script for HR query functionality
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_utils import generate_unified_ai_response

async def test_hr_query():
    """Test the HR query functionality"""
    
    # Test query about employee turnover
    test_query = "What is the employee turnover rate by department?"
    
    print(f"Testing query: {test_query}")
    print("=" * 50)
    
    try:
        # Test the unified AI response
        explanation, sql_query, chart_config, data_availability = generate_unified_ai_response(test_query)
        
        print(f"✅ Success!")
        print(f"Explanation: {explanation}")
        print(f"SQL Query: {sql_query}")
        print(f"Chart Config: {chart_config}")
        print(f"Data Availability: {data_availability}")
        
        # Validate that we didn't get the fallback query
        if "SELECT 1 FROM DUAL" in sql_query.upper():
            print("❌ ERROR: Got fallback query SELECT 1 FROM DUAL")
            return False
        else:
            print("✅ SUCCESS: Got meaningful SQL query")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing HR Query System...")
    print("=" * 50)
    
    # Run the test
    success = asyncio.run(test_hr_query())
    
    if success:
        print("\n🎉 Test PASSED! The system is working correctly.")
    else:
        print("\n💥 Test FAILED! There are issues with the system.")
    
    print("=" * 50)
