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
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    logger = logging.getLogger(__name__)
    logger.info("🚀 بدء تشغيل نظام التداول الآلي...")
    return logger

# استدعاء الإعداد الأولي
logger = setup_initial_logging()

from core.trading_system import TradingSystem
from utils.time_utils import saudi_time

def main():
    """الدالة الرئيسية للتطبيق بالتوقيت السعودي"""
    try:
        current_time = saudi_time.format_time()
        logger.info(f"⏰ التوقيت السعودي الحالي: {current_time} 🇸🇦")
        
        # 🔍 فحص أن النظام يعمل بالتوقيت السعودي
        timezone_info = saudi_time.get_timezone_info()
        logger.info(f"📍 معلومات النطاق الزمني: {timezone_info['timezone']} ({timezone_info['offset']})")
        
        if 'AST' not in timezone_info['name'] and '+03' not in timezone_info['offset']:
            logger.warning("⚠️ تحذير: قد لا يكون التوقيت مضبوطاً على السعودي")
        else:
            logger.info("✅ التوقيت السعودي مضبوط بشكل صحيح")
        
        # 🛠️ الإصلاح: إنشاء النظام مع معالجة الأخطاء
        system = TradingSystem()
        
        logger.info(f"🌐 الخادم يعمل على المنفذ {system.port}")
        logger.info(f"🎯 إعدادات التصحيح: DEBUG={system.config['DEBUG']}, LOG_LEVEL={system.config['LOG_LEVEL']}")
        logger.info(f"📱 حالة التليجرام: {'✅ مفعل' if system.config['TELEGRAM_ENABLED'] else '❌ معطل'}")
        logger.info(f"⏰ التوقيت المستخدم: السعودي 🇸🇦")
        logger.info("🔍 جاهز لاستقبال الإشارات مع تفاصيل كاملة في السجلات...")
        
        # 🛠️ الإصلاح: تشغيل الخادم مع معالجة الأخطاء
        system.app.run(
            host='0.0.0.0', 
            port=system.port, 
            debug=system.config['DEBUG'],
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"❌ فشل تشغيل النظام: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
else:
    # 🛠️ الإصلاح: للاستخدام مع gunicorn
    system = TradingSystem()
    app = system.app