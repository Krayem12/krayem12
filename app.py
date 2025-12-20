#!/usr/bin/env python3
"""
🚀 تطبيق نظام التداول الآلي الرئيسي - التوقيت السعودي
الإصدار المصحح: إصلاح الثغرات الأمنية وتحسين الأداء
"""

import logging
import os
import sys

# ============ إصلاح 1: إعدادات أمان للتسجيل ============
def setup_secure_logging():
    """إعداد تسجيل آمن مع مراعاة الأمان"""
    
    # 🔒 إصلاح: تحديد مستوى التسجيل من متغير البيئة
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    if log_level not in valid_levels:
        log_level = 'INFO'
    
    # 🔒 إصلاح: إعداد مسار آمل للسجلات
    log_dir = os.getenv('LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 🔒 إصلاح: تنسيق آمن (بدون معلومات حساسة)
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'trading_system.log')),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )
    
    logger = logging.getLogger(__name__)
    
    # 🔒 إصلاح: تسجيل معلومات آمنة (بدون بيانات حساسة)
    logger.info("🚀 بدء تشغيل نظام التداول الآلي (نسخة مصححة)")
    return logger

# استدعاء الإعداد الآمن
logger = setup_secure_logging()

# ============ إصلاح 2: استيراد آمن مع معالجة الأخطاء ============
try:
    from core.trading_system import TradingSystem
    from utils.time_utils import saudi_time
except ImportError as e:
    logger.error(f"❌ خطأ في استيراد الوحدات: {e}")
    sys.exit(1)

def main():
    """الدالة الرئيسية للتطبيق بالتوقيت السعودي"""
    try:
        # 🔒 إصلاح: التحقق من وجود البيانات الحساسة في البيئة
        required_env_vars = ['SECRET_KEY', 'DATABASE_URL']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ متغيرات بيئة مفقودة: {missing_vars}")
            logger.error("يرجى إعداد ملف .env مع القيم المطلوبة")
            sys.exit(1)
        
        current_time = saudi_time.format_time()
        logger.info(f"⏰ التوقيت السعودي الحالي: {current_time} 🇸🇦")
        
        # 🔒 إصلاح: التحقق الآمن من النطاق الزمني
        try:
            timezone_info = saudi_time.get_timezone_info()
            logger.info(f"📍 معلومات النطاق الزمني: {timezone_info.get('timezone', 'غير معروف')}")
            
            # التحقق الآمن من التوقيت
            tz_name = timezone_info.get('name', '')
            tz_offset = timezone_info.get('offset', '')
            
            is_saudi_time = ('AST' in tz_name) or ('+03' in tz_offset)
            
            if not is_saudi_time:
                logger.warning(f"⚠️ تحذير: قد لا يكون التوقيت مضبوطاً على السعودي ({tz_name} - {tz_offset})")
            else:
                logger.info("✅ التوقيت السعودي مضبوط بشكل صحيح")
                
        except Exception as tz_error:
            logger.warning(f"⚠️ تحذير في التحقق من النطاق الزمني: {tz_error}")
        
        # 🔒 إصلاح: إنشاء النظام مع إعدادات آمنة
        system = TradingSystem()
        
        # 🔒 إصلاح: تسجيل معلومات آمنة فقط
        logger.info(f"🌐 جاهز للتشغيل على المنفذ: {system.port}")
        
        # 🔒 إصلاح: التحقق من وضع الإنتاج
        is_production = os.getenv('FLASK_ENV') == 'production'
        debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        
        if is_production and debug_mode:
            logger.critical("⚠️ ⚠️ ⚠️ تحذير أمني: وضع التصحيح مفعل في بيئة الإنتاج!")
        
        logger.info(f"🎯 وضع التشغيل: {'إنتاج' if is_production else 'تطوير'}")
        
        # 🔒 إصلاح: تشغيل الخادم مع إعدادات أمنية
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        
        logger.info(f"🚀 بدء تشغيل الخادم على {host}:{port}")
        
        # 🔒 إصلاح: منع وضع التصحيح في الإنتاج
        run_debug = debug_mode and not is_production
        
        system.app.run(
            host=host, 
            port=port, 
            debug=run_debug,  # 🔒 ممنوع في الإنتاج
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ إيقاف النظام بواسطة المستخدم")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ فشل تشغيل النظام: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
else:
    # 🔒 إصلاح: للاستخدام مع gunicorn/WSGI
    try:
        system = TradingSystem()
        app = system.app
        
        # 🔒 إصلاح: إعدادات أمنية إضافية للاستخدام مع WSGI
        if os.getenv('FLASK_ENV') == 'production':
            # تعطيل التصحيح في الإنتاج
            app.config['DEBUG'] = False
            app.config['PROPAGATE_EXCEPTIONS'] = True
            
            # إعدادات أمنية للجلسات
            app.config['SESSION_COOKIE_SECURE'] = True
            app.config['SESSION_COOKIE_HTTPONLY'] = True
            app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
            
    except Exception as e:
        logger.error(f"❌ فشل تهيئة النظام لـ WSGI: {e}")
        raise
