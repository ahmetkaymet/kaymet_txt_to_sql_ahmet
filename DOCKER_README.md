# 🐳 AImet Docker Compose Kurulumu

Bu doküman, AImet projesini Docker Compose kullanarak nasıl çalıştıracağınızı açıklar.

## 📋 Gereksinimler

- Docker 20.10+
- Docker Compose 2.0+
- En az 4GB RAM
- En az 10GB disk alanı

## 🚀 Hızlı Başlangıç

### 1. Projeyi İndirin
```bash
git clone <repository-url>
cd AImet_txt_to_sql-2
```

### 2. Environment Variables Ayarlayın
```bash
# Template dosyasını kopyalayın
cp docker.env.template .env

# .env dosyasını düzenleyin
nano .env
```

**Önemli:** `.env` dosyasında aşağıdaki değerleri doldurun:
- `OPENAI_API_KEY`: OpenAI API anahtarınız
- `ORACLE_USER`: Oracle veritabanı kullanıcı adınız
- `ORACLE_PASSWORD`: Oracle veritabanı şifreniz
- `ORACLE_DSN`: Oracle veritabanı bağlantı bilgileri

### 3. Uygulamayı Başlatın
```bash
# Tüm servisleri başlat
docker-compose up -d

# Logları takip et
docker-compose logs -f
```

### 4. Uygulamayı Test Edin
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🏗️ Docker Compose Yapısı

### Servisler

#### 🔧 Backend (FastAPI)
- **Port**: 8000
- **Container**: `aimet-backend`
- **Image**: Custom build from `Dockerfile.backend`
- **Health Check**: http://localhost:8000/

#### 🎨 Frontend (React)
- **Port**: 3000
- **Container**: `aimet-frontend`
- **Image**: Custom build from `frontend/Dockerfile`
- **Health Check**: http://localhost:3000/

### Volumes (Veri Kalıcılığı)
- `./query_history.db` → `/app/query_history.db`
- `./data.db` → `/app/data.db`
- `./Wallet` → `/app/Wallet`
- `./ruleset` → `/app/ruleset`

### Network
- **Network**: `aimet-network` (bridge)
- Frontend ve backend aynı network üzerinde iletişim kurar

## 📝 Komutlar

### Temel Komutlar
```bash
# Servisleri başlat (detached mode)
docker-compose up -d

# Servisleri durdur
docker-compose down

# Servisleri yeniden başlat
docker-compose restart

# Logları görüntüle
docker-compose logs -f

# Belirli bir servisin loglarını görüntüle
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Geliştirme Komutları
```bash
# Servisleri yeniden build et
docker-compose build

# Belirli bir servisi yeniden build et
docker-compose build backend

# Servisleri force rebuild et
docker-compose build --no-cache

# Container'lara shell ile bağlan
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Debug Komutları
```bash
# Container durumlarını kontrol et
docker-compose ps

# Health check durumlarını kontrol et
docker-compose exec backend curl -f http://localhost:8000/
docker-compose exec frontend curl -f http://localhost:3000/

# Container kaynak kullanımını kontrol et
docker stats
```

## 🔧 Konfigürasyon

### Environment Variables

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `OPENAI_API_KEY` | OpenAI API anahtarı | **Zorunlu** |
| `ORACLE_USER` | Oracle kullanıcı adı | **Zorunlu** |
| `ORACLE_PASSWORD` | Oracle şifre | **Zorunlu** |
| `ORACLE_DSN` | Oracle bağlantı bilgisi | **Zorunlu** |
| `OPENAI_MODEL` | OpenAI model | `gpt-4o` |
| `LOG_LEVEL` | Log seviyesi | `INFO` |

### Port Konfigürasyonu

Eğer portları değiştirmek istiyorsanız, `docker-compose.yml` dosyasında port mapping'i düzenleyin:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Host port 8001, container port 8000
  
  frontend:
    ports:
      - "3001:3000"  # Host port 3001, container port 3000
