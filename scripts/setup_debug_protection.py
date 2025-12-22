# scripts/setup_debug_protection.py
"""
🛠️ سكريبت تهيئة حماية التصحيح
"""

import os
import secrets
import sys
import re

def setup_debug_protection():
    """إعداد حماية التصحيح"""
    
    print("🛠️ إعداد حماية واجهات التصحيح")
    print("=" * 50)
    
    env_file = ".env"
    
    # التحقق من وجود الملف
    if not os.path.exists(env_file):
        print(f"❌ ملف {env_file} غير موجود")
        print("📝 إنشاء ملف .env جديد...")
        
        # إنشاء ملف .env جديد
        with open(env_file, 'w') as f:
            f.write("# 🔒 إعدادات حماية واجهات التصحيح\n")
            f.write("DEBUG_ENABLED=false\n")
            f.write("DEBUG_API_KEY=\n")
            f.write("DEBUG_ALLOWED_IPS=\n")
            f.write("LOG_DEBUG_ACCESS=true\n")
            f.write("DEBUG_RATE_LIMIT_ENABLED=true\n")
            f.write("DEBUG_RATE_LIMIT_REQUESTS=60\n")
            f.write("DEBUG_RATE_LIMIT_PERIOD=60\n")
            f.write("DEBUG_HEADER_NAME=X-Debug-Key\n")
        
        print(f"✅ تم إنشاء {env_file}")
    
    # قراءة الملف
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # البحث عن إعدادات التصحيح
    debug_enabled = False
    debug_key_exists = False
    has_changes = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if line.startswith('DEBUG_ENABLED='):
            value = line.split('=', 1)[1].strip().lower()
            debug_enabled = value == 'true'
        
        if line.startswith('DEBUG_API_KEY='):
            key_value = line.split('=', 1)[1].strip()
            debug_key_exists = bool(key_value)
    
    # إذا كان التصحيح مفعلاً بدون مفتاح
    if debug_enabled and not debug_key_exists:
        print("⚠️ DEBUG_ENABLED=true لكن DEBUG_API_KEY فارغ!")
        print("🔑 توليد مفتاح آمن...")
        
        # توليد مفتاح آمن
        new_key = secrets.token_urlsafe(32)
        masked_key = new_key[:8] + "..." + new_key[-8:]
        print(f"✅ تم توليد مفتاح جديد: {masked_key}")
        
        # تحديث الملف
        new_lines = []
        key_updated = False
        
        for line in lines:
            if line.strip().startswith('DEBUG_API_KEY='):
                new_lines.append(f'DEBUG_API_KEY={new_key}\n')
                key_updated = True
                has_changes = True
            else:
                new_lines.append(line)
        
        # إذا لم يكن المفتاح موجوداً أصلاً
        if not key_updated:
            # إضافة سطر جديد في نهاية القسم
            for i, line in enumerate(new_lines):
                if line.strip().startswith('DEBUG_ENABLED='):
                    # إدراج بعد DEBUG_ENABLED
                    new_lines.insert(i + 1, f'DEBUG_API_KEY={new_key}\n')
                    has_changes = True
                    break
        
        lines = new_lines
    
    # التأكد من وجود جميع الإعدادات المطلوبة
    required_settings = {
        'DEBUG_ENABLED': 'false',
        'DEBUG_API_KEY': '',
        'DEBUG_ALLOWED_IPS': '',
        'LOG_DEBUG_ACCESS': 'true',
        'DEBUG_RATE_LIMIT_ENABLED': 'true',
        'DEBUG_RATE_LIMIT_REQUESTS': '60',
        'DEBUG_RATE_LIMIT_PERIOD': '60',
        'DEBUG_HEADER_NAME': 'X-Debug-Key'
    }
    
    for setting, default in required_settings.items():
        setting_exists = any(line.strip().startswith(f'{setting}=') for line in lines)
        
        if not setting_exists:
            print(f"➕ إضافة إعداد مفقود: {setting}")
            lines.append(f'{setting}={default}\n')
            has_changes = True
    
    # إذا كانت هناك تغييرات، كتابة الملف
    if has_changes:
        # ترتيب الإعدادات
        debug_section = []
        other_lines = []
        
        for line in lines:
            if any(line.strip().startswith(f'{s}=') for s in required_settings.keys()):
                debug_section.append(line)
            else:
                other_lines.append(line)
        
        # كتابة الملف بترتيب منظم
        with open(env_file, 'w') as f:
            # كتابة الأسطر الأخرى أولاً
            for line in other_lines:
                if not line.strip().startswith('# 🔒'):
                    f.write(line)
            
            # كتابة قسم التصحيح
            f.write('\n# 🔒 إعدادات حماية واجهات التصحيح\n')
            for setting in required_settings.keys():
                for line in debug_section:
                    if line.strip().startswith(f'{setting}='):
                        f.write(line)
                        break
        
        print("✅ تم تحديث ملف .env")
        
        # إنشاء ملف .env.example
        print("📝 إنشاء ملف .env.example...")
        example_lines = []
        
        for line in lines:
            if 'KEY' in line or 'PASSWORD' in line or 'SECRET' in line or 'TOKEN' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    example_lines.append(f'{parts[0]}=YOUR_{parts[0]}_HERE\n')
                else:
                    example_lines.append(line)
            else:
                example_lines.append(line)
        
        with open('.env.example', 'w') as f:
            f.writelines(example_lines)
        
        print("✅ تم إنشاء ملف .env.example")
    
    elif not debug_enabled:
        print("✅ DEBUG_ENABLED=false - واجهات التصحيح معطلة (آمن)")
    else:
        print("✅ DEBUG_ENABLED=true مع وجود مفتاح حماية")
    
    # نصائح أمان
    print("\n🔒 نصائح أمان لواجهات التصحيح:")
    print("=" * 50)
    print("1. في بيئة الإنتاج، ضع DEBUG_ENABLED=false")
    print("2. لا تشارك DEBUG_API_KEY مع أي شخص")
    print("3. استخدم DEBUG_ALLOWED_IPS لتقييد IPs المسموح بها")
    print("4. راجع سجلات الوصول بانتظام")
    print("5. استخدم rate limiting (مفعل افتراضيًا)")
    print("6. تأكد من استخدام HTTPS في الإنتاج")
    print("\n🔧 مثال للاستخدام:")
    print("   curl -H 'X-Debug-Key: YOUR_KEY' http://localhost:5000/debug/stats")
    
    return True

