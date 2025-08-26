from langchain_utils import execute_sql_query, generate_hr_optimized_chart

# Test SQL execution
sql_query = '''SELECT NVL("DEPARTMENTTYPE", 'Unknown') AS "Department",
       COUNT(*) AS "Employee_Count"
FROM "EMPLOYEE_DATA"
WHERE "EMPLOYEESTATUS" = 'Active'
GROUP BY NVL("DEPARTMENTTYPE", 'Unknown')
ORDER BY NVL("DEPARTMENTTYPE", 'Unknown")'''

print('Executing SQL...')
results = execute_sql_query(sql_query)

print(f'Results: {len(results)} rows')
for row in results:
    print(row)

print('\n' + '='*50)

# Test chart generation
chart_config = {
    'chart_type': 'bar',
    'title': 'Active Employees by Department',
    'x_column': 'Department',
    'y_column': 'Employee_Count',
    'color_column': 'Department'
}

print('Generating chart...')
chart_data = generate_hr_optimized_chart(results, chart_config)

if chart_data:
    print(f'Chart generated successfully! Type: {type(chart_data)}')
    if isinstance(chart_data, str) and chart_data.startswith('data:image'):
        print('Chart is base64 image')
    elif isinstance(chart_data, str):
        print('Chart is JSON/HTML string')
    else:
        print('Chart is other format')
else:
    print('Chart generation failed - returned None')
