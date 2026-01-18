# ACE Core Integration Guide - txt-to-sql Project

## Overview

Bu rehber, ACE Core'u txt-to-sql projesine nasıl entegre edeceğini gösterir. ACE Core, SQL generation pattern'lerini öğrenir ve ruleset kurallarını Context Collapse olmadan saklar.

## Avantajlar

1. **Kurallar Kaybolmaz**: Uzun süreli kullanımda ruleset kuralları kaybolmaz
2. **Her Query'den Öğrenir**: Başarılı/başarısız SQL pattern'leri kaydedilir
3. **İyileşen Performans**: Zamanla daha iyi SQL query'leri üretir
4. **Context Collapse Önleme**: Incremental updates ile bilgi kaybı yok

## Kurulum

### 1. ACE Core'u Install Et

```bash
cd /Users/ahmet/AImet_txt_to_sql_ace
pip install git+https://github.com/ahmetererr/ace_lib.git
```

### 2. Integration Dosyasını Kontrol Et

`ace_core_integration.py` dosyası zaten hazır.

## Kullanım

### Temel Entegrasyon

```python
from ace_core_integration import get_ace_instance

# Initialize ACE (otomatik olarak ruleset'leri yükler)
ace_sql = get_ace_instance()

# SQL generation'dan önce context al
context = ace_sql.get_sql_context(query_type="employee_count", max_items=20)

# LLM'e context'i gönder (langchain_utils.py'de)
# ...

# Query execution'dan sonra öğren
ace_sql.learn_from_query(
    natural_query="Toplam çalışan sayısı",
    generated_sql="SELECT COUNT(*) FROM ...",
    executed_sql="SELECT COUNT(*) FROM ...",
    success=True,
    execution_feedback={"rows_returned": 150},
    query_type="employee_count"
)
```

## langchain_utils.py'ye Entegrasyon

### process_natural_query_langchain fonksiyonunu güncelle:

```python
from ace_core_integration import get_ace_instance

def process_natural_query_langchain(natural_query: str, ...):
    """Process natural language query with ACE integration"""
    
    # Get ACE instance
    ace_sql = get_ace_instance()
    
    # Detect query type (crew_ai_utils'den)
    query_type = detect_query_type(natural_query)  # "employee_count", etc.
    
    # Get ACE context for SQL generation
    ace_context = ace_sql.get_sql_context(query_type=query_type, max_items=20)
    
    # Get ruleset context (mevcut)
    ruleset_context = get_ruleset_context()
    
    # Combine contexts
    full_context = f"{ace_context}\n\n{ruleset_context}"
    
    # Generate SQL (mevcut kod)
    sql_query = generate_sql_with_langchain(natural_query, full_context)
    
    # Execute query (mevcut kod)
    try:
        result = execute_sql_query(sql_query)
        success = True
        execution_feedback = {"rows_returned": len(result), "success": True}
    except Exception as e:
        success = False
        execution_feedback = {"error": str(e)}
    
    # Learn from query using ACE
    ace_sql.learn_from_query(
        natural_query=natural_query,
        generated_sql=sql_query,
        executed_sql=sql_query,
        success=success,
        execution_feedback=execution_feedback,
        query_type=query_type
    )
    
    return result
```

## Örnek Kullanım

### Örnek 1: İlk Query

```python
from ace_core_integration import initialize_ace_integration

# Initialize
ace_sql = initialize_ace_integration()

# Query processing (langchain ile)
query = "Toplam çalışan sayısını göster"
sql = generate_sql(query, ace_sql.get_sql_context("employee_count"))

# Execute
result = execute_sql(sql)
ace_sql.learn_from_query(query, sql, sql, success=True, query_type="employee_count")
```

### Örnek 2: İstatistikleri Görüntüle

```python
stats = ace_sql.get_statistics()
print(f"Total items: {stats['manual_stats']['total_items']}")
print(f"SQL items: {stats['sql_specific']['sql_items']}")
print(f"Learned patterns: {stats['sql_specific']['learned_patterns']}")
```

### Örnek 3: Öğrenilen Pattern'leri Ara

```python
# Search for patterns
patterns = ace_sql.search_sql_patterns("employee")
for pattern in patterns:
    print(f"- {pattern.content}")
    print(f"  Confidence: {pattern.metadata.confidence_score}")
```

## Test Etmek İçin

```bash
cd /Users/ahmet/AImet_txt_to_sql_ace
python integration_example.py
```

## Entegrasyon Adımları

### 1. main.py'de ACE'yi Initialize Et

```python
from ace_core_integration import initialize_ace_integration

# FastAPI app başlatıldıktan sonra
ace_sql = initialize_ace_integration()
```

### 2. langchain_utils.py'yi Güncelle

- `process_natural_query_langchain` fonksiyonuna ACE context ekle
- Query execution sonrası `learn_from_query` çağır

### 3. crew_ai_utils.py'yi Güncelle (Opsiyonel)

- ACE context'i CrewAI agents'a da ekleyebilirsin
- Query type detection'ı ACE ile iyileştirebilirsin

## State Yönetimi

ACE state otomatik olarak `ace_sql_state.json` dosyasına kaydedilir:

- Her query'den sonra state kaydedilir
- Sunucu restart'tan sonra state yüklenir
- Ruleset'ler ilk başlatmada yüklenir

## İzleme ve Analiz

### Statistics

```python
stats = ace_sql.get_statistics()
```

### Search Learned Patterns

```python
patterns = ace_sql.get_learned_patterns(query_type="employee_count")
```

### Manual Review

```python
review = ace_sql.ace.review_manual(focus_areas=["sql", "business_rule"])
```

## Sorun Giderme

### ACE Core bulunamıyor

```bash
pip install git+https://github.com/ahmetererr/ace_lib.git
```

### Ruleset yüklenmiyor

- `ruleset/` klasörünün doğru yerde olduğundan emin ol
- JSON dosyalarının doğru format olduğunu kontrol et

### State kaydedilmiyor

- Dosya yazma izinlerini kontrol et
- `ace_sql_state.json` dosyasının oluşturulabildiğini kontrol et

## Sonuç

ACE Core entegrasyonu ile:
- ✅ Ruleset kuralları Context Collapse olmadan saklanır
- ✅ Her query'den öğrenilir ve iyileştirme yapılır
- ✅ SQL generation pattern'leri birikir
- ✅ Uzun süreli kullanımda performans artar
