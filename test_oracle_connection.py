#!/usr/bin/env python3
"""
Oracle Database Connection Test Script
Bu script Oracle veritabanına statik IP ile bağlantıyı test eder.
"""

import os
import sys
from dotenv import load_dotenv
import oracledb

def test_oracle_connection():
    """Test Oracle database connection with static IP"""
    
    # Load environment variables
    load_dotenv()
    
    # Get connection parameters
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")
    
    print("🔍 Oracle Bağlantı Testi")
    print("=" * 50)
    
    # Check if environment variables are set
    if not user:
        print("❌ HATA: ORACLE_USER environment variable tanımlanmamış!")
        print("   .env dosyasında ORACLE_USER=your_username ekleyin")
        return False
    
    if not password:
        print("❌ HATA: ORACLE_PASSWORD environment variable tanımlanmamış!")
        print("   .env dosyasında ORACLE_PASSWORD=your_password ekleyin")
        return False
    
    if not dsn:
        print("❌ HATA: ORACLE_DSN environment variable tanımlanmamış!")
        print("   .env dosyasında ORACLE_DSN=192.168.1.100:1521/ORCL ekleyin")
        return False
    
    print(f"👤 Kullanıcı: {user}")
    print(f"🌐 DSN: {dsn}")
    print(f"🔐 Şifre: {'*' * len(password) if password else 'Tanımlanmamış'}")
    print()
    
    try:
        # Enable thin mode
        oracledb.thin = True
        
        print("🔄 Bağlantı kuruluyor...")
        
        # Test connection
        connection = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        
        print("✅ Bağlantı başarılı!")
        
        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT SYSDATE FROM DUAL")
        result = cursor.fetchone()
        
        print(f"📅 Oracle Sunucu Zamanı: {result[0]}")
        
        # Test version
        cursor.execute("SELECT * FROM V$VERSION WHERE ROWNUM = 1")
        version = cursor.fetchone()
        print(f"🔧 Oracle Versiyonu: {version[0]}")
        
        # Close connection
        cursor.close()
        connection.close()
        
        print("✅ Test tamamlandı - Bağlantı çalışıyor!")
        return True
        
    except oracledb.Error as e:
        print(f"❌ Oracle Bağlantı Hatası: {e}")
        print()
        print("🔧 Olası Çözümler:")
        print("1. Oracle sunucusunun çalıştığından emin olun")
        print("2. IP adresinin doğru olduğunu kontrol edin")
        print("3. Port numarasının doğru olduğunu kontrol edin (varsayılan: 1521)")
        print("4. SID/Service Name'in doğru olduğunu kontrol edin")
        print("5. Kullanıcı adı ve şifrenin doğru olduğunu kontrol edin")
        print("6. Oracle sunucusunun uzak bağlantılara izin verdiğinden emin olun")
        return False
        
    except Exception as e:
        print(f"❌ Genel Hata: {e}")
        return False

def main():
    """Main function"""
    print("Oracle Database Connection Test")
    print("Bu script Oracle veritabanına statik IP ile bağlantıyı test eder.")
    print()
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  UYARI: .env dosyası bulunamadı!")
        print("   Lütfen .env dosyası oluşturun ve Oracle bağlantı bilgilerini ekleyin:")
        print()
        print("   ORACLE_USER=your_username")
        print("   ORACLE_PASSWORD=your_password")
        print("   ORACLE_DSN=192.168.1.100:1521/ORCL")
        print()
        return
    
    success = test_oracle_connection()
    
    if success:
        print("\n🎉 Oracle bağlantısı başarılı! Uygulamanızı çalıştırabilirsiniz.")
        sys.exit(0)
    else:
        print("\n💥 Oracle bağlantısı başarısız! Lütfen ayarları kontrol edin.")
        sys.exit(1)

if __name__ == "__main__":
    main()
