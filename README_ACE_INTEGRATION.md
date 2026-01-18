# ACE Core Integration - txt-to-sql Project

## Özet

Bu projeye ACE Core entegre edildi! Artık:
- ✅ Ruleset kuralları Context Collapse olmadan saklanır
- ✅ Her query'den öğrenir ve iyileştirir
- ✅ SQL generation pattern'leri birikir
- ✅ Uzun süreli kullanımda performans artar

## Hızlı Başlangıç

### 1. ACE Core'u Install Et

```bash
cd /Users/ahmet/AImet_txt_to_sql_ace
pip install git+https://github.com/ahmetererr/ace_lib.git
```

### 2. Test Et

```bash
python quick_test_ace.py
```

### 3. Örnek Çalıştır

```bash
python integration_example.py
```

## Dosyalar

- **ace_core_integration.py** - Ana integration modülü
- **integration_example.py** - Kullanım örneği
- **quick_test_ace.py** - Hızlı test script'i
- **INTEGRATION_GUIDE.md** - Detaylı entegrasyon kılavuzu
- **ace_integration_patch.py** - langchain_utils.py için patch örneği

## Kullanım

### Basit Kullanım

```python
from ace_core_integration import get_ace_instance

# Get ACE instance
ace_sql = get_ace_instance()

# Get context for SQL generation
context = ace_sql.get_sql_context(query_type="employee_count")

# After query execution, learn
ace_sql.learn_from_query(
    natural_query="Toplam çalışan sayısı",
    generated_sql="SELECT COUNT(*) FROM ...",
    success=True,
    query_type="employee_count"
)
```

### langchain_utils.py'ye Entegrasyon

Detaylı adımlar için `INTEGRATION_GUIDE.md` dosyasına bak.

## Nasıl Çalışır?

1. **İlk Başlatma**: Ruleset JSON dosyaları ACE Manual'a yüklenir
2. **Query Processing**: ACE Manual'dan context alınır
3. **SQL Generation**: Context LLM'e gönderilir
4. **Query Execution**: SQL çalıştırılır
5. **Learning**: ACE cycle ile öğrenilir (Reflect → Curate)
6. **State Save**: Öğrenilen pattern'ler kaydedilir

## Avantajlar

### Context Collapse Önleme

- **Önceki**: Her query'de ruleset tekrar yüklenir, uzun kullanımda kaybolur
- **ACE ile**: Ruleset ACE Manual'da saklanır, incremental updates ile kaybolmaz

### Sürekli Öğrenme

- **Başarılı query'ler**: Pattern'ler kaydedilir
- **Başarısız query'ler**: Hatalar öğrenilir, tekrarlanmaz
- **Query type detection**: Her query tipinden ayrı pattern'ler öğrenilir

### Performans İyileştirmesi

- En sık kullanılan kurallar önceliklendirilir
- Confidence score'lar ile pattern kalitesi takip edilir
- Usage count ile en etkili pattern'ler kullanılır

## İstatistikler

```python
stats = ace_sql.get_statistics()
print(f"SQL items: {stats['sql_specific']['sql_items']}")
print(f"Learned patterns: {stats['sql_specific']['learned_patterns']}")
```

## Sorun Giderme

### ACE Core bulunamıyor
```bash
pip install git+https://github.com/ahmetererr/ace_lib.git
```

### Ruleset yüklenmiyor
- `ruleset/` klasörünün doğru yerde olduğundan emin ol
- JSON dosyalarını kontrol et

Detaylı bilgi için `INTEGRATION_GUIDE.md` dosyasına bak.
