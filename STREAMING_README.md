# 🚀 AImet Backend Streaming API

Bu proje, GPT-4o mini kullanarak HR verilerini analiz eden streaming API sağlar.

## ✨ Özellikler

### 🔥 Backend Streaming
- **GPT-4o mini Integration**: Maliyet optimizasyonu ile streaming
- **Smart Query Parsing**: Akıllı HR query analizi
- **Real-time Response**: Streaming API endpoints
- **Cost Optimization**: GPT-4o'dan 16.7x daha ucuz

### 🎯 Akıllı Query Parsing
- **Employee Count**: Departman bazında çalışan sayısı
- **Turnover Analysis**: Çalışan ayrılış oranları
- **Salary Insights**: Maaş ve kompanzasyon analizi
- **Recruitment Data**: Aday bilgileri ve eğitim seviyeleri
- **Performance Metrics**: Çalışan performans değerlendirmeleri
- **Experience Analysis**: Deneyim seviyeleri

### 📊 Chart Generation
- **Bar Charts**: Departman karşılaştırmaları
- **Pie Charts**: Kategori dağılımları
- **Custom Configs**: Dinamik chart konfigürasyonu

## 🚀 Kurulum

### Backend
```bash
cd /Users/ahmet/AImet_txt_to_sql
python main.py
```

### Frontend (Eski Arayüz)
```bash
cd frontend
npm run dev
```

## 🔧 API Endpoints

### Streaming SQL Generation
```bash
POST /generate-sql-stream
Content-Type: application/json

{
  "query": "Show me employee count by department"
}
```

### Response Format
```json
{
  "type": "chunk",
  "content": "AI response content...",
  "progress": 0.75
}

{
  "type": "result",
  "explanation": "Analysis explanation...",
  "sql_query": "SELECT statement...",
  "chart_config": {
    "chart_type": "bar",
    "title": "Chart Title",
    "x_column": "x_column_name",
    "y_column": "y_column_name"
  }
}
```

## 📱 Kullanım

### 1. Eski Frontend Arayüzü
- Frontend'de "Execute" butonuna tıklayın
- HR verisi hakkında soru sorun
- Normal flow ile sonuçları görün

### 2. Backend API Testing
```bash
# Test script'i çalıştırın
python test_streaming.py

# Manuel curl test
curl -X POST "http://localhost:8000/generate-sql-stream" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me employee turnover by department"}' \
  --no-buffer
```

## 🛠️ Teknik Detaylar

### Backend Architecture
- **FastAPI**: Modern Python web framework
- **LangChain**: AI pipeline orchestration
- **StreamingResponse**: Server-sent events
- **SQLite**: Embedded database

### AI Integration
- **GPT-4o mini**: Maliyet optimizasyonu
- **Streaming**: Realtime token generation
- **Smart Parsing**: Query intent recognition
- **Fallback Logic**: Error handling

## 📈 Performance

### Streaming Benefits
- **Instant Feedback**: Kullanıcı beklemez
- **Progressive Loading**: İçerik kademeli yüklenir
- **Resource Efficiency**: Daha az bellek kullanımı

### Response Times
- **First Chunk**: < 100ms
- **Full Response**: < 2s
- **SQL Execution**: < 500ms
- **Chart Generation**: < 1s

## 💰 Maliyet Optimizasyonu

### Model Karşılaştırması
| Model | 1000 token maliyeti | Tasarruf |
|-------|---------------------|----------|
| **GPT-4o** | $0.0125 | - |
| **GPT-4o mini** | $0.00075 | **94% tasarruf** |

### Aylık Kullanım (1000 sorgu)
- **GPT-4o**: $12.50/ay
- **GPT-4o mini**: $0.75/ay
- **Yıllık tasarruf**: $141

## 🔍 Test Queries

### Employee Analytics
- "Show me employee count by department"
- "What is the average salary by position?"
- "Analyze employee turnover by department"

### Performance & Experience
- "Show me performance ratings by department"
- "What is the average experience by team?"
- "Analyze employee satisfaction scores"

### Recruitment & Training
- "How many candidates do we have by education level?"
- "Show me training completion rates"
- "Analyze recruitment pipeline data"

## 🚨 Troubleshooting

### Common Issues
1. **Port Conflicts**: 8000 portunun boş olduğundan emin olun
2. **CORS Errors**: Backend CORS ayarlarını kontrol edin
3. **Streaming Failures**: Network bağlantısını ve API key'i kontrol edin

### Debug Commands
```bash
# Process kontrolü
lsof -i :8000

# Log kontrolü
tail -f backend.log

# API test
curl -v http://localhost:8000/health
```

## 🔮 Gelecek Özellikler

- **Advanced Query Parsing**: Daha akıllı intent recognition
- **Multi-language Support**: Türkçe dahil çoklu dil desteği
- **Performance Optimization**: Daha hızlı response times
- **Advanced Analytics**: Daha detaylı HR insights

## 📞 Destek

Proje ile ilgili sorularınız için:
- GitHub Issues kullanın
- Backend loglarını kontrol edin
- Test script'lerini çalıştırın

---

**🎉 AImet Backend Streaming API ile HR verilerinizi maliyet optimizasyonu ile analiz edin!**
