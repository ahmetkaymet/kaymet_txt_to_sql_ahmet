# CrewAI Multi-Agent System for HR Analytics

Bu proje, CrewAI tabanlı çoklu ajan sistemi kullanarak HR analitik sorgularını işleyen gelişmiş bir Thought of Chain mimarisi içerir.

## 🏗️ Mimari

### Ana Bileşenler

1. **Main Router**: Gelen istekleri sınıflandırır ve hangi crew'lerin çalışacağına karar verir
2. **Table Analysis Crew**: Hangi tabloda hangi sütunlara bakılacağını belirler
3. **Business Rules Crew**: Ruleset'teki business rule'ları uygular
4. **Intent Detection Crew**: Kullanıcı niyetini tespit eder
5. **Response Generator Crew**: Final response'u üretir

### Thought of Chain Akışı

```
Kullanıcı Sorgusu
       ↓
   Main Router (Sınıflandırma)
       ↓
   ┌─────────────────────────────────────┐
   │        Paralel Çalışan Crew'ler     │
   ├─────────────────────────────────────┤
   │  Table Analysis  │  Business Rules  │  Intent Detection  │
   │      Crew        │      Crew        │      Crew          │
   └─────────────────────────────────────┘
       ↓
   Response Generator Crew
       ↓
   Final SQL + Açıklama + Chart Config
```

## 🚀 Kurulum

### Gereksinimler

```bash
pip install -r requirements.txt
```

Yeni eklenen bağımlılıklar:
- `crewai>=0.28.0`
- `crewai-tools>=0.1.0`
- `langchain-core>=0.1.0`

### Ortam Değişkenleri

`.env` dosyasında:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## 📊 Kullanım

### API Endpoint'leri

#### 1. CrewAI ile Sorgu Çalıştırma
```http
POST /crew-ai-execute
Content-Type: application/json

{
    "query": "Kaç çalışan var?",
    "session_id": "optional-session-id",
    "username": "demo_admin"
}
```

#### 2. Mevcut LangChain Endpoint'leri
- `/execute-sql` - LangChain ile sorgu çalıştırma
- `/check-and-execute` - Veri kontrolü ve sorgu çalıştırma
- `/generate-sql` - Sadece SQL üretme

### Programatik Kullanım

```python
from crew_ai_utils import process_query_with_crew_ai

# Sorgu işleme
explanation, sql_query, chart_config, data_availability = process_query_with_crew_ai(
    "Departmanlara göre çalışan sayısı"
)

print(f"Açıklama: {explanation}")
print(f"SQL: {sql_query}")
print(f"Chart: {chart_config}")
```

## 🧪 Test

CrewAI sistemini test etmek için:

```bash
python test_crew_ai.py
```

Bu script şunları test eder:
- Ruleset Manager
- Main Router sınıflandırması
- Tam CrewAI pipeline'ı

## 📋 Sorgu Türleri

Sistem şu sorgu türlerini destekler:

- `employee_count`: Çalışan sayısı sorguları
- `department_analysis`: Departman analizi
- `leave_analysis`: İzin kullanım analizi
- `turnover_analysis`: Devir hızı analizi
- `person_lookup`: Kişi arama
- `education_analysis`: Eğitim seviyesi analizi
- `gender_analysis`: Cinsiyet dağılımı
- `service_analysis`: Hizmet süresi analizi
- `general_analysis`: Genel HR analizi

## 🔧 Crew Detayları

### Table Analysis Crew
- **Rol**: HR Database Schema Expert
- **Görev**: En uygun tablo ve sütunları belirleme
- **Çıktı**: JSON formatında tablo ve sütun analizi

### Business Rules Crew
- **Rol**: HR Business Rules Expert
- **Görev**: Business rule'ları uygulama ve compliance sağlama
- **Çıktı**: JSON formatında business rules analizi

### Intent Detection Crew
- **Rol**: HR Query Intent Specialist
- **Görev**: Kullanıcı niyetini tespit etme ve belirsizlikleri giderme
- **Çıktı**: JSON formatında intent analizi

### Response Generator Crew
- **Rol**: HR SQL Query Generator
- **Görev**: Final SQL sorgusu ve response üretme
- **Çıktı**: JSON formatında tam response

## 📁 Dosya Yapısı

```
├── crew_ai_utils.py          # Ana CrewAI implementasyonu
├── langchain_utils.py        # Güncellenmiş LangChain utils (fallback)
├── main.py                   # Güncellenmiş FastAPI app
├── test_crew_ai.py          # Test scripti
├── requirements.txt          # Güncellenmiş bağımlılıklar
└── CREW_AI_README.md        # Bu dosya
```

## 🔄 Fallback Mekanizması

Sistem, CrewAI başarısız olursa otomatik olarak orijinal LangChain pipeline'ına geri döner:

```python
try:
    # CrewAI ile işleme
    result = process_query_with_crew_ai(query)
except Exception:
    # LangChain fallback
    result = _generate_unified_ai_response_fallback(query)
```

## 🎯 Avantajlar

1. **Paralel İşleme**: Birden fazla crew aynı anda çalışır
2. **Uzmanlaşmış Ajanlar**: Her crew kendi alanında uzman
3. **Business Rules Compliance**: Ruleset'teki kurallar otomatik uygulanır
4. **Intent Detection**: Kullanıcı niyeti otomatik tespit edilir
5. **Hata Toleransı**: Fallback mekanizması ile güvenilirlik
6. **JSON Format**: Yapılandırılmış çıktılar

## 🚨 Önemli Notlar

1. **Ruleset Bağımlılığı**: Sistem ruleset JSON dosyalarına bağımlıdır
2. **OpenAI API**: CrewAI OpenAI API kullanır
3. **Performans**: Paralel işleme sayesinde hızlı
4. **Güvenlik**: Business rules otomatik uygulanır
5. **Test**: Her değişiklikten sonra test edilmelidir

## 🔮 Gelecek Geliştirmeler

- [ ] Daha fazla crew türü ekleme
- [ ] Crew'ler arası iletişim geliştirme
- [ ] Performans optimizasyonu
- [ ] Daha detaylı logging
- [ ] Metrics ve monitoring
