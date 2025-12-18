# trading_system.py
import schedule
import threading
import time
import logging
import os
import json
import pytz

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
            raise ValueError("❌ فشل تحميل الإشارات")

        self.keywords = self.config_manager.keywords

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
        self.app = Flask(__name__, template_folder=templates_path)

        @self.app.route("/")
        def home():
            return {
                "status": "running",
                "system": "Trading System",
                "version": "11.1_saudi_time",
                "timestamp": datetime.now().isoformat()
            }

        self.webhook_handler.register_routes(self.app)

        @self.app.route("/status")
        def status():
            return self.get_system_status()

        @self.app.route("/health")
        def health():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }

        logger.info("✅ تم تهيئة Flask بنجاح")

    # ============================================================
    # 📊 Trends Web + API (Redis → Saudi Time)
    # ============================================================
    def setup_trend_routes(self):

        @self.app.route("/api/trends", methods=["GET"])
        def api_trends():
            trends = []

            redis_client = getattr(self.config_manager, "redis", None)
            if not redis_client:
                return jsonify(trends)

            riyadh_tz = pytz.timezone("Asia/Riyadh")

            try:
                symbols = redis_client.smembers("trend:symbols")

                for sym in symbols:
                    symbol = sym.decode() if isinstance(sym, (bytes, bytearray)) else str(sym)

                    trend_val = redis_client.get(f"trend:{symbol}")
                    updated_raw = redis_client.get(f"trend:{symbol}:updated_at")

                    if not trend_val:
                        continue

                    updated_at_sa = "—"
                    if updated_raw:
                        try:
                            dt = datetime.fromisoformat(
                                updated_raw.decode() if isinstance(updated_raw, (bytes, bytearray)) else str(updated_raw)
                            )
                            if dt.tzinfo is None:
                                dt = pytz.utc.localize(dt)

                            dt_sa = dt.astimezone(riyadh_tz)
                            updated_at_sa = dt_sa.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            updated_at_sa = "—"

                    trends.append({
                        "symbol": symbol,
                        "trend": trend_val.decode() if isinstance(trend_val, (bytes, bytearray)) else str(trend_val),
                        "updated_at": updated_at_sa
                    })

            except Exception as e:
                logger.error(f"❌ Redis trend read error: {e}")

            return jsonify(trends)

        @self.app.route("/trends")
        def trends_page():
            return render_template("trends.html")

        logger.info("📊 Trends page enabled with Saudi Time")

    # ============================================================

    def setup_scheduler(self):
        self.cleanup_manager.setup_scheduler()

    def display_system_info(self):
        self.config_manager.display_config()

    def get_system_status(self):
        return {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "port": self.port,
            "trading_mode": self.config.get("TRADING_MODE")
        }

    def run(self):
        logger.info(f"🚀 تشغيل النظام على المنفذ {self.port}")

        self.app.run(
            host="0.0.0.0",
            port=self.port,
            debug=self.config.get("DEBUG", False),
            use_reloader=False
        )
