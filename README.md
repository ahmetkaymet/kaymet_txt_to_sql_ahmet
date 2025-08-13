# AImet - AI-Powered Data Analytics

A modern, AI-powered application that converts natural language queries to SQL and provides intelligent data analysis with interactive visualizations.

## ✨ Features

### 🤖 **AI-Powered Natural Language Processing**
- **LangChain Integration**: Advanced LLM pipeline for natural language to SQL conversion
- **Smart Query Analysis**: AI determines data availability and suggests optimizations
- **Intelligent Explanations**: Detailed AI-generated explanations of SQL queries and results

### 📊 **Advanced Data Visualization**
- **Automatic Chart Detection**: AI recommends the most suitable chart type for your data
- **Interactive Charts**: Pie charts, bar charts, line charts, scatter plots, and tables
- **PNG Export**: High-quality chart images with HTML fallback support
- **Responsive Design**: Charts adapt to different screen sizes

### 🔍 **Smart Data Analysis**
- **Data Availability Check**: AI warns if requested data cannot be accessed
- **Result Summaries**: Natural language insights about query results
- **Query Optimization**: AI suggests improvements for better data retrieval

### 💾 **Comprehensive Query Management**
- **Session Management**: Organize queries by sessions
- **Query History**: Complete history with explanations, charts, and configurations
- **Duplicate Prevention**: Smart deduplication to avoid redundant queries
- **Persistent Storage**: SQLite database for reliable data persistence

## 🚀 Technology Stack

### **Backend**
- **Python 3.11+**: Core application logic
- **FastAPI**: Modern, fast web framework
- **LangChain**: LLM application framework
- **OpenAI GPT-4o**: Advanced language model
- **SQLite**: Lightweight database
- **Plotly**: Interactive chart generation
- **Pandas**: Data manipulation and analysis

### **Frontend**
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **Chakra UI**: Beautiful, accessible components
- **Plotly.js**: Interactive chart rendering
- **Vite**: Fast build tool

## 📋 Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- OpenAI API key
- Modern web browser

## 🛠️ Installation

### 1. **Clone the Repository**
```bash
git clone <repository-url>
cd kaymet_txt_to_sql_ahmet-3
```

### 2. **Backend Setup**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# OR create manually:
echo "OPENAI_API_KEY=your-api-key-here" > .env

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### 3. **Database Setup**
```bash
# IMPORTANT: You need to create and populate your own database!
# The application will NOT automatically create sample data.

# Option 1: Create database manually
python -c "
import sqlite3
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# Create your tables (example structure)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Stores (
        StoreID INTEGER PRIMARY KEY,
        StoreName TEXT NOT NULL,
        State TEXT NOT NULL,
        City TEXT NOT NULL,
        ZipCode TEXT,
        Address TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Products (
        ProductID INTEGER PRIMARY KEY,
        ProductName TEXT NOT NULL,
        Category TEXT,
        Price REAL NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Transactions (
        TransactionID INTEGER PRIMARY KEY,
        StoreID INTEGER,
        ProductID INTEGER,
        Quantity INTEGER,
        PricePerQuantity REAL,
        TransactionDate DATE,
        FOREIGN KEY (StoreID) REFERENCES Stores (StoreID),
        FOREIGN KEY (ProductID) REFERENCES Products (ProductID)
    )
''')

# Insert sample data (optional)
cursor.execute('''
    INSERT OR IGNORE INTO Stores (StoreID, StoreName, State, City, ZipCode, Address) VALUES
    (1, 'Downtown Store', 'NY', 'New York', '10001', '123 Main St'),
    (2, 'Uptown Store', 'NY', 'New York', '10002', '456 Oak Ave'),
    (3, 'Westside Store', 'CA', 'Los Angeles', '90210', '789 Sunset Blvd')
''')

cursor.execute('''
    INSERT OR IGNORE INTO Products (ProductID, ProductName, Category, Price) VALUES
    (1, 'Laptop', 'Electronics', 999.99),
    (2, 'Smartphone', 'Electronics', 699.99),
    (3, 'Coffee Mug', 'Home', 19.99)
''')

cursor.execute('''
    INSERT OR IGNORE INTO Transactions (TransactionID, StoreID, ProductID, Quantity, PricePerQuantity, TransactionDate) VALUES
    (1, 1, 1, 2, 999.99, '2024-01-15'),
    (2, 2, 2, 1, 699.99, '2024-01-16'),
    (3, 3, 3, 5, 19.99, '2024-01-17')
''')

conn.commit()
conn.close()
print('Database created successfully with sample data!')
"

# Option 2: Import from existing SQL file
# sqlite3 data.db < your_data.sql

# Option 3: Use your own database
# Just place your existing database file as 'data.db' in the project root
```

