import logging
logging.basicConfig(level=logging.INFO)

from langchain_utils import generate_unified_ai_response, execute_sql_query, generate_hr_optimized_chart

# Test query
query = "Show me employee count by department"
print(f"Testing query: {query}")
print("=" * 60)

try:
    # Step 1: Generate AI response
    print("Step 1: Generating AI response...")
    explanation, sql_query, chart_config, data_availability = generate_unified_ai_response(query)
    
    print(f"Chart config: {chart_config}")
    print(f"Chart type: {chart_config.get('chart_type')}")
    print(f"X column: {chart_config.get('x_column')}")
    print(f"Y column: {chart_config.get('y_column')}")
    
    print("\n" + "=" * 60)
    
    # Step 2: Execute SQL
    print("Step 2: Executing SQL...")
    results = execute_sql_query(sql_query)
    print(f"SQL results: {len(results)} rows")
    for row in results:
        print(row)
    
    print("\n" + "=" * 60)
    
    # Step 3: Generate chart
    print("Step 3: Generating chart...")
    if chart_config and chart_config.get("chart_type") and chart_config["chart_type"] != "none" and chart_config["chart_type"] != "table":
        print("Chart generation should happen...")
        chart_data = generate_hr_optimized_chart(results, chart_config)
        print(f"Chart data result: {type(chart_data)}")
        if chart_data:
            print("Chart generated successfully!")
            if isinstance(chart_data, str):
                if chart_data.startswith('data:image'):
                    print("Chart is base64 image")
                else:
                    print("Chart is string data")
            else:
                print("Chart is other format")
        else:
            print("Chart generation returned None")
    else:
        print("Chart generation not needed")
        print(f"Chart config: {chart_config}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
