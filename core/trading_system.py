# trading_system.py - النسخة المحدثة
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

# ✅ إضافة ProxyFix
from werkzeug.middleware.proxy_fix import ProxyFix

from config.config_manager import ConfigManager
from core.signal_processor import SignalProcessor
from core.trade_manager import TradeManager
from core.group_manager import GroupManager
from core.webhook_handler import WebhookHandler
from notifications.notification_manager import NotificationManager
from maintenance.cleanup_manager import CleanupManager
from utils.time_utils import saudi_time

logger = logging.getLogger(__name__)

class TradingSystem:
    """🎯 Trading System with Proxy Support"""

    def __init__(self):
        logger.info("🚀 Starting Trading System with TYPE SAFETY & PROXY SUPPORT...")
        try:
            self.setup_managers()
            self.setup_flask()
            self.setup_trend_routes()
            self.setup_scheduler()
            self.display_system_info()
            logger.info("✅ System initialized successfully with type safety")
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise

    def setup_managers(self):
        logger.info("🔧 جاري تهيئة المديرين مع Type Safety...")

        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.port = self.config_manager.port

        if not self.config:
            raise ValueError("❌ فشل تحميل الإعدادات")

        self.signals = self.config_manager.signals
        if not self.signals:
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

        # ✅ التحقق من Type Safety
        self._validate_type_safety()
        
        logger.info("✅ تم تهيئة جميع المديرين مع Type Safety")

    def _validate_type_safety(self):
        """التحقق من صحة تحويلات الأنواع"""
        logger.info("🔍 التحقق من Type Safety...")
        
        test_values = {
            'DEBUG': self.config_manager.get_bool('DEBUG'),
            'PORT': self.config_manager.get_int('PORT'),
            'MAX_OPEN_TRADES': self.config_manager.get_int('MAX_OPEN_TRADES'),
            'GROUP1_ENABLED': self.config_manager.get_bool('GROUP1_ENABLED'),
            'DUPLICATE_SIGNAL_BLOCK_TIME': self.config_manager.get_int('DUPLICATE_SIGNAL_BLOCK_TIME'),
            'CLEANUP_FACTOR': self.config_manager.get_float('CLEANUP_FACTOR'),
        }
        
        all_valid = True
        for key, value in test_values.items():
            if key.endswith('ENABLED'):
                if not isinstance(value, bool):
                    logger.error(f"❌ {key} ليس bool: {type(value).__name__}")
                    all_valid = False
            elif 'FACTOR' in key or 'THRESHOLD' in key:
                if not isinstance(value, (int, float)):
                    logger.error(f"❌ {key} ليس عدد: {type(value).__name__}")
                    all_valid = False
            else:
                if not isinstance(value, int):
                    logger.error(f"❌ {key} ليس int: {type(value).__name__}")
                    all_valid = False
        
        if all_valid:
            logger.info("✅ جميع التحويلات صحيحة")
        else:
            logger.warning("⚠️ هناك مشاكل في تحويل الأنواع")

    def setup_flask(self):
        logger.info("🔧 جاري تهيئة Flask مع ProxyFix...")

        templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.app = Flask(__name__, template_folder=templates_path)
        
        # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
        # ✅ إضافة ProxyFix لدعم Cloud Run/Render
        # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
        self.app.wsgi_app = ProxyFix(
            self.app.wsgi_app,
            x_for=1,      # عدد Proxies الموثوقة
            x_proto=1,
            x_host=1,
            x_port=1,
            x_prefix=1
        )
        
        logger.info("✅ ProxyFix مفعل لدعم البيئات السحابية")

        @self.app.route("/")
        def home():
            return {
                "status": "running",
                "system": "Trading System with Type Safety",
                "proxy_support": True,
                "timestamp": datetime.now().isoformat()
            }

        self.webhook_handler.register_routes(self.app)

        @self.app.route("/status")
        def status():
            return self.get_system_status()

        @self.app.route("/health")
        def health():
            return {"status": "healthy", "proxy_support": True}

    # ... (بقية الكود كما هو مع تعديلات طفيفة)
    
    def run(self):
        logger.info(f"🚀 تشغيل النظام على المنفذ {self.port}")
        logger.info(f"🔧 Type Safety: ✅, ProxyFix: ✅")
        
        # ✅ التحقق النهائي
        self._final_validation()
        
        self.app.run(
            host="0.0.0.0",
            port=self.port,
            debug=self.config_manager.get_bool('DEBUG'),
            use_reloader=False
        )
    
    def _final_validation(self):
        """التحقق النهائي قبل التشغيل"""
        logger.info("🔍 التحقق النهائي قبل التشغيل...")
        
        # التحقق من Redis
        if hasattr(self.trade_manager, 'redis_enabled'):
            logger.info(f"🔧 Redis: {'✅ مفعل' if self.trade_manager.redis_enabled else '❌ معطل'}")
        
        # التحقق من GroupMapper
        if hasattr(self.group_manager, 'group_mapper'):
            logger.info("🔧 GroupMapper: ✅ مفعل")
        
        # التحقق من DebugGuard
        if hasattr(self.webhook_handler, 'debug_guard'):
            debug_status = self.webhook_handler.debug_guard.get_debug_status()
            logger.info(f"🔧 DebugGuard: {'✅ مفعل' if debug_status.get('debug_enabled') else '❌ معطل'}")
        
        # التحقق من التحويلات
        critical_settings = [
            ('DUPLICATE_SIGNAL_BLOCK_TIME', 'int'),
            ('CLEANUP_FACTOR', 'float'),
            ('TELEGRAM_ENABLED', 'bool'),
            ('MAX_OPEN_TRADES', 'int'),
        ]
        
        for key, expected_type in critical_settings:
            if expected_type == 'int':
                value = self.config_manager.get_int(key)
            elif expected_type == 'float':
                value = self.config_manager.get_float(key)
            elif expected_type == 'bool':
                value = self.config_manager.get_bool(key)
            else:
                value = self.config_manager.get_str(key)
            
            actual_type = type(value).__name__
            logger.info(f"📋 {key}: {actual_type} = {value}")