**Note**: The `query_history.db` file will be created automatically for storing query history, but you must provide your own `data.db` with your actual data!

### 4. **Frontend Setup**
```bash
cd frontend
npm install
```

## 🔑 **Required Configuration Files**

### **Environment Variables (.env)**
```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional: Custom configurations
OPENAI_MODEL=gpt-4o
LOG_LEVEL=INFO
```

### **Database Files**
- `data.db` - Main application database (auto-created)
- `query_history.db` - Query history database (auto-created)

### **API Key Setup**
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add it to your `.env` file
4. **Never commit your .env file to version control!**

## 🚀 Running the Application

### 1. **Start Backend**
```bash
python main.py
```
Backend will be available at `http://localhost:8000`

### 2. **Start Frontend**
```bash
cd frontend
npm run dev
```
Frontend will be available at `http://localhost:3000`

## 📁 **Project Structure**
```
kaymet_txt_to_sql_ahmet-3/
├── .env                    # Environment variables (create this)
├── .gitignore             # Git ignore rules
├── main.py                # FastAPI application entry point
├── langchain_utils.py     # LangChain integration and AI logic
├── query_history.py       # Database operations and history management
├── requirements.txt       # Python dependencies
├── data.db               # YOUR database with your data (create this!)
├── query_history.db      # Query history database (auto-created)
├── frontend/             # React frontend application
│   ├── src/
│   ├── package.json
│   └── index.html
└── README.md             # This file
```

**Important Files to Create:**
- `.env` - Your environment variables
- `data.db` - Your actual database with your data

## 💡 Usage Examples

### **Basic Query**
```
"Show me all stores in New York"
```
**AI Response**: "I found 5 stores in New York. Here's the breakdown..."

### **Sales Analysis**
```
"Show me sales by state"
```
**AI Response**: "I found sales data for 8 states. California has the highest sales at $15,000..."

### **Chart Generation**
```
"Create a pie chart of sales by product category"
```
**AI Response**: "I've generated a pie chart showing the distribution of sales across 6 product categories..."

## 🔧 API Endpoints

- `GET /`: API information
- `GET /sessions`: Get all query sessions
- `POST /generate-sql`: Generate SQL from natural language
- `POST /execute-sql`: Execute natural language query
- `POST /check-and-execute`: Check data availability and execute
- `POST /chart`: Generate charts for query results

## 📊 Chart Types

The AI automatically detects and generates the most appropriate chart type:

- **Pie Charts**: For categorical data distribution
- **Bar Charts**: For comparisons across categories
- **Line Charts**: For time series and trends
- **Scatter Plots**: For correlation analysis
- **Tables**: For detailed data display

## 🎯 Key Benefits

1. **No SQL Knowledge Required**: Ask questions in plain English
2. **AI-Powered Insights**: Get intelligent analysis of your data
3. **Interactive Visualizations**: Beautiful charts that tell your data story
4. **Smart Error Handling**: AI warns about data access issues
5. **Professional Results**: Production-ready SQL queries and explanations

## 🔒 Security Features

- **SQL Injection Prevention**: All queries are validated and sanitized
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Graceful error handling without exposing sensitive information
- **Environment Variables**: Secure API key management

## 📈 Performance

- **Fast Response**: Optimized LangChain pipeline
- **Efficient Caching**: Smart query result caching
- **Background Processing**: Non-blocking chart generation
- **Responsive UI**: Smooth user experience

## 🚨 **Troubleshooting**

### **Common Issues**

1. **"OpenAI API Key not found"**
   - Check your `.env` file exists
   - Verify `OPENAI_API_KEY` is set correctly
   - Restart the backend after changes

2. **"Database connection failed"**
   - Ensure you have write permissions in the project directory
   - Check if SQLite is available in your Python environment
   - **Verify `data.db` file exists with your data**

3. **"No data available for this query"**
   - **Check if your `data.db` has the required tables and data**
   - Verify table names and column names match your schema
   - Ensure your database has sample data to query

4. **"Frontend not loading"**
   - Verify Node.js version (18+)
   - Run `npm install` in the frontend directory
   - Check if port 3000 is available

5. **"Chart generation failed"**
   - Install kaleido: `pip install kaleido`
   - Check Plotly installation: `pip install plotly`

### **Performance Optimization**
- Use `gpt-4o-mini` for faster responses (edit `langchain_utils.py`)
- Enable caching for repeated queries
- Optimize database queries with proper indexing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information

---

**Built with ❤️ using LangChain, OpenAI, and modern web technologies** 
