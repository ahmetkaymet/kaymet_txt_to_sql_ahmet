# 🚀 **AImet - AI-Powered Data Analytics**

> **Developed by Ahmet ERER** | **2025 Internship Project** | **Contact: [ahmeterer00@gmail.com]**

A modern, AI-powered application that converts natural language queries to SQL and provides intelligent data analysis with interactive visualizations.

## 👨‍💻 **Developer Information**
- **Developer:** Ahmet ERER
- **Project Type:** 2025 Internship Project
- **Institution:** [Bilisim AS.]
- **Contact:** [ahmeterer00@gmail.com]
- **GitHub:** [ahmetererr]

---

## ✨ **Features**

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

---

## 🚀 **Technology Stack**

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

---

## 📋 **Prerequisites**

- Python 3.11 or higher
- Node.js 18 or higher
- OpenAI API key
- Modern web browser

---

## 🛠️ **Installation**

### 1. **Clone the Repository**
```bash
git clone <repository-url>
cd AImet_txt_to_sql
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
# IMPORTANT: You need to configure Oracle Database connection!
# The application uses Oracle Database with static IP connection.

# 1. Create .env file from .env.example
cp .env.example .env

# 2. Edit .env file with your Oracle database credentials
nano .env
```

**Required Environment Variables:**
```env
# Oracle Database Credentials
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password

# Static IP Configuration (REQUIRED )
ORACLE_STATIC_IP=192.168.1.100
ORACLE_PORT=1521

# Database Identifier (Service Name OR SID - use only one)
ORACLE_SERVICE_NAME=ORCL
# OR
# ORACLE_SID=ORCL
```

**Note**: The `query_history.db` file will be created automatically for storing query history. You must configure your Oracle database connection in the `.env` file!

### 4. **Frontend Setup**
```bash
cd frontend
npm install
```

---

## 🔑 **Required Configuration Files**

### **Environment Variables (.env)**
```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Required: Oracle Database Configuration
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password
ORACLE_STATIC_IP=192.168.1.100
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCL

# Optional: Custom configurations
OPENAI_MODEL=gpt-4o
LOG_LEVEL=INFO
```

### **Database Files**
- `query_history.db` - Query history database (auto-created)
- Oracle Database - Main application database (configured via .env)

### **API Key Setup**
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add it to your `.env` file
4. **Never commit your .env file to version control!**

---

## 🚀 **Running the Application**

### 1. **Test Database Connection**
```bash
# Test Oracle database connection
python test_oracle_connection.py
```

### 2. **Start Backend**
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

---

## 📁 **Project Structure**
```
AImet_txt_to_sql/
├── .env                    # Environment variables (create this)
├── .gitignore             # Git ignore rules
├── LICENSE                # Project license
├── main.py                # FastAPI application entry point
├── langchain_utils.py     # LangChain integration and AI logic
├── query_history.py       # Database operations and history management
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── query_history.db      # Query history database (auto-created)
├── frontend/             # React frontend application
│   ├── src/
│   ├── package.json
│   └── index.html
├── DATA CATALOGS/        # HR data catalogs
├── HR_DATASET_GUIDE.md   # HR data guide
├── STREAMING_README.md   # Streaming features guide
└── README.md             # This file
```

**Important Files to Create:**
- `.env` - Your environment variables (copy from .env.example)
- Oracle Database connection configuration

---

## 💡 **Usage Examples**

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

---

## 🔧 **API Endpoints**

- `GET /`: API information and endpoint list
- `GET /sessions`: Get all query sessions
- `GET /test-cors`: Test CORS configuration
- `POST /generate-sql`: Generate SQL from natural language
- `POST /generate-sql-stream`: Generate SQL with streaming response
- `POST /execute-sql`: Execute natural language query
- `POST /check-and-execute`: Check data availability and execute
- `POST /chart`: Generate charts for query results

---

## 📊 **Chart Types**

The AI automatically detects and generates the most appropriate chart type:

- **Pie Charts**: For categorical data distribution
- **Bar Charts**: For comparisons across categories
- **Line Charts**: For time series and trends
- **Scatter Plots**: For correlation analysis
- **Tables**: For detailed data display

---

## 🎯 **Key Benefits**

1. **No SQL Knowledge Required**: Ask questions in plain English
2. **AI-Powered Insights**: Get intelligent analysis of your data
3. **Interactive Visualizations**: Beautiful charts that tell your data story
4. **Smart Error Handling**: AI warns about data access issues
5. **Professional Results**: Production-ready SQL queries and explanations

---

## 🔒 **Security Features**

- **SQL Injection Prevention**: All queries are validated and sanitized
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Graceful error handling without exposing sensitive information
- **Environment Variables**: Secure API key management

---

## 📈 **Performance**

- **Fast Response**: Optimized LangChain pipeline
- **Efficient Caching**: Smart query result caching
- **Background Processing**: Non-blocking chart generation
- **Responsive UI**: Smooth user experience

---

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

---

## 🤝 **Contributing**

This project was developed by **Ahmet ERER** as an internship project. 

For any questions or contributions:
1. Contact the original developer: [ahmeterer00@gmail.com]
2. Check the documentation
3. Review existing issues
4. Create a new issue with detailed information

---

## 📄 **License**

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

**Important Notice:**
This software was developed by **Ahmet ERER** as an internship project.
Any commercial use, distribution, or modification without explicit written
permission from the original developer is strictly prohibited.

---

## 🆘 **Support**

For issues and questions:
1. Check the documentation
2. Review existing issues
3. Contact the developer: [ahmeterer00@gmail.com]
4. Create a new issue with detailed information

---

## 📞 **Contact Information**

- **Developer:** Ahmet ERER
- **Email:** [ahmeterer00@gmail.com]
- **Project:** AImet - AI-Powered Data Analytics
- **Type:** 2025 Internship Project


---

**Built with ❤️ by Ahmet ERER using LangChain, OpenAI, and modern web technologies**

**Project Completion Date:** Aug2025  

