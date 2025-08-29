# 🎯 **HR Dataset Analytics Guide**

> **Developed by Ahmet ERER** | **2025 Internship Project** | **Contact: ahmet.erer00@gmail.com**

Bu proje artık HR (İnsan Kaynakları) verilerinizi analiz etmek için optimize edilmiştir!

## 👨‍💻 **Developer Information**
- **Developer:** Ahmet ERER
- **Project Type:** 2025 Internship Project
- **Institution:** Bilisim AS.
- **Contact:** ahmet.erer00@gmail.com
- **GitHub:** ahmetererr

---

## 📊 **Desteklenen HR Veri Türleri:**

### 1. **Employee Data (Çalışan Verileri)**
- Kişisel bilgiler, departman, pozisyon
- Maaş, işe başlama tarihi, deneyim
- Performans skorları, kariyer gelişimi

### 2. **Employee Engagement Survey Data**
- Memnuniyet skorları, geri bildirimler
- Departman bazında engagement analizi
- Zaman içinde trend analizi

### 3. **Recruitment Data (İşe Alım Verileri)**
- Başvurular, mülakatlar, işe alım süreci
- Kaynak analizi, conversion rates
- Zaman bazında hiring trends

### 4. **Training and Development Data**
- Kurs tamamlama oranları
- Sertifikalar, beceri gelişimi
- Eğitim etkinliği analizi

## 🚀 **Hızlı Başlangıç Sorguları:**

### **Çalışan Sayıları:**
```
"Show me employee count by department"
"Kaç çalışan var?"
"How many employees are in each position?"
```

### **Maaş Analizi:**
```
"What is the average salary by position?"
"Show me salary distribution by department"
"Find salary ranges for different experience levels"
```

### **Engagement Analizi:**
```
"Analyze employee engagement scores by department"
"Show me satisfaction trends over time"
"What are the engagement scores by team?"
```

### **Eğitim Metrikleri:**
```
"Show me training completion rates"
"Analyze skill development progress"
"What courses have the highest completion rates?"
```

### **İşe Alım Analizi:**
```
"Show me recruitment funnel metrics"
"Analyze hiring trends by month"
"What are the application sources?"
```

## 📈 **Özel Chart Türleri:**

### **HR-Specific Visualizations:**
- **Heatmap**: Engagement skorları departman bazında
- **Boxplot**: Maaş dağılımı departman bazında
- **Histogram**: Deneyim süresi dağılımı
- **Enhanced Dashboard**: Kapsamlı HR analizi

### **Chart Seçim Mantığı:**
- **Çalışan sayıları** → Pie chart (dağılım) veya Bar chart (karşılaştırma)
- **Maaş analizi** → Boxplot (dağılım) veya Histogram (frekans)
- **Engagement skorları** → Heatmap (çoklu faktör) veya Bar chart (karşılaştırma)
- **Trend analizi** → Line chart (zaman serisi)

## 🔧 **Teknik Özellikler:**

### **AI Optimizasyonları:**
- **Unified Pipeline**: Tüm AI işlemleri tek seferde
- **HR-Specific Prompts**: HR verilerine özel AI analizi
- **Smart Chart Detection**: Otomatik chart türü seçimi
- **Enhanced Insights**: HR odaklı öneriler ve action items

### **Performans İyileştirmeleri:**
- **Connection Pooling**: Hızlı veritabanı erişimi
- **Schema Caching**: Şema bilgileri cache'leniyor
- **Optimized Logging**: Sadece önemli bilgiler loglanıyor

## 📋 **Örnek Kullanım Senaryoları:**

### **Senaryo 1: Departman Bazında Çalışan Analizi**
```
Query: "Show me employee count by department with average salary"
Result: 
- SQL: SELECT department, COUNT(*) as employee_count, AVG(salary) as avg_salary FROM employees GROUP BY department
- Chart: Bar chart showing employee count and average salary by department
- Insights: Department size vs. compensation analysis
```