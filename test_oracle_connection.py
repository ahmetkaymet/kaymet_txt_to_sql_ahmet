#!/usr/bin/env python3
"""
Oracle Database Bağlantı Testi - Statik IP ile
"""

import os
from config.oracle_config import OracleConnection, get_db_connection

def test_static_ip_connection():
    """Mevcut konfigürasyon ile statik IP bağlantısını test et"""
    
    # Environment variables'ları kontrol et
    static_ip = os.getenv("ORACLE_STATIC_IP")
    port = os.getenv("ORACLE_PORT", "1521")
    service_name = os.getenv("ORACLE_SERVICE_NAME")
    sid = os.getenv("ORACLE_SID")
    
    print("🔍 Environment Variables Kontrolü:")
    print(f"   ORACLE_STATIC_IP: {static_ip or '❌ Tanımlanmamış'}")
    print(f"   ORACLE_PORT: {port}")
    print(f"   ORACLE_SERVICE_NAME: {service_name or '❌ Tanımlanmamış'}")
    print(f"   ORACLE_SID: {sid or '❌ Tanımlanmamış'}")
    print(f"   ORACLE_USER: {os.getenv('ORACLE_USER') or '❌ Tanımlanmamış'}")
    print(f"   ORACLE_PASSWORD: {'✅ Tanımlanmış' if os.getenv('ORACLE_PASSWORD') else '❌ Tanımlanmamış'}")
    print()
    
    if not static_ip:
        print("❌ ORACLE_STATIC_IP environment variable'ı tanımlanmamış!")
        print("📝 .env dosyasına ORACLE_STATIC_IP değerini ekleyin")
        return False
    
    if not service_name and not sid:
        print("❌ ORACLE_SERVICE_NAME veya ORACLE_SID environment variable'ı tanımlanmamış!")
        print("📝 .env dosyasına ikisinden birini ekleyin")
        return False
    
    print(f"🔗 Statik IP ile bağlanmaya çalışılıyor: {static_ip}:{port}")
    
    if service_name:
        print(f"📡 Service Name: {service_name}")
    else:
        print(f"📡 SID: {sid}")
    
    try:
        # Mevcut konfigürasyon ile bağlantı
        oracle_conn = OracleConnection()
        connection = oracle_conn.connect()
        
        if connection:
            print("✅ Statik IP ile bağlantı başarılı!")
            
            # Test sorgusu çalıştır
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            result = cursor.fetchone()
            
            if result:
                print("✅ Test sorgusu başarılı!")
                print(f"Sonuç: {result}")
            
            # Database bilgilerini al
            cursor.execute("SELECT SYSDATE FROM DUAL")
            result = cursor.fetchone()
            print(f"📅 Sistem tarihi: {result[0]}")
            
            # Bağlantıyı kapat
            oracle_conn.close()
            return True
            
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return False

def test_connection_pool():
    """Connection pool ile statik IP bağlantısını test et"""
    
    try:
        print("🔄 Connection pool ile statik IP test ediliyor...")
        
        with get_db_connection() as connection:
            if connection:
                print("✅ Connection pool ile bağlantı başarılı!")
                
                # Test sorgusu
                cursor = connection.cursor()
                cursor.execute("SELECT USER FROM DUAL")
            
                result = cursor.fetchone()
                
                if result:
                    print(f"👤 Bağlı kullanıcı: {result[0]}")
                
                return True
                
    except Exception as e:
        print(f"❌ Connection pool hatası: {e}")
        return False

def create_env_file():
    """Örnek .env dosyası oluştur"""
    
    env_content = """# Oracle Database Bağlantısı - SADECE Statik IP
# Cloud Wallet KULLANILMAZ - Zorunlu statik IP bağlantısı
# Bu dosyayı düzenleyerek gerçek değerleri girin

# Oracle Database Credentials
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password

# ZORUNLU: Statik IP Konfigürasyonu
ORACLE_STATIC_IP=192.168.1.100
ORACLE_PORT=1521

# ZORUNLU: Database Tanımlayıcısı (Service Name VEYA SID - ikisinden birini kullanın)
# Seçenek 1: Service Name kullanarak
ORACLE_SERVICE_NAME=ORCL

# Seçenek 2: SID kullanarak (Service Name yerine)
# ORACLE_SID=ORCL

# NOT: ORACLE_STATIC_IP yerine gerçek database sunucunuzun IP adresini yazın
# NOT: ORACLE_SERVICE_NAME veya ORACLE_SID'den sadece birini tanımlayın
# NOT: Cloud wallet ayarları kaldırıldı - sadece statik IP kullanılır
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ .env dosyası oluşturuldu!")
        print("📝 Lütfen .env dosyasını düzenleyerek gerçek değerleri girin")
        return True
    except Exception as e:
        print(f"❌ .env dosyası oluşturulamadı: {e}")
        return False

def main():
    """Ana fonksiyon"""
    print("🚀 Mevcut Oracle Konfigürasyonu ile Statik IP Bağlantı Testi")
    print("=" * 60)
    
    # .env dosyası var mı kontrol et
    if not os.path.exists('.env'):
        print("❌ .env dosyası bulunamadı!")
        print("📝 .env dosyası oluşturuluyor...")
        if create_env_file():
            print("\n📋 Lütfen .env dosyasını düzenleyerek gerçek değerleri girin")
            print("   Sonra bu testi tekrar çalıştırın")
            return
        else:
            print("❌ .env dosyası oluşturulamadı!")
            return
    
    print("✅ .env dosyası bulundu")
    print()
    
    # Test 1: Direkt bağlantı
    print("📋 Test 1: Statik IP ile Direkt Bağlantı")
    test1_result = test_static_ip_connection()
    print()
    
    if test1_result:
        # Test 2: Connection pool
        print("📋 Test 2: Connection Pool ile Statik IP")
        test2_result = test_connection_pool()
        print()
        
        # Sonuç özeti
        print("📊 Test Sonuçları:")
        print(f"   Test 1 (Direkt): {'✅ Başarılı' if test1_result else '❌ Başarısız'}")
        print(f"   Test 2 (Pool): {'✅ Başarılı' if test2_result else '❌ Başarısız'}")
        
        if test1_result and test2_result:
            print("\n🎉 Tüm testler başarılı! Statik IP ile bağlantı çalışıyor.")
            print("🌐 Mevcut Oracle konfigürasyonu statik IP ile çalışıyor!")
        else:
            print("\n⚠️  Bazı testler başarısız. Lütfen konfigürasyonu kontrol edin.")
    else:
        print("❌ İlk test başarısız oldu. Diğer testler atlandı.")

if __name__ == "__main__":
    main()
