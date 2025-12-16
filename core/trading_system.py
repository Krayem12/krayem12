# trading_system.py
import schedule
import threading
import time
import logging
from flask import Flask
from datetime import datetime
from typing import Dict, Optional

from config.config_manager import ConfigManager
from core.signal_processor import SignalProcessor
from core.trade_manager import TradeManager
from core.group_manager import GroupManager
from core.webhook_handler import WebhookHandler
from notifications.notification_manager import NotificationManager
from maintenance.cleanup_manager import CleanupManager

logger = logging.getLogger(__name__)

class TradingSystem:
    """🎯 Trading System with DETAILED TREND CHANGE NOTIFICATIONS"""

    def __init__(self):
        logger.info("🚀 Starting Trading System with COMPLETE METHOD IMPLEMENTATION + GROUP3 + GROUP4 + GROUP5...")
        try:
            self.setup_managers()
            self.setup_flask()
            self.setup_scheduler()
            self.display_system_info()
            logger.info("✅ System initialized successfully with detailed trend notifications")
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise

    def setup_managers(self):
        """🎯 Setup all manager classes with cross-references"""
        logger.info("🔧 جاري تهيئة المديرين...")
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.port = self.config_manager.port

        # 🔧 FIXED: التحقق من اكتمال الإعدادات الأساسية أولاً
        if not self.config:
            raise ValueError("❌ فشل تحميل الإعدادات")
        
        # 🔧 FIXED: التحقق من وجود الإشارات وتحقيق الحد الأدنى
        self.signals = self.config_manager.signals
        if not self.signals or len(self.signals) == 0:
            logger.error("❌ فشل تحميل أي إشارات")
            raise ValueError("❌ فشل تحميل الإشارات")
        
        # حساب إجمالي الإشارات المحملة
        total_signals = sum(len(signal_list) for signal_list in self.signals.values() if signal_list)
        if total_signals == 0:
            logger.warning("⚠️ تم تحميل الإشارات ولكنها فارغة")
        
        self.keywords = self.config_manager.keywords
        
        # 🛠️ التحقق النهائي من إعدادات الخادم الخارجي
        logger.info(f"🔍 تحقق نهائي - EXTERNAL_SERVER_ENABLED: {self.config['EXTERNAL_SERVER_ENABLED']}")
        logger.info(f"🔍 تحقق نهائي - EXTERNAL_SERVER_URL: {self.config['EXTERNAL_SERVER_URL']}")
        
        logger.info("✅ تم تحميل الإعدادات بنجاح، جاري تهيئة المديرين...")

        # Initialize core managers
        self.signal_processor = SignalProcessor(self.config, self.signals, self.keywords)
        self.trade_manager = TradeManager(self.config)
        
        # 🎯 NEW: Pass trade_manager to group_manager
        self.group_manager = GroupManager(self.config, self.trade_manager)
        
        self.notification_manager = NotificationManager(self.config)
        
        # 🆕 إعداد الوصول المتبادل بين المديرين
        self.trade_manager.set_group_manager(self.group_manager)
        self.trade_manager.set_notification_manager(self.notification_manager)
        
        # 🛠️ الإصلاح: إضافة notification_manager كمُعامل رابع لـ CleanupManager
        self.cleanup_manager = CleanupManager(
            self.config, 
            self.trade_manager, 
            self.group_manager,
            self.notification_manager  # ✅ تمت إضافته هنا
        )
        
        self.webhook_handler = WebhookHandler(
            self.config,
            self.signal_processor,
            self.group_manager,
            self.trade_manager,
            self.notification_manager,
            self.cleanup_manager
        )
        
        logger.info("✅ تم تهيئة جميع المديرين بنجاح")

    def setup_flask(self):
        """🎯 Setup Flask app with routes"""
        logger.info("🔧 جاري تهيئة تطبيق Flask...")
        
        self.app = Flask(__name__)
        
        # 🛠️ الإصلاح: إضافة route أساسي للفحص
        @self.app.route('/')
        def home():
            return {
                "status": "running",
                "system": "Trading System",
                "version": "11.0_detailed_trend_with_group4_group5",
                "timestamp": datetime.now().isoformat()
            }
        
        # Register routes from webhook handler
        self.webhook_handler.register_routes(self.app)
        
        # Additional system routes
        @self.app.route('/status')
        def status():
            return self.get_system_status()

        # 🆕 إضافة مسار لعرض إحصائيات الإشارات
        @self.app.route('/signal_stats/<symbol>')
        def signal_stats(symbol):
            return self.get_signal_statistics(symbol)
        
        # 🔧 FIXED: إضافة مسار للصحة والاستعداد
        @self.app.route('/health')
        def health():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "config_manager": bool(self.config),
                    "signal_processor": bool(self.signal_processor),
                    "trade_manager": bool(self.trade_manager),
                    "group_manager": bool(self.group_manager),
                    "notification_manager": bool(self.notification_manager),
                    "webhook_handler": bool(self.webhook_handler)
                }
            }
            
        logger.info("✅ تم تهيئة تطبيق Flask والمسارات بنجاح")

    def setup_scheduler(self):
        """Setup daily cleanup scheduler"""
        self.cleanup_manager.setup_scheduler()

    def display_system_info(self):
        """🎯 Display system information"""
        self.config_manager.display_config()
        self.display_loaded_signals()
        
        # 🛠️ الإصلاح: التحقق من تطبيق الإعدادات
        self._verify_strategy_application()

    def _verify_strategy_application(self):
        """🛠️ التحقق من تطبيق استراتيجيات التداول بشكل صحيح"""
        logger.info("\n🔍 التحقق من تطبيق استراتيجيات التداول:")

        modes_to_check = [
            ('TRADING_MODE', 'النمط الأساسي'),
            ('TRADING_MODE1', 'النمط الإضافي 1'), 
            ('TRADING_MODE2', 'النمط الإضافي 2')
        ]
        
        for mode_key, mode_name in modes_to_check:
            mode_value = self.config.get(mode_key)
            
            # 🛠️ الإصلاح: TRADING_MODE دائماً مفعول
            if mode_key == 'TRADING_MODE':
                enabled = True  # ⬅️ النمط الأساسي مفعول دائمًا
                status = '✅ مفعل'
            else:
                enabled = self.config.get(f'{mode_key}_ENABLED', False)
                status = '✅ مفعل' if enabled else '❌ معطل'
            
            logger.info(f"   {mode_name}: {mode_value} ({status})")
            
            if enabled and not mode_value:
                logger.error(f"   ❌ {mode_name} مفعل ولكن لا توجد استراتيجية محددة!")
            elif enabled:
                logger.info(f"   ✅ {mode_name} مفعل ومسجل بشكل صحيح: {mode_value}")

    def display_loaded_signals(self):
        """🎯 Display loaded signals information"""
        logger.info("\n📊 Loaded Signals Summary:")
        total_signals = 0
        for category, signals in self.signals.items():
            if signals:
                logger.info(f"   📁 {category}: {len(signals)} signals")
                total_signals += len(signals)
            else:
                logger.info(f"   📁 {category}: ❌ NO SIGNALS")

        logger.info(f"\n📈 Total signals loaded: {total_signals}")
        
        # 🎯 NEW: Display strategy information
        logger.info(f"\n🎯 Active Trading Strategy: {self.config['TRADING_MODE']}")
        logger.info(f"   • Group1 Trend Mode: {self.config['GROUP1_TREND_MODE']}")
        logger.info(f"   • Group2 Enabled: {'✅ YES' if self.config['GROUP2_ENABLED'] else '❌ NO'}")
        logger.info(f"   • Group3 Enabled: {'✅ YES' if self.config['GROUP3_ENABLED'] else '❌ NO'}")
        logger.info(f"   • Group4 Enabled: {'✅ YES' if self.config['GROUP4_ENABLED'] else '❌ NO'}")
        logger.info(f"   • Group5 Enabled: {'✅ YES' if self.config['GROUP5_ENABLED'] else '❌ NO'}")
        
        # 🆕 عرض معلومات الإشعارات التفصيلية
        logger.info(f"\n🧹 Detailed Trend Notifications: {'✅ ACTIVE' if self.trade_manager.group_manager else '❌ INACTIVE'}")
        logger.info(f"📊 Signal Statistics Tracking: {'✅ ENABLED' if self.trade_manager.notification_manager else '❌ DISABLED'}")

    def get_system_status(self):
        """🎯 Get system status"""
        try:
            # 🔧 FIXED: التحقق من وجود المديرين قبل الوصول إليهم
            trade_manager_active = hasattr(self.trade_manager, 'group_manager') and self.trade_manager.group_manager is not None
            notification_manager_active = hasattr(self.trade_manager, 'notification_manager') and self.trade_manager.notification_manager is not None
            
            return {
                "status": "active",
                "version": "11.0_detailed_trend_with_group4_group5",
                "timestamp": datetime.now().isoformat(),
                "port": self.port,
                "trading_mode": self.config.get('TRADING_MODE', 'UNKNOWN'),
                "group1_trend_mode": self.config.get('GROUP1_TREND_MODE', 'UNKNOWN'),
                "group2_enabled": self.config.get('GROUP2_ENABLED', False),
                "group3_enabled": self.config.get('GROUP3_ENABLED', False),
                "group4_enabled": self.config.get('GROUP4_ENABLED', False),
                "group5_enabled": self.config.get('GROUP5_ENABLED', False),
                "detailed_trend_notifications": trade_manager_active and notification_manager_active
            }
        except Exception as e:
            logger.error(f"❌ Error in get_system_status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_signal_statistics(self, symbol: str):
        """🆕 الحصول على إحصائيات الإشارات لرمز معين"""
        try:
            stats = self.group_manager.get_group_stats(symbol)
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "statistics": stats
            }
        except Exception as e:
            return {"error": f"Failed to get signal statistics: {str(e)}"}

    def run(self):
        """تشغيل النظام"""
        try:
            logger.info(f"🚀 بدء تشغيل نظام التداول على المنفذ {self.port}")
            
            # 🔧 FIXED: إضافة معالجة للإغلاق النظيف
            import signal
            import sys
            
            def signal_handler(sig, frame):
                logger.info("🛑 استقبال إشارة إغلاق، جاري الإغلاق النظيف...")
                self.shutdown()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            self.app.run(
                host='0.0.0.0', 
                port=self.port, 
                debug=self.config.get('DEBUG', False),
                use_reloader=False
            )
            
        except Exception as e:
            logger.error(f"❌ فشل تشغيل النظام: {e}")
            raise

    def shutdown(self):
        """إغلاق النظام بشكل نظيف"""
        logger.info("🧹 جاري إغلاق النظام بشكل نظيف...")
        
        try:
            # إغلاق جميع المديرين
            if hasattr(self.trade_manager, 'cleanup_memory'):
                self.trade_manager.cleanup_memory()
            
            if hasattr(self.group_manager, 'cleanup_memory'):
                self.group_manager.cleanup_memory()
            
            if hasattr(self.signal_processor, 'cleanup_memory'):
                self.signal_processor.cleanup_memory()
            
            if hasattr(self.webhook_handler, 'cleanup_memory'):
                self.webhook_handler.cleanup_memory()
            
            logger.info("✅ تم إغلاق النظام بنجاح")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إغلاق النظام: {e}")

    def reload_configuration(self):
        """إعادة تحميل الإعدادات"""
        try:
            logger.info("🔄 محاولة إعادة تحميل الإعدادات...")
            
            # 🔧 FIXED: محاولة إعادة تحميل config_manager
            if hasattr(self.config_manager, 'reload_config'):
                success = self.config_manager.reload_config()
                if success:
                    # تحديث الإعدادات في جميع المديرين
                    self.config = self.config_manager.config
                    self.signals = self.config_manager.signals
                    self.keywords = self.config_manager.keywords
                    
                    # تحديث signal_processor
                    if self.signal_processor:
                        self.signal_processor.signals = self.signals
                        self.signal_processor.keywords = self.keywords
                        self.signal_processor.setup_signal_index()
                    
                    logger.info("✅ تم إعادة تحميل الإعدادات بنجاح")
                    return True
                else:
                    logger.error("❌ فشل إعادة تحميل الإعدادات")
                    return False
            else:
                logger.warning("⚠️ config_manager لا يدعم إعادة التحميل")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة تحميل الإعدادات: {e}")
            return False