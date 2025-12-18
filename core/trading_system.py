# trading_system.py
import schedule
import threading
import time
import logging
import os
import json
from flask import Flask, render_template, jsonify
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
            self.setup_trend_routes()
            self.setup_scheduler()
            self.display_system_info()
            logger.info("✅ System initialized successfully with detailed trend notifications")
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise

    def setup_managers(self):
        logger.info("🔧 جاري تهيئة المديرين...")

        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.port = self.config_manager.port

        if not self.config:
            raise ValueError("❌ فشل تحميل الإعدادات")

        self.signals = self.config_manager.signals
        if not self.signals or len(self.signals) == 0:
            logger.error("❌ فشل تحميل أي إشارات")
            raise ValueError("❌ فشل تحميل الإشارات")

        total_signals = sum(len(signal_list) for signal_list in self.signals.values() if signal_list)
        if total_signals == 0:
            logger.warning("⚠️ تم تحميل الإشارات ولكنها فارغة")

        self.keywords = self.config_manager.keywords

        logger.info(f"🔍 تحقق نهائي - EXTERNAL_SERVER_ENABLED: {self.config['EXTERNAL_SERVER_ENABLED']}")
        logger.info(f"🔍 تحقق نهائي - EXTERNAL_SERVER_URL: {self.config['EXTERNAL_SERVER_URL']}")

        self.signal_processor = SignalProcessor(self.config, self.signals, self.keywords)
        self.trade_manager = TradeManager(self.config)
        self.group_manager = GroupManager(self.config, self.trade_manager)
        self.notification_manager = NotificationManager(self.config)

        self.trade_manager.set_group_manager(self.group_manager)
        self.trade_manager.set_notification_manager(self.notification_manager)

        self.cleanup_manager = CleanupManager(
            self.config,
            self.trade_manager,
            self.group_manager,
            self.notification_manager
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
        logger.info("🔧 جاري تهيئة تطبيق Flask...")

        templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")

        self.app = Flask(
            __name__,
            template_folder=templates_path
        )

        @self.app.route('/')
        def home():
            return {
                "status": "running",
                "system": "Trading System",
                "version": "11.0_detailed_trend_with_group4_group5",
                "timestamp": datetime.now().isoformat()
            }

        self.webhook_handler.register_routes(self.app)

        @self.app.route('/status')
        def status():
            return self.get_system_status()

        @self.app.route('/signal_stats/<symbol>')
        def signal_stats(symbol):
            return self.get_signal_statistics(symbol)

        @self.app.route('/health')
        def health():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }

        logger.info("✅ تم تهيئة تطبيق Flask والمسارات بنجاح")

    # 🔥 UPDATED: Redis trends reader (NO LOGIC REMOVED)
    def setup_trend_routes(self):
        """📊 دعم صفحة ويب /trends و API /api/trends لعرض الاتجاهات من Redis"""

        @self.app.route("/api/trends", methods=["GET"])
        def api_trends():
            trends = []

            redis_client = getattr(self.config_manager, "redis", None)
            if not redis_client:
                return jsonify(trends)

            try:
                symbols = redis_client.smembers("trend:symbols")

                for sym in symbols:
                    symbol = sym.decode() if isinstance(sym, (bytes, bytearray)) else str(sym)
                    value = redis_client.get(f"trend:{symbol}")
                    if not value:
                        continue

                    trend_value = value.decode() if isinstance(value, (bytes, bytearray)) else str(value)

                    trends.append({
                        "symbol": symbol,
                        "trend": trend_value,
                        "updated_at": None
                    })

            except Exception as e:
                logger.error(f"❌ Error reading trends from Redis: {e}")

            return jsonify(trends)

        @self.app.route("/trends")
        def trends_page():
            return render_template("trends.html")

        logger.info("📊 Trend web page enabled: /trends , API: /api/trends")

    def setup_scheduler(self):
        self.cleanup_manager.setup_scheduler()

    def display_system_info(self):
        self.config_manager.display_config()
        self.display_loaded_signals()
        self._verify_strategy_application()

    def _verify_strategy_application(self):
        logger.info("\n🔍 التحقق من تطبيق استراتيجيات التداول:")

        modes_to_check = [
            ('TRADING_MODE', 'النمط الأساسي'),
            ('TRADING_MODE1', 'النمط الإضافي 1'),
            ('TRADING_MODE2', 'النمط الإضافي 2')
        ]

        for mode_key, mode_name in modes_to_check:
            mode_value = self.config.get(mode_key)
            enabled = True if mode_key == 'TRADING_MODE' else self.config.get(f'{mode_key}_ENABLED', False)
            status = '✅ مفعل' if enabled else '❌ معطل'
            logger.info(f"   {mode_name}: {mode_value} ({status})")

    def display_loaded_signals(self):
        logger.info("\n📊 Loaded Signals Summary:")
        total_signals = 0
        for category, signals in self.signals.items():
            count = len(signals) if signals else 0
            logger.info(f"   📁 {category}: {count}")
            total_signals += count
        logger.info(f"📈 Total signals loaded: {total_signals}")

    def get_system_status(self):
        return {
            "status": "active",
            "version": "11.0_detailed_trend_with_group4_group5",
            "timestamp": datetime.now().isoformat(),
            "port": self.port,
            "trading_mode": self.config.get('TRADING_MODE')
        }

    def get_signal_statistics(self, symbol: str):
        try:
            stats = self.group_manager.get_group_stats(symbol)
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "statistics": stats
            }
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        logger.info(f"🚀 بدء تشغيل نظام التداول على المنفذ {self.port}")
        self.app.run(
            host='0.0.0.0',
            port=self.port,
            debug=self.config.get('DEBUG', False),
            use_reloader=False
        )