```

## 🗄️ Veritabanı Konfigürasyonu

### Oracle Database

#### Harici Oracle Kullanımı
Varsayılan olarak, uygulama harici bir Oracle veritabanına bağlanır. `.env` dosyasında Oracle bilgilerini doğru şekilde ayarlayın:

```bash
ORACLE_USER=hr_user
ORACLE_PASSWORD=secure_password
ORACLE_DSN=192.168.1.100:1521/HRDB
```

#### Docker'da Oracle Çalıştırma (İsteğe Bağlı)
Eğer Oracle'ı da Docker'da çalıştırmak istiyorsanız, `docker-compose.yml` dosyasındaki Oracle servisini aktif edin:

```yaml
# Bu kısmı uncomment edin
oracle-db:
  image: container-registry.oracle.com/database/express:21.3.0-xe
  container_name: aimet-oracle
  ports:
    - "1521:1521"
  environment:
    - ORACLE_PWD=oracle123
  volumes:
    - oracle-data:/opt/oracle/oradata
```

### SQLite Database
- `query_history.db`: Sorgu geçmişi otomatik oluşturulur
- `data.db`: Ana veritabanı (manuel oluşturmanız gerekir)

## 🚨 Sorun Giderme

### Yaygın Sorunlar

#### 1. Port Çakışması
```bash
# Port kullanımını kontrol et
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# Çakışan servisleri durdur
sudo systemctl stop apache2  # Örnek
```

#### 2. Oracle Bağlantı Hatası
```bash
# Oracle bağlantısını test et
docker-compose exec backend python test_oracle_connection.py

# Oracle container'ı kontrol et (eğer Docker'da çalışıyorsa)
docker-compose logs oracle-db
```

#### 3. Memory Hatası
```bash
# Docker memory limitini artır
# Docker Desktop: Settings > Resources > Memory > 4GB+
```

#### 4. Build Hatası
```bash
# Cache'i temizle ve yeniden build et
docker-compose build --no-cache

# Docker system temizliği
docker system prune -a
```

#### 5. ARM64 (Apple Silicon) Sorunları
```bash
# Rollup ARM64 hatası için:
docker-compose build --no-cache frontend

# Platform belirterek build:
docker-compose build --build-arg BUILDPLATFORM=linux/arm64 frontend

# Multi-platform build:
docker buildx build --platform linux/arm64,linux/amd64 -t aimet-frontend ./frontend
```

### Log Analizi

```bash
# Tüm servislerin logları
docker-compose logs

# Belirli bir servisin logları
docker-compose logs backend | grep ERROR
docker-compose logs frontend | grep WARN

# Real-time log takibi
docker-compose logs -f --tail=100
```

### Container Debug

```bash
# Container içine shell ile bağlan
docker-compose exec backend bash
docker-compose exec frontend sh

# Container durumunu kontrol et
docker-compose ps
docker stats

# Container'ı yeniden başlat
docker-compose restart backend
```

## 🔒 Güvenlik

### Production Deployment

#### 1. Environment Variables
```bash
# Production için güvenli .env dosyası
cp docker.env.template .env.production

# Docker secrets kullanın (önerilen)
echo "your-api-key" | docker secret create openai_api_key -
```

#### 2. Network Security
```yaml
# docker-compose.prod.yml
services:
  backend:
    networks:
      - backend-network
    # Sadece frontend'den erişilebilir
  
  frontend:
    networks:
      - frontend-network
      - backend-network
    # Public erişim
```

#### 3. Resource Limits
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

## 📊 Monitoring

### Health Checks
```bash
# Health check durumlarını kontrol et
docker-compose ps

# Manuel health check
curl http://localhost:8000/
curl http://localhost:3000/health
```

### Performance Monitoring
```bash
# Resource kullanımı
docker stats

# Container detayları
docker-compose exec backend top
docker-compose exec frontend ps aux
```

## 🧹 Temizlik

```bash
# Servisleri durdur ve container'ları sil
docker-compose down

# Volume'ları da sil
docker-compose down -v

# Image'ları sil
docker-compose down --rmi all

# Tüm Docker temizliği
docker system prune -a --volumes
```

## 📚 Ek Kaynaklar

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Docker Guide](https://fastapi.tiangolo.com/deployment/docker/)
- [React Docker Guide](https://create-react-app.dev/docs/deployment/)
- [Oracle Docker Images](https://github.com/oracle/docker-images)

## 🆘 Destek

Sorun yaşarsanız:

1. **Logları kontrol edin**: `docker-compose logs`
2. **Health check yapın**: `docker-compose ps`
3. **GitHub Issues** oluşturun
4. **Developer'a ulaşın**: [ahmeterer00@gmail.com]

---

**Not**: Bu Docker Compose kurulumu geliştirme ve test amaçlıdır. Production kullanımı için ek güvenlik ve performans optimizasyonları gerekebilir.
