# trading_system.py - النسخة المحدثة
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
from utils.time_utils import saudi_time  # ✅ استيراد موحد

# ✅ استيراد المكونات الجديدة
try:
    from core.group_mapper import GroupMapper
    from core.debug_guard import DebugGuard
    GROUP_MAPPER_AVAILABLE = True
    DEBUG_GUARD_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ المكونات الجديدة غير متوفرة: {e}")
    GROUP_MAPPER_AVAILABLE = False
    DEBUG_GUARD_AVAILABLE = False

logger = logging.getLogger(__name__)

class TradingSystem:
    """🎯 Trading System with GROUP MAPPER & DEBUG GUARD SUPPORT"""

    def __init__(self):
        logger.info("🚀 Starting Trading System with GROUP MAPPER + DEBUG GUARD...")
        try:
            self.setup_managers()
            self.setup_flask()
            self.setup_trend_routes()
            self.setup_scheduler()
            self.display_system_info()
            logger.info("✅ System initialized successfully with new components")
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise

    def setup_managers(self):
        logger.info("🔧 جاري تهيئة المديرين مع المكونات الجديدة...")

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
        
        # ✅ إنشاء TradeManager مع دعم GroupMapper
        self.trade_manager = TradeManager(self.config)
        
        # ✅ إنشاء GroupManager مع GroupMapper
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

        # ✅ إنشاء WebhookHandler مع DebugGuard
        self.webhook_handler = WebhookHandler(
            self.config,
            self.signal_processor,
            self.group_manager,
            self.trade_manager,
            self.notification_manager,
            self.cleanup_manager
        )

        # ✅ التحقق من المكونات الجديدة
        self._check_new_components()
        
        logger.info("✅ تم تهيئة جميع المديرين بنجاح مع المكونات الجديدة")

    def _check_new_components(self):
        """التحقق من توفر المكونات الجديدة"""
        try:
            # التحقق من GroupMapper
            if hasattr(self.group_manager, 'group_mapper'):
                logger.info("✅ GroupMapper مفعل في GroupManager")
            else:
                logger.warning("⚠️ GroupMapper غير مفعل في GroupManager")
            
            # التحقق من DebugGuard
            if hasattr(self.webhook_handler, 'debug_guard'):
                debug_status = self.webhook_handler.debug_guard.get_debug_status()
                logger.info(f"✅ DebugGuard مفعل - حالة: {debug_status.get('debug_enabled', False)}")
            else:
                logger.warning("⚠️ DebugGuard غير مفعل في WebhookHandler")
                
        except Exception as e:
            logger.warning(f"⚠️ خطأ في التحقق من المكونات الجديدة: {e}")

    def setup_flask(self):
        logger.info("🔧 جاري تهيئة Flask مع المكونات الجديدة...")

        templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.app = Flask(__name__, template_folder=templates_path)

        @self.app.route("/")
        def home():
            return {
                "status": "running",
                "system": "Trading System with GroupMapper & DebugGuard",
                "version": "1.2.0",
                "components": {
                    "group_mapper": GROUP_MAPPER_AVAILABLE,
                    "debug_guard": DEBUG_GUARD_AVAILABLE
                },
                "timestamp": datetime.now().isoformat()
            }

        self.webhook_handler.register_routes(self.app)

        @self.app.route("/status")
        def status():
            return self.get_system_status()

        @self.app.route("/health")
        def health():
            return {"status": "healthy"}

    # ===============================
    # 📊 Trends API + Page
    # ===============================
    def setup_trend_routes(self):

        @self.app.route("/api/trends", methods=["GET"])
        def api_trends():
            trends = []
            
            logger.info("📊 طلب بيانات الاتجاهات من Redis...")
            
            # 🔧 الإصلاح: استخدام redis من trade_manager بشكل مباشر
            redis_client = None
            try:
                # التحقق من وجود redis في trade_manager
                if hasattr(self.trade_manager, "redis") and self.trade_manager.redis:
                    # 🔧 الإصلاح: استدعاء دالة العميل مباشرة
                    if hasattr(self.trade_manager.redis, "get_client"):
                        redis_client = self.trade_manager.redis.get_client()
                    elif hasattr(self.trade_manager.redis, "client"):
                        redis_client = self.trade_manager.redis.client
                    else:
                        logger.error("❌ لم يتم العثور على عميل Redis في TradeManager")
                else:
                    logger.warning("⚠️ Redis غير متوفر في TradeManager")
                    
                if not redis_client:
                    logger.warning("⚠️ عميل Redis غير متوفر، إرجاع قائمة فارغة")
                    return jsonify(trends)
                    
                # اختبار الاتصال بـ Redis
                try:
                    redis_client.ping()
                    logger.info("✅ تم الاتصال بـ Redis بنجاح")
                except Exception as e:
                    logger.error(f"❌ فشل الاتصال بـ Redis: {e}")
                    return jsonify(trends)

            except Exception as e:
                logger.error(f"❌ خطأ في الحصول على عميل Redis: {e}")
                return jsonify(trends)

            riyadh_tz = pytz.timezone("Asia/Riyadh")

            try:
                # 🔧 الإصلاح: استخدام decode_responses=True في Redis
                symbols = redis_client.smembers("trend:symbols") or set()
                logger.info(f"📈 عدد الرموز في Redis: {len(symbols)}")
                
                if not symbols:
                    logger.info("ℹ️ لا توجد رموز في قاعدة بيانات Redis")
                    return jsonify(trends)

                for sym in symbols:
                    symbol = str(sym)
                    logger.debug(f"🔍 جلب بيانات الرمز: {symbol}")
                    
                    trend_val = redis_client.get(f"trend:{symbol}")
                    
                    if not trend_val:
                        logger.debug(f"⚠️ لا توجد بيانات اتجاه للرمز: {symbol}")
                        continue

                    updated_raw = redis_client.get(f"trend:{symbol}:updated_at")
                    updated_at_sa = "—"

                    if updated_raw:
                        try:
                            dt = datetime.fromisoformat(str(updated_raw))
                            if dt.tzinfo is None:
                                dt = pytz.utc.localize(dt)
                            updated_at_sa = dt.astimezone(riyadh_tz).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception as e:
                            logger.debug(f"⚠️ خطأ في تحويل الوقت للرمز {symbol}: {e}")
                            updated_at_sa = "—"

                    trends.append({
                        "symbol": symbol,
                        "trend": str(trend_val),
                        "updated_at": updated_at_sa,
                        "group_mapper": GROUP_MAPPER_AVAILABLE
                    })

                trends.sort(key=lambda x: x["symbol"])
                logger.info(f"✅ تم تحميل {len(trends)} اتجاه بنجاح")
                
            except Exception as e:
                logger.error(f"❌ خطأ في قراءة بيانات الاتجاه من Redis: {e}")
                # 🔧 الإصلاح: إرجاع البيانات المحلية كبديل
                try:
                    trends = self._get_local_trends()
                    logger.info(f"✅ تم تحميل {len(trends)} اتجاه من البيانات المحلية")
                except Exception as local_e:
                    logger.error(f"❌ فشل تحميل البيانات المحلية: {local_e}")

            return jsonify(trends)

        @self.app.route("/trends")
        def trends_page():
            return render_template("trends.html")
    
    def _get_local_trends(self):
        """🔧 الإصلاح: الحصول على الاتجاهات من TradeManager بشكل آمن"""
        trends = []
        try:
            # ✅ التحقق من وجود trade_manager و current_trend
            if not hasattr(self, 'trade_manager') or self.trade_manager is None:
                logger.error("❌ trade_manager غير متوفر")
                return trends
                
            if not hasattr(self.trade_manager, 'current_trend'):
                logger.error("❌ current_trend غير متوفر في trade_manager")
                return trends
                
            current_trends = self.trade_manager.current_trend
            
            if not isinstance(current_trends, dict):
                logger.error("❌ current_trend ليس قاموسًا")
                return trends
                
            for symbol, trend in current_trends.items():
                try:
                    if trend and isinstance(trend, str) and trend.upper() != "UNKNOWN":
                        trends.append({
                            "symbol": str(symbol) if symbol else "UNKNOWN",
                            "trend": trend.upper(),
                            "updated_at": saudi_time.format_time(),
                            "group_mapper": hasattr(self.trade_manager, 'group_mapper') and self.trade_manager.group_mapper is not None
                        })
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في معالجة اتجاه الرمز {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الاتجاهات المحلية: {e}")
            
        return trends

    def setup_scheduler(self):
        self.cleanup_manager.setup_scheduler()

    def display_system_info(self):
        self.config_manager.display_config()
        
        # ✅ عرض معلومات المكونات الجديدة
        logger.info("🔍 معلومات المكونات الجديدة:")
        logger.info(f"   📦 GroupMapper: {'✅ متوفر' if GROUP_MAPPER_AVAILABLE else '❌ غير متوفر'}")
        logger.info(f"   🔒 DebugGuard: {'✅ متوفر' if DEBUG_GUARD_AVAILABLE else '❌ غير متوفر'}")
        
        if hasattr(self.group_manager, 'group_mapper'):
            try:
                stats = self.group_manager.group_mapper.get_group_statistics(self.config)
                logger.info(f"   📊 المجموعات: {stats['enabled_groups']}/{stats['total_groups']} مفعلة")
            except:
                logger.info("   📊 المجموعات: معلومات غير متوفرة")

    def get_system_status(self):
        return {
            "status": "active",
            "port": self.port,
            "version": "1.2.0_with_group_mapper",
            "components": {
                "group_mapper": GROUP_MAPPER_AVAILABLE,
                "debug_guard": DEBUG_GUARD_AVAILABLE,
                "trade_manager": hasattr(self.trade_manager, 'group_mapper') and self.trade_manager.group_mapper is not None,
                "group_manager": hasattr(self.group_manager, 'group_mapper') and self.group_manager.group_mapper is not None,
                "webhook_handler": hasattr(self.webhook_handler, 'debug_guard') and self.webhook_handler.debug_guard is not None
            },
            "timestamp": datetime.now().isoformat()
        }

    def run(self):
        logger.info(f"🚀 تشغيل النظام على المنفذ {self.port}")
        logger.info(f"🔧 المكونات الجديدة: GroupMapper={'✅' if GROUP_MAPPER_AVAILABLE else '❌'}, DebugGuard={'✅' if DEBUG_GUARD_AVAILABLE else '❌'}")
        
        self.app.run(
            host="0.0.0.0",
            port=self.port,
            debug=self.config.get("DEBUG", False),
            use_reloader=False
        )
