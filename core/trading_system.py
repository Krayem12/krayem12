"""
🎯 نظام التداول الآلي مع إشعارات مفصلة لتغيرات الاتجاه
الإصدار المصحح: إصلاح الثغرات الأمنية وتحسين الأداء والموثوقية
"""

import schedule
import threading
import time
import logging
import os
import json
import pytz
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from config.config_manager import ConfigManager
from core.signal_processor import SignalProcessor
from core.trade_manager import TradeManager
from core.group_manager import GroupManager
from core.webhook_handler import WebhookHandler
from notifications.notification_manager import NotificationManager
from maintenance.cleanup_manager import CleanupManager

logger = logging.getLogger(__name__)

class TradingSystem:
    """🎯 نظام التداول مع إشعارات مفصلة لتغيرات الاتجاه"""
    
    # 🔒 ثوابت الأمان
    MAX_REQUEST_SIZE = 16 * 1024 * 1024  # 16MB
    RATE_LIMIT_WINDOW = 60  # ثانية
    RATE_LIMIT_MAX_REQUESTS = 100  # طلب/دقيقة
    TRENDS_CACHE_DURATION = 30  # ثانية

    def __init__(self):
        """تهيئة النظام مع التحقق من الأمان"""
        logger.info("🚀 بدء نظام التداول مع التنفيذ الكامل + GROUP3 + GROUP4 + GROUP5...")
        
        try:
            self._validate_environment()
            self.setup_managers()
            self.setup_flask()
            self.setup_trend_routes()
            self.setup_scheduler()
            self.setup_rate_limiting()
            self.display_system_info()
            logger.info("✅ تم تهيئة النظام بنجاح")
            
        except Exception as e:
            logger.error(f"❌ فشل تهيئة النظام: {e}", exc_info=True)
            raise

    def _validate_environment(self):
        """🔒 التحقق من متغيرات البيئة المطلوبة"""
        required_vars = [
            'SECRET_KEY',
            'FLASK_ENV',
            'ALLOWED_ORIGINS'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.error(f"❌ متغيرات بيئة مفقودة: {missing}")
            raise EnvironmentError(
                f"متغيرات بيئة مفقودة: {missing}. "
                "يرجى إعداد ملف .env"
            )

    def setup_managers(self):
        """🔧 تهيئة جميع المديرين"""
        logger.info("🔧 جاري تهيئة المديرين...")

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

        logger.info("✅ تم تهيئة جميع المديرين بنجاح")

    def setup_flask(self):
        """🔧 تهيئة Flask مع إعدادات أمنية"""
        logger.info("🔧 جاري تهيئة Flask...")

        templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
        static_path = os.path.join(os.path.dirname(__file__), "..", "static")
        
        # 🔒 إنشاء تطبيق Flask مع مسارات آمنة
        self.app = Flask(
            __name__, 
            template_folder=templates_path,
            static_folder=static_path
        )
        
        # 🔒 إعدادات أمنية أساسية
        self.app.config.update({
            'SECRET_KEY': os.getenv('SECRET_KEY', 'fallback-change-in-production'),
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=1),
            'MAX_CONTENT_LENGTH': self.MAX_REQUEST_SIZE,
        })
        
        # 🔒 إعداد CORS آمن
        allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
        if allowed_origins == ['']:
            allowed_origins = []
        
        CORS(self.app, 
             origins=allowed_origins,
             supports_credentials=True,
             methods=['GET', 'POST', 'PUT', 'DELETE'],
             allow_headers=['Content-Type', 'Authorization']
        )
        
        # 🔒 إصلاح للخوادم الوسيطة (Reverse Proxy)
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        
        # 🔒 إعداد المسارات الأساسية
        @self.app.route("/")
        def home():
            """🔒 الصفحة الرئيسية الآمنة"""
            return {
                "status": "running",
                "system": "Trading System",
                "version": "1.0.0",
                "timestamp": datetime.now(pytz.timezone("Asia/Riyadh")).isoformat(),
                "environment": os.getenv('FLASK_ENV', 'development')
            }

        self.webhook_handler.register_routes(self.app)

        @self.app.route("/status")
        def status():
            """🔒 حالة النظام"""
            return self.get_system_status()

        @self.app.route("/health")
        def health():
            """🔒 فحص الصحة"""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # 🔒 إضافة معالج أخطاء مركزي
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({"error": "المسار غير موجود"}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            logger.error(f"❌ خطأ داخلي في الخادم: {error}")
            return jsonify({"error": "خطأ داخلي في الخادم"}), 500

    def setup_rate_limiting(self):
        """🔧 إعداد الحد من الطلبات للوقاية من الهجمات"""
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        
        self.limiter = Limiter(
            get_remote_address,
            app=self.app,
            default_limits=[f"{self.RATE_LIMIT_MAX_REQUESTS} per minute"],
            storage_uri="memory://",
            strategy="fixed-window"
        )
        
        # 🔒 تطبيق الحد على المسارات الحساسة
        self.limiter.limit(f"{self.RATE_LIMIT_MAX_REQUESTS} per minute")(
            self.app.route("/api/trends")
        )
        
        logger.info("✅ تم إعداد نظام الحد من الطلبات")

    # ===============================
    # 📊 Trends API + Page
    # ===============================
    def setup_trend_routes(self):
        """🔧 إعداد مسارات الاتجاهات مع التخزين المؤقت"""
        
        # 🔒 قاموس للتخزين المؤقت
        self._trends_cache = {
            "data": [],
            "timestamp": None
        }

        @self.app.route("/api/trends", methods=["GET"])
        def api_trends():
            """🔒 الحصول على بيانات الاتجاهات مع التخزين المؤقت"""
            try:
                # 🔒 التحقق من التخزين المؤقت
                current_time = datetime.now()
                if (self._trends_cache["timestamp"] and 
                    (current_time - self._trends_cache["timestamp"]).seconds < self.TRENDS_CACHE_DURATION):
                    logger.debug("📊 إرجاع البيانات من التخزين المؤقت")
                    return jsonify(self._trends_cache["data"])
                
                trends = self._fetch_trends_from_redis()
                
                # 🔒 تحديث التخزين المؤقت
                self._trends_cache = {
                    "data": trends,
                    "timestamp": current_time
                }
                
                return jsonify(trends)
                
            except Exception as e:
                logger.error(f"❌ خطأ في api_trends: {e}", exc_info=True)
                return jsonify({"error": "خطأ في الخادم"}), 500

        @self.app.route("/trends")
        def trends_page():
            """🔒 صفحة عرض الاتجاهات"""
            try:
                return render_template("trends.html")
            except Exception as e:
                logger.error(f"❌ خطأ في تحميل صفحة الاتجاهات: {e}")
                return "خطأ في تحميل الصفحة", 500
    
    def _fetch_trends_from_redis(self) -> List[Dict[str, Any]]:
        """🔒 جلب بيانات الاتجاهات من Redis بأمان"""
        trends = []
        
        logger.info("📊 جلب بيانات الاتجاهات من Redis...")
        
        redis_client = None
        try:
            # 🔒 الحصول على عميل Redis بأمان
            if hasattr(self.trade_manager, "redis") and self.trade_manager.redis:
                # محاولة الوصول للعميل بأكثر من طريقة
                if callable(getattr(self.trade_manager.redis, "get_client", None)):
                    redis_client = self.trade_manager.redis.get_client()
                elif hasattr(self.trade_manager.redis, "client"):
                    redis_client = self.trade_manager.redis.client
                elif hasattr(self.trade_manager.redis, "_client"):
                    redis_client = self.trade_manager.redis._client
                else:
                    logger.error("❌ لم يتم العثور على عميل Redis في TradeManager")
            else:
                logger.warning("⚠️ Redis غير متوفر في TradeManager")
                
            if not redis_client:
                logger.info("ℹ️ عميل Redis غير متوفر، إرجاع بيانات محلية")
                return self._get_local_trends()
                
            # 🔒 اختبار اتصال Redis
            try:
                redis_client.ping()
                logger.info("✅ تم الاتصال بـ Redis بنجاح")
            except Exception as e:
                logger.error(f"❌ فشل الاتصال بـ Redis: {e}")
                return self._get_local_trends()

        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على عميل Redis: {e}")
            return self._get_local_trends()

        riyadh_tz = pytz.timezone("Asia/Riyadh")

        try:
            # 🔒 جلب الرموز بأمان
            symbols = set()
            try:
                symbols_set = redis_client.smembers("trend:symbols")
                if symbols_set:
                    symbols = {str(sym) for sym in symbols_set}
            except Exception as e:
                logger.warning(f"⚠️ خطأ في جلب الرموز من Redis: {e}")
            
            logger.info(f"📈 عدد الرموز في Redis: {len(symbols)}")
            
            if not symbols:
                logger.info("ℹ️ لا توجد رموز في Redis")
                return self._get_local_trends()

            # 🔒 جلب بيانات كل رمز
            for symbol in sorted(symbols):
                try:
                    # 🔒 جلب الاتجاه
                    trend_val = redis_client.get(f"trend:{symbol}")
                    if not trend_val:
                        logger.debug(f"⚠️ لا توجد بيانات اتجاه للرمز: {symbol}")
                        continue
                    
                    # 🔒 جلب وقت التحديث
                    updated_at_sa = "—"
                    updated_raw = redis_client.get(f"trend:{symbol}:updated_at")
                    
                    if updated_raw:
                        try:
                            dt = datetime.fromisoformat(str(updated_raw))
                            if dt.tzinfo is None:
                                dt = pytz.utc.localize(dt)
                            updated_at_sa = dt.astimezone(riyadh_tz).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception as e:
                            logger.debug(f"⚠️ خطأ في تحويل الوقت للرمز {symbol}: {e}")
                    
                    # 🔒 إضافة للنتائج
                    trends.append({
                        "symbol": symbol,
                        "trend": str(trend_val).upper(),
                        "updated_at": updated_at_sa
                    })
                    
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في معالجة الرمز {symbol}: {e}")
                    continue

            logger.info(f"✅ تم تحميل {len(trends)} اتجاه بنجاح")
            
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة بيانات الاتجاه من Redis: {e}")
            trends = self._get_local_trends()

        return trends

    def _get_local_trends(self) -> List[Dict[str, Any]]:
        """🔒 الحصول على الاتجاهات من TradeManager"""
        trends = []
        try:
            riyadh_tz = pytz.timezone("Asia/Riyadh")
            current_time = datetime.now(riyadh_tz).strftime("%Y-%m-%d %H:%M:%S")
            
            # 🔒 التحقق من وجود current_trend
            if hasattr(self.trade_manager, "current_trend"):
                trends_dict = self.trade_manager.current_trend
                if isinstance(trends_dict, dict):
                    for symbol, trend in trends_dict.items():
                        if trend and str(trend).upper() != "UNKNOWN":
                            trends.append({
                                "symbol": str(symbol),
                                "trend": str(trend).upper(),
                                "updated_at": current_time
                            })
                    
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الاتجاهات المحلية: {e}")
            
        return trends

    def setup_scheduler(self):
        """🔧 إعداد المجدول"""
        self.cleanup_manager.setup_scheduler()

    def display_system_info(self):
        """🔧 عرض معلومات النظام"""
        self.config_manager.display_config()
        
        # 🔒 تسجيل معلومات أمنية مهمة
        logger.info(f"🔒 وضع التشغيل: {os.getenv('FLASK_ENV', 'development')}")
        logger.info(f"🔒 حجم الطلب الأقصى: {self.MAX_REQUEST_SIZE / (1024*1024)} MB")
        logger.info(f"🔒 حد الطلبات: {self.RATE_LIMIT_MAX_REQUESTS} طلب/دقيقة")

    def get_system_status(self):
        """🔒 الحصول على حالة النظام"""
        return {
            "status": "active",
            "port": self.port,
            "environment": os.getenv('FLASK_ENV', 'development'),
            "timestamp": datetime.now(pytz.timezone("Asia/Riyadh")).isoformat(),
            "rate_limit": f"{self.RATE_LIMIT_MAX_REQUESTS} requests/minute",
            "cache_enabled": True,
            "cache_duration": f"{self.TRENDS_CACHE_DURATION} seconds"
        }

    def run(self):
        """🔒 تشغيل النظام"""
        is_production = os.getenv('FLASK_ENV') == 'production'
        debug_mode = self.config.get("DEBUG", False) and not is_production
        
        if is_production and self.config.get("DEBUG", False):
            logger.warning("⚠️ ⚠️ ⚠️ تحذير: وضع التصحيح مفعل في بيئة الإنتاج!")
            debug_mode = False
        
        logger.info(f"🚀 تشغيل النظام على المنفذ {self.port}")
        logger.info(f"🎯 وضع التشغيل: {'إنتاج' if is_production else 'تطوير'}")
        logger.info(f"🔧 وضع التصحيح: {'مفعل' if debug_mode else 'معطل'}")
        
        self.app.run(
            host="0.0.0.0",
            port=self.port,
            debug=debug_mode,
            use_reloader=debug_mode
        )
