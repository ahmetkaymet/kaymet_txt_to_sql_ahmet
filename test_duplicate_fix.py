#!/usr/bin/env python3
"""
Duplicate API Çağrıları Test Script'i
Bu script, frontend'deki duplicate API çağrılarının önlenip önlenmediğini test eder.
"""

import time
import requests
from datetime import datetime

def test_sessions_endpoint():
    """Sessions endpoint'ini test eder ve duplicate çağrıları kontrol eder"""
    
    print("🚀 Enhanced Duplicate API Çağrıları Test")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Tek çağrı
    print(f"\n📊 Test 1: Tek sessions çağrısı - {datetime.now().strftime('%H:%M:%S')}")
    try:
        response1 = requests.get(f"{base_url}/sessions")
        print(f"✓ Status: {response1.status_code}")
        print(f"✓ Response size: {len(response1.content)} bytes")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Hızlı ardışık çağrılar (duplicate önleme testi)
    print(f"\n📊 Test 2: Hızlı ardışık çağrılar (100ms aralıkla) - {datetime.now().strftime('%H:%M:%S')}")
    print("   Bu testte backend duplicate request'leri önlemeli ve log'lar tekrarlanmamalı")
    for i in range(5):
        try:
            response = requests.get(f"{base_url}/sessions")
            print(f"  Call {i+1}: Status {response.status_code}, Size {len(response.content)} bytes")
            time.sleep(0.1)  # 100ms bekle
        except Exception as e:
            print(f"  Call {i+1}: Error {e}")
    
    # Test 3: Normal aralıklarla çağrılar
    print(f"\n📊 Test 3: Normal aralıklarla çağrılar (1s aralıkla) - {datetime.now().strftime('%H:%M:%S')}")
    print("   Bu testte normal çağrılar yapılmalı")
    for i in range(3):
        try:
            response = requests.get(f"{base_url}/sessions")
            print(f"  Call {i+1}: Status {response.status_code}, Size {len(response.content)} bytes")
            time.sleep(1)  # 1 saniye bekle
        except Exception as e:
            print(f"  Call {i+1}: Error {e}")
    
    print("\n🎉 Test completed!")
    print("\n💡 Backend log'larında:")
    print("   - Hızlı ardışık çağrılarda duplicate log'lar görünmemeli")
    print("   - Normal aralıklarla çağrılarda log'lar görünmeli")
    print("   - Frontend'de console'da 'Fetch skipped' mesajları görünmeli")

if __name__ == "__main__":
    test_sessions_endpoint()
