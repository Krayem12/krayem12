#!/usr/bin/env python3
"""
🚀 تطبيق نظام التداول الآلي الرئيسي
"""

import logging
import os
import sys
from core.trading_system import TradingSystem

# 🛠️ الإصلاح: إعداد التسجيل قبل تحميل أي وحدات
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

logger = logging.getLogger(__name__)

def main():
    """الدالة الرئيسية للتطبيق"""
    try:
        print("🚀 Starting Trading System with COMPLETE METHOD IMPLEMENTATION + GROUP3 + GROUP4 + GROUP5...")
        print("🔧 تفعيل وضع التصحيح والتفاصيل الكاملة...")
        
        # 🛠️ الإصلاح: إنشاء النظام مع معالجة الأخطاء
        system = TradingSystem()
        
        print(f"🌐 Server running on port {system.port}")
        print(f"🎯 إعدادات التصحيح: DEBUG={system.config['DEBUG']}, LOG_LEVEL={system.config['LOG_LEVEL']}")
        print(f"📱 حالة التليجرام: {'✅ مفعل' if system.config['TELEGRAM_ENABLED'] else '❌ معطل'}")
        print("🔍 جاهز لاستقبال الإشارات مع تفاصيل كاملة في اللوقو...")
        
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