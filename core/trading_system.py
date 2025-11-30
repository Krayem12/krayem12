# trading_system.py
import schedule
import threading
import time
import logging
from flask import Flask
from datetime import datetime

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
        self.signals = self.config_manager.signals  # 🛠️ حفظ المرجع للإشارات
        self.keywords = self.config_manager.keywords
        self.port = self.config_manager.port

        # ✅ التحقق من اكتمال الإعدادات الأساسية أولاً
        if not self.config or not self.signals:
            raise ValueError("❌ فشل تحميل الإعدادات أو الإشارات")
        
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
            logger.info(f"   📁 {category}: {len(signals)} signals")
            total_signals += len(signals)

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
        return {
            "status": "active",
            "version": "11.0_detailed_trend_with_group4_group5",
            "timestamp": datetime.now().isoformat(),
            "port": self.port,
            "trading_mode": self.config['TRADING_MODE'],
            "group1_trend_mode": self.config['GROUP1_TREND_MODE'],
            "group2_enabled": self.config['GROUP2_ENABLED'],
            "group3_enabled": self.config['GROUP3_ENABLED'],
            "group4_enabled": self.config['GROUP4_ENABLED'],
            "group5_enabled": self.config['GROUP5_ENABLED'],
            "detailed_trend_notifications": bool(self.trade_manager.group_manager and self.trade_manager.notification_manager)
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