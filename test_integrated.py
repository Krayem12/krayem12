#!/usr/bin/env python3
"""
اختبار جميع نماذج الرسائل الجديدة
"""

import requests
import time
import sys
import os

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_all_message_types():
    """اختبار جميع أنواع الرسائل الجديدة"""
    base_url = "http://localhost:10000"
    
    print("🧪 اختبار جميع نماذج الرسائل الجديدة")
    print("=" * 60)
    
    # إشارات اختبارية تشمل جميع الأنواع
    test_scenarios = [
        {
            "name": "📊 إشارة الاتجاه العام",
            "signal": "SPX500 | bullish_catcher | OPEN | CLOSE",
            "description": "اختبار رسالة الاتجاه العام ☰☰☰"
        },
        {
            "name": "🚀 إشارة دخول صفقة",
            "signal": "SPX500 | bullish_sbos_buy | OPEN | CLOSE", 
            "description": "اختبار رسالة الدخول ✦✦✦"
        },
        {
            "name": "✅ إشارة تأكيد الاتجاه",
            "signal": "SPX500 | bullish_tracer | OPEN | CLOSE",
            "description": "اختبار رسالة التأكيد ✅ 📊"
        },
        {
            "name": "🚪 إشارة خروج صفقة",
            "signal": "SPX500 | exit_buy | CLOSE | OPEN",
            "description": "اختبار رسالة الخروج ════"
        },
        {
            "name": "🔔 إشارة تأكيد إضافية",
            "signal": "SPX500 | bullish_confirmation+ | OPEN | CLOSE",
            "description": "اختبار إشارة التأكيد مع الرموز الخاصة"
        }
    ]
    
    print("📋 سيناريوهات الاختبار:")
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"   {i}. {scenario['name']}: {scenario['signal']}")
    
    print("\n🚀 بدء الاختبار...")
    print("=" * 60)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📨 [{i}/{len(test_scenarios)}] {scenario['name']}")
        print(f"   📝 {scenario['description']}")
        print(f"   🔍 الإشارة: {scenario['signal']}")
        
        try:
            response = requests.post(
                f"{base_url}/webhook",
                data=scenario['signal'],
                headers={'Content-Type': 'text/plain'},
                timeout=10
            )
            
            result = response.json()
            status = result.get('status', 'unknown')
            message = result.get('message', '')
            
            if status == 'success':
                print(f"   ✅ النتيجة: نجاح - {message}")
            else:
                print(f"   ⚠️  النتيجة: {status} - {message}")
            
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
        
        time.sleep(2)  # انتظار بين الإشارات
    
    print("\n" + "=" * 60)
    print("🎯 اختبار نماذج الرسائل اكتمل!")
    print("💡 يمكنك فتح http://localhost:10000/test لمزيد من الاختبارات")

def test_complete_workflow():
    """اختبار سيناريو كامل من البداية إلى النهاية"""
    base_url = "http://localhost:10000"
    
    print("\n🔄 اختبار سيناريو تداول كامل")
    print("=" * 50)
    
    workflow_signals = [
        "SPX500 | bullish_catcher | OPEN | CLOSE",           # تحديد الاتجاه
        "SPX500 | bullish_tracer | OPEN | CLOSE",            # تأكيد الاتجاه  
        "SPX500 | bullish_sbos_buy | OPEN | CLOSE",          # دخول صفقة
        "SPX500 | bullish_confirmation+ | OPEN | CLOSE",     # تأكيد إضافي
        "SPX500 | exit_buy | CLOSE | OPEN"                   # خروج صفقة
    ]
    
    for i, signal in enumerate(workflow_signals, 1):
        print(f"\n🔄 [{i}/{len(workflow_signals)}] مرحلة {i}: {signal}")
        
        try:
            response = requests.post(
                f"{base_url}/webhook",
                data=signal,
                headers={'Content-Type': 'text/plain'},
                timeout=10
            )
            
            result = response.json()
            print(f"   📊 النتيجة: {result.get('status', 'unknown')}")
            
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
        
        time.sleep(2)
    
    print("\n✅ سيناريو التداول الكامل اكتمل!")

if __name__ == "__main__":
    test_all_message_types()
    test_complete_workflow()