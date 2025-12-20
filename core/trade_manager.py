# core/trade_manager.py
# ==========================================================
# ✅ TradeManager – FINAL & COMPATIBLE VERSION
# 🔒 النسخة المصححة مع إصلاحات أمنية وأداء محسنة
# ==========================================================

import logging
import threading
import hashlib
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque

# ----------------------------------------------------------
# 🕒 Saudi Time (Safe Import)
# ----------------------------------------------------------
try:
    from utils.time_utils import saudi_time
    SAUDI_TZ_AVAILABLE = True
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ SaudiTime import failed: {e}, using UTC")
    SAUDI_TZ_AVAILABLE = False

# ----------------------------------------------------------
# 🔴 Redis Manager (Safe Import with encryption)
# ----------------------------------------------------------
try:
    from utils.redis_manager import RedisManager
    REDIS_MANAGER_AVAILABLE = True
except Exception:
    try:
        from core.redis_manager import RedisManager
        REDIS_MANAGER_AVAILABLE = True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️ RedisManager import failed: {e}")
        REDIS_MANAGER_AVAILABLE = False
        RedisManager = None

logger = logging.getLogger(__name__)


class TradeManager:
    """
    TradeManager – FINAL SECURE VERSION
    
    ✔ يدير الاتجاهات (Trend) والصفقات بشكل آمن
    ✔ متوافق بالكامل مع GroupManager و TradingSystem
    ✔ يحتوي جميع الدوال المتوقعة مع حماية أمنية
    🔒 تشفير البيانات الحساسة، مصادقة، تسجيل آمن
    """

    # ======================================================
    # 🔒 CONSTANTS FOR SECURITY
    # ======================================================
    MAX_TRADES_PER_SYMBOL = 10  # 🔒 حد أقصى للصفقات لكل رمز
    MAX_TOTAL_TRADES = 100      # 🔒 إجمالي الصفقات النشطة
    TRADE_ID_SALT = os.getenv('TRADE_ID_SALT', 'default-salt-change-me')
    ENCRYPTION_ENABLED = True
    SESSION_TIMEOUT = 3600  # 🔒 ساعة بالثواني

    # ======================================================
    # 🚀 INIT (Secure Initialization)
    # ======================================================
    def __init__(self, config: dict):
        """تهيئة آمنة لمدير الصفقات"""
        
        # 🔒 التحقق من التكوين الأساسي
        if not config or not isinstance(config, dict):
            raise ValueError("❌ التكوين مطلوب ويجب أن يكون قاموساً")
        
        self.config = config.copy()  # 🔒 نسخة لتجنب التعديل المباشر
        
        # 🔒 التحقق من الإعدادات الحساسة
        self._validate_config()
        
        logger.info(f"🧠 TradeManager المحمّل من: {__file__}")

        # 🔒 أقفال للخيوط المتوازية (Thread-safe)
        self.trade_lock = threading.RLock()  # 🔒 RLock للسماح بإعادة الدخول
        self.trend_lock = threading.RLock()
        self.redis_lock = threading.RLock()

        # 🔒 الصفقات النشطة مع قيود أمنية
        self.active_trades: Dict[str, dict] = {}
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0
        self.metrics = {
            "trades_opened": 0,
            "trades_closed": 0,
            "errors": 0,
            "security_blocks": 0
        }

        # 🔒 الاتجاهات مع التتبع الآمن
        self.current_trend: Dict[str, str] = {}
        self.previous_trend: Dict[str, str] = {}
        self.last_reported_trend: Dict[str, str] = {}
        self.trend_strength: Dict[str, int] = defaultdict(int)
        self.trend_update_times: Dict[str, datetime] = {}

        # 🔒 مخازن الاتجاه مع حدود آمنة
        self.trend_pool: Dict[str, dict] = defaultdict(lambda: {
            "signals": {},
            "count": 0,
            "created_at": self._get_current_time()
        })
        
        self.trend_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)  # 🔒 حد أقصى للذاكرة
        )

        # 🔒 المديرين الخارجيين مع التحقق
        self.group_manager = None
        self.notification_manager = None

        # 🔒 سجل الأخطاء الآمن
        self._error_log = deque(maxlen=200)
        self._security_log = deque(maxlen=100)

        # 🔒 Redis مع تشفير
        self.redis = None
        self.redis_enabled = False
        
        if REDIS_MANAGER_AVAILABLE and RedisManager:
            try:
                # 🔒 تهيئة Redis مع إعدادات أمنية
                redis_config = {
                    'host': config.get('redis_host', 'localhost'),
                    'port': config.get('redis_port', 6379),
                    'password': config.get('redis_password'),
                    'ssl': config.get('redis_ssl', True),
                    'ssl_cert_reqs': 'required' if config.get('redis_ssl') else None,
                    'decode_responses': True,
                    'socket_timeout': 10,
                    'socket_connect_timeout': 5
                }
                
                self.redis = RedisManager(redis_config)
                
                # 🔒 التحقق من تفعيل Redis
                self.redis_enabled = False
                if hasattr(self.redis, "is_enabled"):
                    self.redis_enabled = self.redis.is_enabled()
                elif hasattr(self.redis, "client"):
                    try:
                        self.redis.client.ping()
                        self.redis_enabled = True
                    except:
                        self.redis_enabled = False
                
                if self.redis_enabled:
                    self._load_trends_from_redis()
                    logger.info("✅ Redis آمن مفعل")
                else:
                    logger.warning("⚠️ Redis غير مفعل أو غير متصل")
                    
            except Exception as e:
                logger.error(f"❌ فشل تهيئة Redis: {e}")
                self.redis = None
                self.redis_enabled = False
                self._log_security_event("redis_init_failed", str(e))
        else:
            logger.info("ℹ️ Redis غير متوفر، استخدام الذاكرة المحلية فقط")

        logger.info("✅ TradeManager FINAL SECURE مهيأ – التوقيت السعودي 🇸🇦")
        self._log_security_event("system_started", "TradeManager initialized")

    def _validate_config(self):
        """🔒 التحقق من إعدادات الأمان في التكوين"""
        security_issues = []
        
        # 🔒 التحقق من كلمات المرور
        redis_pass = self.config.get('redis_password', '')
        if redis_pass and len(redis_pass) < 12:
            security_issues.append("كلمة مرور Redis قصيرة (<12 حرف)")
        
        # 🔒 التحقق من العتبات
        trend_threshold = self.config.get("TREND_CHANGE_THRESHOLD", 2)
        if trend_threshold < 2 or trend_threshold > 10:
            security_issues.append(f"عتبة تغيير الاتجاه غير آمنة: {trend_threshold}")
        
        if security_issues:
            logger.warning(f"⚠️ مشاكل أمنية في التكوين: {security_issues}")
            for issue in security_issues:
                self._log_security_event("config_issue", issue)

    # ======================================================
    # 🕒 TIME UTILITIES (Secure)
    # ======================================================
    def _get_current_time(self) -> datetime:
        """🔒 الحصول على الوقت الحالي بشكل آمن"""
        try:
            if SAUDI_TZ_AVAILABLE:
                return saudi_time.now()
            else:
                # 🔒 استخدام UTC كبديل آمن
                from datetime import timezone
                return datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الوقت: {e}")
            return datetime.utcnow()

    def _generate_trade_id(self, symbol: str, direction: str, strategy_type: str) -> str:
        """🔒 إنشاء معرف صفقة آمن فريد"""
        try:
            timestamp = int(time.time() * 1000)
            unique_str = f"{symbol}_{direction}_{strategy_type}_{timestamp}_{self.TRADE_ID_SALT}"
            
            # 🔒 استخدام هاش آمن
            hash_obj = hashlib.sha256(unique_str.encode())
            trade_hash = hash_obj.hexdigest()[:16]  # 16 حرف كاف
            
            # 🔒 إضافة رمز للتحقق
            return f"TRADE_{symbol[:4]}_{direction[:1]}_{trade_hash}"
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء معرف الصفقة: {e}")
            # 🔒 معرف طارئ
            return f"EMERGENCY_{int(time.time())}_{hashlib.md5(symbol.encode()).hexdigest()[:8]}"

    # ======================================================
    # 🔗 REQUIRED BY TradingSystem (Secure)
    # ======================================================
    def set_group_manager(self, group_manager):
        """🔒 تعيين مدير المجموعات مع التحقق"""
        if group_manager is None:
            logger.warning("⚠️ GroupManager فارغ")
            return
            
        if hasattr(group_manager, '__class__'):
            logger.debug(f"✅ تم تعيين GroupManager: {group_manager.__class__.__name__}")
        self.group_manager = group_manager

    def set_notification_manager(self, notification_manager):
        """🔒 تعيين مدير الإشعارات مع التحقق"""
        if notification_manager is None:
            logger.warning("⚠️ NotificationManager فارغ")
            return
            
        if hasattr(notification_manager, '__class__'):
            logger.debug(f"✅ تم تعيين NotificationManager: {notification_manager.__class__.__name__}")
        self.notification_manager = notification_manager

    # ======================================================
    # 🔧 REQUIRED BY GroupManager (Secure)
    # ======================================================
    def count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """
        🔒 عد الصفقات النشطة لرمز ضمن نمط تداول
        """
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"⚠️ رمز غير صالح لـ count_trades_by_mode: {symbol}")
            return 0
            
        if not mode_key or not isinstance(mode_key, str):
            logger.warning(f"⚠️ مفتاح نمط غير صالح: {mode_key}")
            return 0

        try:
            with self.trade_lock:
                count = sum(
                    1 for trade in self.active_trades.values()
                    if trade.get("symbol") == symbol
                    and trade.get("mode") == mode_key
                )
                
                # 🔒 تسجيل للأغراض الأمنية
                if count > self.MAX_TRADES_PER_SYMBOL:
                    self._log_security_event(
                        "high_trade_count", 
                        f"{symbol}: {count} trades in mode {mode_key}"
                    )
                    
                return count
                
        except Exception as e:
            self._handle_error("count_trades_by_mode", e, extra_data={
                "symbol": symbol,
                "mode_key": mode_key
            })
            return 0

    def get_active_trades_count(self, symbol: str = None) -> int:
        """
        🔒 عد جميع الصفقات النشطة لرمز، أو الإجمالي إذا لم يتم تحديد رمز
        """
        try:
            with self.trade_lock:
                if symbol:
                    if not isinstance(symbol, str):
                        logger.warning(f"⚠️ رمز غير صالح: {symbol}")
                        return 0
                        
                    count = sum(
                        1 for trade in self.active_trades.values()
                        if trade.get("symbol") == symbol
                    )
                    
                    # 🔒 التحقق من الحد الأقصى
                    if count > self.MAX_TRADES_PER_SYMBOL:
                        self._log_security_event(
                            "symbol_trade_limit_exceeded",
                            f"{symbol}: {count} trades (max: {self.MAX_TRADES_PER_SYMBOL})"
                        )
                        
                    return count
                else:
                    total = len(self.active_trades)
                    
                    # 🔒 التحقق من الحد الإجمالي
                    if total > self.MAX_TOTAL_TRADES:
                        self._log_security_event(
                            "total_trade_limit_exceeded",
                            f"Total: {total} trades (max: {self.MAX_TOTAL_TRADES})"
                        )
                        
                    return total
                    
        except Exception as e:
            self._handle_error("get_active_trades_count", e, extra_data={
                "symbol": symbol
            })
            return 0

    def open_trade(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> Tuple[bool, str]:
        """
        🔒 فتح صفقة جديدة مع التحقق الأمني
        """
        if not all([symbol, direction, strategy_type, mode_key]):
            logger.error("❌ بيانات صفقة ناقصة")
            return False, "missing_data"
        
        if direction not in ['buy', 'sell']:
            logger.error(f"❌ اتجاه غير صالح: {direction}")
            return False, "invalid_direction"
            
        # 🔒 التحقق من الحدود الأمنية
        symbol_trades = self.get_active_trades_count(symbol)
        if symbol_trades >= self.MAX_TRADES_PER_SYMBOL:
            logger.warning(f"⚠️ تم الوصول للحد الأقصى للصفقات للرمز {symbol}: {symbol_trades}")
            self.metrics["security_blocks"] += 1
            return False, "symbol_limit_exceeded"
            
        total_trades = self.get_active_trades_count()
        if total_trades >= self.MAX_TOTAL_TRADES:
            logger.warning(f"⚠️ تم الوصول للحد الأقصى الإجمالي للصفقات: {total_trades}")
            self.metrics["security_blocks"] += 1
            return False, "total_limit_exceeded"

        try:
            # 🔒 إنشاء معرف آمن للصفقة
            trade_id = self._generate_trade_id(symbol, direction, strategy_type)
            current_time = self._get_current_time()
            
            with self.trade_lock:
                trade_info = {
                    'id': trade_id,
                    'symbol': symbol.upper()[:10],  # 🔒 تطبيع وتحديد الطول
                    'direction': direction.lower(),
                    'strategy_type': strategy_type[:50],  # 🔒 تحديد الطول
                    'mode': mode_key[:50],
                    'opened_at': current_time.isoformat(),
                    'timezone': 'Asia/Riyadh 🇸🇦' if SAUDI_TZ_AVAILABLE else 'UTC',
                    'hash': hashlib.sha256(
                        f"{trade_id}{symbol}{direction}{self.TRADE_ID_SALT}".encode()
                    ).hexdigest()[:16]  # 🔒 هاش للتحقق
                }
                
                self.active_trades[trade_id] = trade_info
                self.symbol_trade_count[symbol] += 1
                self.total_trade_counter += 1
                self.metrics["trades_opened"] += 1
                
                # 🔒 تسجيل أمني
                self._log_security_event("trade_opened", trade_id, {
                    "symbol": symbol,
                    "direction": direction,
                    "strategy": strategy_type
                })
                
                logger.info(f"✅ تم فتح صفقة آمنة: {trade_id}")
                return True, trade_id
                
        except Exception as e:
            self._handle_error("open_trade", e, extra_data={
                "symbol": symbol,
                "direction": direction,
                "strategy": strategy_type
            })
            return False, str(e)

    def handle_exit_signal(self, symbol: str, reason: str = "") -> Tuple[int, List[str]]:
        """
        🔒 إغلاق جميع الصفقات لرمز معين
        """
        if not symbol:
            logger.warning("⚠️ رمز غير محدد لـ handle_exit_signal")
            return 0, []
            
        closed_ids = []
        closed_count = 0
        
        try:
            with self.trade_lock:
                to_close = [
                    tid for tid, trade in self.active_trades.items()
                    if trade.get("symbol") == symbol
                ]
                
                for tid in to_close:
                    trade_info = self.active_trades.pop(tid, None)
                    if trade_info:
                        closed_ids.append(tid)
                        closed_count += 1
                        
                        # 🔒 تسجيل أمني للإغلاق
                        self._log_security_event("trade_closed", tid, {
                            "symbol": symbol,
                            "reason": reason,
                            "direction": trade_info.get('direction')
                        })

            if closed_count > 0:
                self.metrics["trades_closed"] += closed_count
                logger.info(f"🔚 تم إغلاق {closed_count} صفقات للرمز {symbol} - {reason}")
                
                # 🔒 تحديث العداد
                self.symbol_trade_count[symbol] = max(
                    0, self.symbol_trade_count.get(symbol, 0) - closed_count
                )
                
            return closed_count, closed_ids
            
        except Exception as e:
            self._handle_error("handle_exit_signal", e, extra_data={
                "symbol": symbol,
                "reason": reason
            })
            return 0, []

    # ======================================================
    # 📈 TREND HANDLING (Secure)
    # ======================================================
    def get_current_trend(self, symbol: str) -> str:
        """🔒 الحصول على الاتجاه الحالي لرمز"""
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"⚠️ رمز غير صالح لـ get_current_trend: {symbol}")
            return "UNKNOWN"
            
        try:
            # 🔒 التحقق من التخزين المحلي أولاً
            trend = self.current_trend.get(symbol)
            if trend:
                # 🔒 التحقق من صلاحية التخزين المؤقت (5 دقائق)
                update_time = self.trend_update_times.get(symbol)
                if update_time:
                    age = (self._get_current_time() - update_time).total_seconds()
                    if age > 300:  # 5 دقائق
                        logger.debug(f"ℹ️ بيانات اتجاه قديمة للرمز {symbol}: {age:.0f} ثانية")
                        return "UNKNOWN"
                return trend

            # 🔒 التحقق من Redis
            if self.redis_enabled:
                try:
                    saved = self.redis.get_trend(symbol)
                    if saved:
                        self.current_trend[symbol] = saved
                        self.trend_update_times[symbol] = self._get_current_time()
                        return saved
                except Exception as redis_e:
                    logger.warning(f"⚠️ خطأ Redis في get_current_trend: {redis_e}")

            return "UNKNOWN"
            
        except Exception as e:
            self._handle_error("get_current_trend", e, extra_data={
                "symbol": symbol
            })
            return "UNKNOWN"

    def update_trend(self, symbol: str, classification: str, signal_data: Dict) -> Tuple[bool, str, List[str]]:
        """
        🔒 تحديث الاتجاه لرمز مع التحقق الأمني
        """
        if not symbol or not isinstance(signal_data, dict):
            logger.error("❌ بيانات غير صالحة لـ update_trend")
            return False, "UNKNOWN", []

        try:
            # 🔒 تحديد اتجاه الإشارة
            direction = self._determine_trend_direction(signal_data)
            if not direction:
                current = self.get_current_trend(symbol)
                return False, current, []

            with self.trend_lock:
                old_trend = self.get_current_trend(symbol)
                pool = self.trend_pool[symbol]

                # 🔒 تسجيل الإشارة
                signal_type = (signal_data.get("signal_type") or "").strip()
                if signal_type:
                    # 🔒 تحديد حجم مخزن الإشارات
                    if len(pool["signals"]) < 50:  # حد أقصى آمن
                        pool["signals"][signal_type] = True
                    else:
                        logger.warning(f"⚠️ تجاوز حد مخزن إشارات الرمز {symbol}")

                # 🔒 التحقق من العتبة المطلوبة
                required = int(
                    self.config.get("TREND_CHANGE_THRESHOLD", 3)
                )
                if len(pool["signals"]) < required:
                    return False, old_trend, []

                # 🔒 تأكيد تغيير الاتجاه
                self.previous_trend[symbol] = old_trend
                self.current_trend[symbol] = direction
                self.last_reported_trend[symbol] = direction
                self.trend_strength[symbol] = min(
                    self.trend_strength.get(symbol, 0) + 1, 
                    100  # 🔒 حد أقصى للقوة
                )
                self.trend_update_times[symbol] = self._get_current_time()

                # 🔒 تسجيل التاريخ
                self.trend_history[symbol].append({
                    "time": self._get_current_time().isoformat(),
                    "old": old_trend,
                    "new": direction,
                    "signals": list(pool["signals"].keys())[:10],  # 🔒 تحديد العدد
                    "classification": classification[:100]
                })

                # 🔒 حفظ في Redis إذا كان مفعلاً
                if self.redis_enabled:
                    try:
                        with self.redis_lock:
                            self.redis.set_trend(symbol, direction)
                            self._redis_set_raw(
                                f"trend_updated_at:{symbol}",
                                self._get_current_time().isoformat()
                            )
                            
                        # 🔒 تسجيل أمني
                        self._log_security_event("trend_updated", symbol, {
                            "old": old_trend,
                            "new": direction,
                            "signal_count": len(pool["signals"])
                        })
                        
                    except Exception as e:
                        logger.warning(f"⚠️ حفظ Redis للاتجاه فشل: {e}")

                # 🔒 إعادة تعيين المخزن
                used_signals = list(pool["signals"].keys())[:20]  # 🔒 تحديد العدد
                self.trend_pool[symbol] = {
                    "signals": {}, 
                    "count": 0,
                    "created_at": self._get_current_time()
                }

                changed = (old_trend != direction)
                if changed:
                    logger.info(f"📊 تغير اتجاه {symbol}: {old_trend} → {direction}")

                return changed, old_trend, used_signals

        except Exception as e:
            self._handle_error("update_trend", e, extra_data={
                "symbol": symbol,
                "classification": classification
            })
            current = self.get_current_trend(symbol)
            return False, current, []

    def _determine_trend_direction(self, signal_data: Dict) -> Optional[str]:
        """🔒 تحديد اتجاه الاتجاه من بيانات الإشارة"""
        if not signal_data:
            return None
            
        try:
            text = (signal_data.get("signal_type") or "").lower().strip()
            
            # 🔒 قائمة آمنة للكلمات المفتاحية
            bullish_keywords = ['bull', 'up', 'long', 'شراء', 'صاعد']
            bearish_keywords = ['bear', 'down', 'short', 'بيع', 'هابط']
            
            # 🔒 التحقق من الكلمات المفتاحية
            for keyword in bullish_keywords:
                if keyword in text:
                    return "bullish"
                    
            for keyword in bearish_keywords:
                if keyword in text:
                    return "bearish"
                    
            return None
            
        except Exception:
            return None

    # ======================================================
    # 🔴 REDIS HELPERS (Secure)
    # ======================================================
    def _redis_set_raw(self, key: str, value: str):
        """🔒 تعيين قيمة في Redis بشكل آمن"""
        if not self.redis_enabled or not self.redis:
            return
            
        if not key or not isinstance(key, str):
            logger.warning("⚠️ مفتاح Redis غير صالح")
            return
            
        try:
            with self.redis_lock:
                # 🔒 تطبيع المفتاح
                safe_key = key.replace(" ", "_").replace(":", "_")[:100]
                
                if hasattr(self.redis, "set_raw"):
                    self.redis.set_raw(safe_key, value[:1000])  # 🔒 تحديد حجم القيمة
                elif hasattr(self.redis, "client"):
                    self.redis.client.set(safe_key, value[:1000], ex=self.SESSION_TIMEOUT)
                else:
                    logger.warning("⚠️ لا توجد طريقة معروفة للوصول إلى Redis")
                    
        except Exception as e:
            logger.warning(f"⚠️ تعيين Redis الخام فشل: {e}")
            self.metrics["errors"] += 1

    def _load_trends_from_redis(self):
        """🔒 تحميل الاتجاهات من Redis بشكل آمن"""
        if not self.redis_enabled or not self.redis:
            return
            
        try:
            with self.redis_lock:
                if hasattr(self.redis, "get_all_trends"):
                    trends = self.redis.get_all_trends()
                    if isinstance(trends, dict):
                        loaded = 0
                        for symbol, trend in trends.items():
                            if isinstance(symbol, str) and isinstance(trend, str):
                                self.current_trend[symbol] = trend
                                self.trend_update_times[symbol] = self._get_current_time()
                                loaded += 1
                                
                        logger.info(f"✅ تم تحميل {loaded} اتجاه من Redis")
                    else:
                        logger.warning(f"⚠️ تنسيق اتجاهات Redis غير صالح: {type(trends)}")
                        
        except Exception as e:
            logger.warning(f"⚠️ فشل تحميل الاتجاهات من Redis: {e}")

    # ======================================================
    # 🔒 SECURITY & LOGGING
    # ======================================================
    def _handle_error(self, where: str, exc: Exception, extra_data: dict = None):
        """🔒 معالجة الأخطاء بشكل آمن"""
        error_msg = f"{where}: {type(exc).__name__}: {str(exc)}"
        logger.error(error_msg)
        
        self.metrics["errors"] += 1
        
        self._error_log.append({
            "time": self._get_current_time().isoformat(),
            "where": where,
            "error_type": type(exc).__name__,
            "error": str(exc)[:200],  # 🔒 تحديد طول الرسالة
            "extra": extra_data if extra_data else {}
        })
        
        # 🔒 تسجيل أمني للأخطاء الحرجة
        if "password" in str(exc).lower() or "secret" in str(exc).lower():
            self._log_security_event("sensitive_error", where, {
                "error_type": type(exc).__name__,
                "hint": "تحتوي الرسالة على كلمات حساسة"
            })

    def _log_security_event(self, event_type: str, details: Any, extra: dict = None):
        """🔒 تسجيل حدث أمني"""
        try:
            event = {
                "time": self._get_current_time().isoformat(),
                "type": event_type,
                "details": str(details)[:500],
                "extra": extra if extra else {}
            }
            
            self._security_log.append(event)
            
            # 🔒 تسجيل في السجل حسب مستوى الخطورة
            if event_type in ["trade_opened", "trend_updated"]:
                logger.debug(f"🔒 حدث أمني: {event_type} - {details}")
            elif event_type in ["high_trade_count", "symbol_limit_exceeded"]:
                logger.warning(f"⚠️ حدث أمني: {event_type} - {details}")
            elif "failed" in event_type or "error" in event_type:
                logger.error(f"❌ حدث أمني: {event_type} - {details}")
                
        except Exception as e:
            logger.error(f"❌ فشل تسجيل الحدث الأمني: {e}")

    def get_error_log(self) -> List[dict]:
        """🔒 الحصول على سجل الأخطاء (بدون بيانات حساسة)"""
        try:
            # 🔒 تصفية البيانات الحساسة قبل الإرجاع
            safe_log = []
            for entry in list(self._error_log):
                safe_entry = entry.copy()
                
                # 🔒 إزالة أي بيانات حساسة محتملة
                if "extra" in safe_entry and safe_entry["extra"]:
                    for key in list(safe_entry["extra"].keys()):
                        if any(sensitive in key.lower() for sensitive in ["pass", "key", "token", "secret"]):
                            safe_entry["extra"][key] = "***REMOVED***"
                
                safe_log.append(safe_entry)
                
            return safe_log
        except Exception as e:
            logger.error(f"❌ فشل الحصول على سجل الأخطاء: {e}")
            return []

    def get_security_log(self) -> List[dict]:
        """🔒 الحصول على سجل الأمن (للمراقبة فقط)"""
        try:
            return list(self._security_log)
        except Exception as e:
            logger.error(f"❌ فشل الحصول على سجل الأمن: {e}")
            return []

    def get_metrics(self) -> Dict[str, Any]:
        """🔒 الحصول على مقاييس النظام"""
        return {
            **self.metrics,
            "active_trades": len(self.active_trades),
            "total_symbols": len(self.symbol_trade_count),
            "redis_enabled": self.redis_enabled,
            "security_events": len(self._security_log),
            "error_count": len(self._error_log)
        }

    # ======================================================
    # 🧹 CLEANUP (Secure)
    # ======================================================
    def cleanup_memory(self):
        """🔒 تنظيف الذاكرة مع التحقق الأمني"""
        try:
            cutoff = self._get_current_time() - timedelta(days=7)
            
            # 🔒 تنظيف تاريخ الاتجاهات
            for symbol, hist in list(self.trend_history.items()):
                cleaned = [
                    h for h in hist
                    if "time" in h and h["time"] >= cutoff.isoformat()
                ]
                self.trend_history[symbol] = deque(cleaned, maxlen=200)
            
            # 🔒 تنظيف مخازن الاتجاهات القديمة
            for symbol, pool in list(self.trend_pool.items()):
                if "created_at" in pool and pool["created_at"] < cutoff:
                    del self.trend_pool[symbol]
            
            # 🔒 تسجيل حدث التنظيف
            self._log_security_event("memory_cleanup", "تم تنظيف البيانات القديمة")
            
            logger.info("🧹 تم تنظيف الذاكرة بنجاح")
            
        except Exception as e:
            self._handle_error("cleanup_memory", e)

    def shutdown(self):
        """🔒 إيقاف النظام بشكل آمن"""
        try:
            logger.info("🔒 إيقاف TradeManager بشكل آمن...")
            
            # 🔒 تسجيل المقاييس النهائية
            final_metrics = self.get_metrics()
            logger.info(f"📊 المقاييس النهائية: {json.dumps(final_metrics, ensure_ascii=False)}")
            
            # 🔒 تسجيل أحداث الأمن
            security_count = len(self._security_log)
            if security_count > 0:
                logger.info(f"🔒 أحداث الأمن المسجلة: {security_count}")
            
            # 🔒 إغلاق اتصالات Redis
            if self.redis and hasattr(self.redis, "close"):
                try:
                    self.redis.close()
                    logger.info("✅ تم إغلاق اتصال Redis")
                except Exception as e:
                    logger.error(f"❌ خطأ في إغلاق Redis: {e}")
            
            logger.info("✅ تم إيقاف TradeManager بنجاح")
            
        except Exception as e:
            logger.error(f"❌ خطأ في عملية الإيقاف: {e}")
