import pandas as pd
import plotly.express as px
import base64

# Test data
test_data = [
    {"Department": "IT", "Employee_Count": 25},
    {"Department": "HR", "Employee_Count": 15},
    {"Department": "Finance", "Employee_Count": 20}
]

print("Test data:", test_data)

# Convert to DataFrame
df = pd.DataFrame(test_data)
print("DataFrame shape:", df.shape)
print("DataFrame columns:", list(df.columns))

# Try to create a simple bar chart
try:
    print("Creating bar chart...")
    fig = px.bar(
        df,
        x="Department",
        y="Employee_Count",
        title="Test Chart"
    )
    print("Chart created successfully")
    
    # Try to convert to PNG
    try:
        print("Converting to PNG...")
        img_bytes = fig.to_image(format="png", engine="kaleido")
        img_base64 = base64.b64encode(img_bytes).decode()
        result = f"data:image/png;base64,{img_base64}"
        print(f"PNG conversion successful! Result length: {len(result)}")
        print("Result starts with:", result[:50])
    except Exception as e:
        print(f"PNG conversion failed: {e}")
        
        # Try HTML fallback
        try:
            print("Trying HTML fallback...")
            html_string = fig.to_html(include_plotlyjs=False, full_html=False)
            result = {
                "chart_type": "bar",
                "title": "Test Chart",
                "html": html_string,
                "fallback": True
            }
            print("HTML fallback successful!")
            print("Result type:", type(result))
        except Exception as e2:
            print(f"HTML fallback also failed: {e2}")
            result = None
    
except Exception as e:
    print(f"Chart creation failed: {e}")
    result = None

print("\nFinal result:", result is not None)