def check_current_protection():
    """فحص حالة الحماية الحالية"""
    
    print("\n🔍 فحص حالة حماية التصحيح الحالية")
    print("=" * 50)
    
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("❌ ملف .env غير موجود")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    # البحث عن الإعدادات
    patterns = {
        'DEBUG_ENABLED': r'DEBUG_ENABLED\s*=\s*(\w+)',
        'DEBUG_API_KEY': r'DEBUG_API_KEY\s*=\s*(\S+)',
        'DEBUG_ALLOWED_IPS': r'DEBUG_ALLOWED_IPS\s*=\s*([\d\.,\s]+)',
    }
    
    findings = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            findings[key] = match.group(1).strip()
        else:
            findings[key] = None
    
    # تحليل النتائج
    debug_enabled = findings.get('DEBUG_ENABLED', '').lower() == 'true'
    has_api_key = bool(findings.get('DEBUG_API_KEY'))
    has_allowed_ips = bool(findings.get('DEBUG_ALLOWED_IPS'))
    
    print(f"🔐 DEBUG_ENABLED: {'✅ مفعل' if debug_enabled else '❌ معطل'}")
    print(f"🔑 DEBUG_API_KEY: {'✅ موجود' if has_api_key else '❌ مفقود'}")
    print(f"🌐 DEBUG_ALLOWED_IPS: {'✅ محدد' if has_allowed_ips else '⚠️ غير محدد'}")
    
    # تقدير مستوى الأمان
    if not debug_enabled:
        print("\n🎉 مستوى الأمان: عالي - التصحيح معطل")
        security_level = "HIGH"
    elif debug_enabled and has_api_key and has_allowed_ips:
        print("\n👍 مستوى الأمان: متوسط - مع حماية كافية")
        security_level = "MEDIUM"
    elif debug_enabled and has_api_key:
        print("\n⚠️ مستوى الأمان: منخفض - تحتاج إلى تحديد IPs")
        security_level = "LOW"
    else:
        print("\n🚨 مستوى الأمان: خطير - لا توجد حماية!")
        security_level = "CRITICAL"
    
    return security_level

if __name__ == "__main__":
    print("🛡️ نظام حماية واجهات التصحيح")
    print("=" * 50)
    
    # فحص الحالة الحالية
    security_level = check_current_protection()
    
    # عرض خيارات
    print("\n🔧 الخيارات المتاحة:")
    print("1. إعداد حماية تلقائية (موصى به)")
    print("2. عرض حالة الحماية فقط")
    print("3. إنشاء مفتاح جديد فقط")
    
    try:
        choice = input("\nاختر الخيار (1-3): ").strip()
        
        if choice == '1':
            success = setup_debug_protection()
            if success:
                print("\n✅ تم إعداد الحماية بنجاح!")
                # فحص الحالة الجديدة
                check_current_protection()
        elif choice == '2':
            check_current_protection()
        elif choice == '3':
            new_key = secrets.token_urlsafe(32)
            print(f"\n🔑 المفتاح الجديد: {new_key}")
            print("\n📝 قم بنسخه وإضافته إلى ملف .env:")
            print(f"DEBUG_API_KEY={new_key}")
        else:
            print("❌ خيار غير صالح")
        
        print("\n🎯 تم الانتهاء!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ تم إلغاء العملية")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        sys.exit(1)
