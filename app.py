#!/usr/bin/env python3
"""
🚀 تطبيق نظام التداول الآلي الرئيسي - التوقيت السعودي
"""

import logging
import os
import sys

# 🛠️ الإصلاح: إعداد التسجيل قبل تحميل أي وحدات
def setup_initial_logging():
    """إعداد التسجيل الأولي لضمان ظهور الرسائل من البداية"""
    # التحقق من متغير البيئة لـ Render
    if os.getenv('RENDER', 'false').lower() == 'true':
        # في Render، استخدام مستوى تسجيل مناسب
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    logger = logging.getLogger(__name__)
    logger.info("🚀 بدء تشغيل نظام التداول الآلي...")
    
    # تسجيل معلومات البيئة
    logger.info(f"🎯 بيئة التشغيل: {'Render' if os.getenv('RENDER') else 'Local'}")
    logger.info(f"📦 Python: {sys.version}")
    logger.info(f"📁 المسار: {os.path.dirname(os.path.abspath(__file__))}")
    
    return logger

# استدعاء الإعداد الأولي
logger = setup_initial_logging()

# تحميل النظام بشكل آمن
try:
    from core.trading_system import TradingSystem
    from utils.time_utils import saudi_time
    
    # إنشاء النظام بشكل متأخر للتقليل من الأخطاء المبكرة
    SYSTEM_INITIALIZED = False
    system = None
    
    def initialize_system():
        """تهيئة النظام بأمان"""
        global system, SYSTEM_INITIALIZED
        
        if not SYSTEM_INITIALIZED:
            try:
                logger.info("🔧 جاري تهيئة نظام التداول...")
                system = TradingSystem()
                SYSTEM_INITIALIZED = True
                logger.info("✅ تم تهيئة النظام بنجاح")
                
                # التحقق من أن النظام يعمل
                if hasattr(system, 'app'):
                    logger.info("✅ تطبيق Flask جاهز")
                else:
                    logger.error("❌ تطبيق Flask غير متوفر")
                    raise RuntimeError("تطبيق Flask غير متوفر")
                    
            except Exception as e:
                logger.error(f"❌ فشل تهيئة النظام: {e}")
                import traceback
                logger.error(f"🔍 تفاصيل الخطأ:\n{traceback.format_exc()}")
                raise
    
    # تهيئة النظام فوراً
    initialize_system()
    
    # الحصول على التطبيق لاستخدامه مع gunicorn
    app = system.app
    
    # إضافة نقطة نهاية للتحقق من صحة الخادم
    @app.route('/server_health')
    def server_health():
        """نقطة نهاية للتحقق من صحة الخادم"""
        return {
            'status': 'healthy',
            'service': 'Trading System',
            'python_version': sys.version,
            'render_environment': bool(os.getenv('RENDER')),
            'gunicorn_ready': True,
            'system_initialized': SYSTEM_INITIALIZED,
            'timestamp': saudi_time.now().isoformat() if SYSTEM_INITIALIZED else 'NOT_INITIALIZED'
        }
    
    logger.info("✅ تطبيق Flask جاهز لاستخدام gunicorn")
    
except ImportError as e:
    logger.error(f"❌ خطأ في استيراد الوحدات: {e}")
    import traceback
    logger.error(f"🔍 تفاصيل الخطأ:\n{traceback.format_exc()}")
    
    # إنشاء تطبيق Flask بسيط كحل بديل
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def fallback_home():
        return {'status': 'fallback', 'error': 'System initialization failed'}
    
    @app.route('/health')
    def fallback_health():
        return {'status': 'fallback', 'message': 'Running in fallback mode'}

def main():
    """الدالة الرئيسية للتطبيق بالتوقيت السعودي"""
    try:
        # التحقق من أن النظام مهيأ
        if not SYSTEM_INITIALIZED or system is None:
            logger.error("❌ النظام غير مهيأ بشكل صحيح")
            raise RuntimeError("System not properly initialized")
        
        current_time = saudi_time.format_time()
        logger.info(f"⏰ التوقيت السعودي الحالي: {current_time} 🇸🇦")
        
        # 🔍 فحص أن النظام يعمل بالتوقيت السعودي
        timezone_info = saudi_time.get_timezone_info()
        logger.info(f"📍 معلومات النطاق الزمني: {timezone_info['timezone']} ({timezone_info['offset']})")
        
        if 'AST' not in timezone_info['name'] and '+03' not in timezone_info['offset']:
            logger.warning("⚠️ تحذير: قد لا يكون التوقيت مضبوطاً على السعودي")
        else:
            logger.info("✅ التوقيت السعودي مضبوط بشكل صحيح")
        
        logger.info(f"🌐 الخادم يعمل على المنفذ {system.port}")
        logger.info(f"🎯 إعدادات التصحيح: DEBUG={system.config.get('DEBUG', 'UNKNOWN')}")
        logger.info(f"📱 حالة التليجرام: {'✅ مفعل' if system.config.get('TELEGRAM_ENABLED') else '❌ معطل'}")
        logger.info(f"⏰ التوقيت المستخدم: السعودي 🇸🇦")
        logger.info("🔍 جاهز لاستقبال الإشارات مع تفاصيل كاملة في السجلات...")
        
        # 🛠️ التشغيل مع دعم متغيرات البيئة
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', system.port))
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        logger.info(f"🌍 الإعدادات النهائية: host={host}, port={port}, debug={debug}")
        
        # 🛠️ الإصلاح: تشغيل الخادم مع معالجة الأخطاء
        system.app.run(
            host=host, 
            port=port, 
            debug=debug,
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"❌ فشل تشغيل النظام: {e}")
        import traceback
        logger.error(f"🔍 تفاصيل الخطأ:\n{traceback.format_exc()}")
        sys.exit(1)

# ✅ هذا مهم جداً لـ Render: جعل التطبيق متاحاً لـ gunicorn
if __name__ == '__main__':
    main()
