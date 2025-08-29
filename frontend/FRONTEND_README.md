# Frontend Güncellemeleri

## Yeni Özellikler

### 1. 🗓️ Günlük Chat History Başlıkları
- **Today** - Bugün yapılan sorgular
- **Yesterday** - Dün yapılan sorgular  
- **This Week** - Bu hafta yapılan sorgular
- **This Month** - Bu ay yapılan sorgular
- **Older** - Daha eski sorgular

### 2. 🗑️ Query Silme Seçeneği
- Her sorgu kartının sağ üst köşesinde silme butonu
- Hover yapıldığında görünür olur
- Tıklanarak sorgu geçmişten kaldırılır

### 3. 🎨 Modern UI Tasarımı
- **Inter** font ailesi eklendi (Google Fonts)
- Daha modern ve temiz görünüm
- Geliştirilmiş renk paleti
- Hover efektleri ve animasyonlar

### 4. 📱 Responsive Tasarım
- Desktop ve mobile için optimize edilmiş
- Collapsible sidebar
- Mobile drawer menü

## Kurulum ve Çalıştırma

### Gereksinimler
- Node.js 16+ 
- npm veya yarn

### Adımlar
1. **Bağımlılıkları yükle:**
   ```bash
   cd frontend
   npm install
   ```

2. **Development server'ı başlat:**
   ```bash
   npm run dev
   ```

3. **Tarayıcıda aç:**
   ```
   http://localhost:5173
   ```

## Teknik Detaylar

### Font Güncellemeleri
- `index.html`'de Inter font import edildi
- Chakra UI tema konfigürasyonu güncellendi
- Global font ailesi Inter olarak ayarlandı

### Chat History Güncellemeleri
- `groupHistoryByDate()` fonksiyonu eklendi
- Tarih bazlı gruplandırma
- Silme fonksiyonalitesi (`deleteQuery`)
- Mobile ve desktop sidebar senkronizasyonu

### Tema Konfigürasyonu
- Custom brand renkleri
- Button ve Input component stilleri
- Global CSS ayarları
- Hover ve focus efektleri

## Dosya Yapısı

```
frontend/
├── src/
│   ├── App.tsx          # Ana uygulama komponenti
│   └── main.tsx         # Tema konfigürasyonu
├── index.html           # Font importları
├── package.json         # Bağımlılıklar
└── FRONTEND_README.md   # Bu dosya
```

## Özellik Kullanımı

### Chat History'de Sorgu Silme
1. Sidebar'da bir sorgu kartına hover yapın
2. Sağ üst köşede çıkan silme butonuna tıklayın
3. Sorgu geçmişten kaldırılır

### Günlük Grupları
- Sorgular otomatik olarak tarihe göre gruplandırılır
- Her grup başlığı farklı renkte gösterilir
- Zaman bilgisi saat:dakika formatında gösterilir

## Notlar

- Backend'de silme endpoint'i henüz yok, sadece frontend'den kaldırılıyor
- Tarih gruplandırması client-side yapılıyor
- Responsive tasarım tüm ekran boyutlarında test edildi
- Modern font ve renk paleti kullanıcı deneyimini iyileştiriyor
