#!/usr/bin/env python3
import logging
from core.trading_system import TradingSystem

# 🛠️ الإصلاح: إضافة رسائل تأكيد عند بدء التشغيل
print("🚀 Starting Trading System with COMPLETE METHOD IMPLEMENTATION + GROUP3...")
print("🔧 تفعيل وضع التصحيح والتفاصيل الكاملة...")

if __name__ == '__main__':
    system = TradingSystem()
    print(f"🌐 Server running on port {system.port}")
    print(f"🎯 إعدادات التصحيح: DEBUG={system.config['DEBUG']}, LOG_LEVEL={system.config['LOG_LEVEL']}")
    print(f"📱 حالة التليجرام: {'✅ مفعل' if system.config['TELEGRAM_ENABLED'] else '❌ معطل'}")
    print("🔍 جاهز لاستقبال الإشارات مع تفاصيل كاملة في اللوقو...")
    
    system.app.run(host='0.0.0.0', port=system.port, debug=False)
else:
    system = TradingSystem()
    app = system.app