# core/trade_manager.py
# ==========================================================
# ✅ TradeManager – FINAL VERSION
# ==========================================================

import logging
import threading
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque

# ----------------------------------------------------------
# 🕒 Saudi Time (Safe Import)
# ----------------------------------------------------------
try:
    from utils.time_utils import saudi_time
except Exception:
    import pytz
    from datetime import datetime

    class SaudiTime:
        def __init__(self):
            self.tz = pytz.timezone("Asia/Riyadh")

        def now(self):
            return datetime.now(self.tz)

    saudi_time = SaudiTime()

# ----------------------------------------------------------
# 🔴 Redis Manager (Safe Import)
# ----------------------------------------------------------
try:
    from utils.redis_manager import RedisManager
except Exception:
    try:
        from core.redis_manager import RedisManager
    except Exception:
        RedisManager = None

logger = logging.getLogger(__name__)


class TradeManager:
    """
    TradeManager – FINAL VERSION
    ✔ يدير الاتجاهات (Trend) ولا يرسل إشعار إلا عند تحديد اتجاه واضح
    """

    # ======================================================
    # 🚀 INIT
    # ======================================================
    def __init__(self, config: dict):
        self.config = config

        logger.info(f"🧠 TradeManager loaded from: {__file__}")

        # Locks
        self.trade_lock = threading.Lock()
        self.trend_lock = threading.Lock()

        # Trades
        self.active_trades: Dict[str, dict] = {}
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0
        self.metrics = {
            "trades_opened": 0,
            "trades_closed": 0
        }

        # Trends
        self.current_trend: Dict[str, str] = {}
        self.previous_trend: Dict[str, str] = {}
        self.last_reported_trend: Dict[str, str] = {}
        self.trend_strength: Dict[str, int] = defaultdict(int)

        # Trend buffers
        self.trend_pool: Dict[str, dict] = defaultdict(lambda: {
            "signals": {},
            "count": 0
        })
        self.trend_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )

        # External managers
        self.group_manager = None
        self.notification_manager = None

        # Error log
        self._error_log = deque(maxlen=200)

        # Redis
        self.redis = None
        self.redis_enabled = False
        if RedisManager:
            try:
                self.redis = RedisManager(config)
                self.redis_enabled = getattr(
                    self.redis, "is_enabled", lambda: False
                )()
                if self.redis_enabled:
                    self._load_trends_from_redis()
            except Exception as e:
                logger.warning(f"⚠️ Redis init failed: {e}")
                self.redis = None
                self.redis_enabled = False

        logger.info("✅ TradeManager FINAL initialized – Saudi Time 🇸🇦")

    # ======================================================
    # 🔗 REQUIRED BY TradingSystem
    # ======================================================
    def set_group_manager(self, group_manager):
        self.group_manager = group_manager

    def set_notification_manager(self, notification_manager):
        self.notification_manager = notification_manager

    # ======================================================
    # 🔧 REQUIRED BY GroupManager
    # ======================================================
    def count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """عدد الصفقات المفتوحة للنمط"""
        try:
            with self.trade_lock:
                return sum(
                    1 for trade in self.active_trades.values()
                    if trade.get("symbol") == symbol
                    and trade.get("mode") == mode_key
                )
        except Exception as e:
            logger.error(f"count_trades_by_mode failed: {e}")
            return 0

    def get_active_trades_count(self, symbol: str = None) -> int:
        """عدد الصفقات النشطة"""
        try:
            with self.trade_lock:
                if symbol:
                    return sum(
                        1 for trade in self.active_trades.values()
                        if trade.get("symbol") == symbol
                    )
                else:
                    return len(self.active_trades)
        except Exception as e:
            logger.error(f"get_active_trades_count failed: {e}")
            return 0

    def open_trade(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> bool:
        """فتح صفقة جديدة"""
        try:
            trade_id = f"{symbol}_{direction}_{saudi_time.now().strftime('%Y%m%d%H%M%S')}_{hash(strategy_type) % 10000:04d}"
            
            with self.trade_lock:
                trade_info = {
                    'id': trade_id,
                    'symbol': symbol,
                    'direction': direction,
                    'strategy_type': strategy_type,
                    'mode': mode_key,
                    'opened_at': saudi_time.now().isoformat(),
                    'timezone': 'Asia/Riyadh 🇸🇦'
                }
                
                self.active_trades[trade_id] = trade_info
                self.symbol_trade_count[symbol] += 1
                self.total_trade_counter += 1
                self.metrics["trades_opened"] += 1
                
                logger.info(f"✅ تم فتح صفقة: {trade_id} - التوقيت السعودي 🇸🇦")
                return True
                
        except Exception as e:
            self._handle_error("open_trade", e)
            return False

    def handle_exit_signal(self, symbol: str, reason: str = "") -> int:
        """إغلاق جميع صفقات الرمز"""
        closed = 0
        try:
            with self.trade_lock:
                to_close = [
                    tid for tid, trade in self.active_trades.items()
                    if trade.get("symbol") == symbol
                ]
                for tid in to_close:
                    self.active_trades.pop(tid, None)
                    closed += 1

            if closed:
                self.metrics["trades_closed"] += closed
                logger.info(f"🔚 تم إغلاق {closed} صفقة لـ {symbol}")

        except Exception as e:
            logger.error(f"handle_exit_signal failed: {e}")

        return closed

    # ======================================================
    # 📈 TREND HANDLING - النسخة النهائية
    # ======================================================
    def get_current_trend(self, symbol: str) -> str:
        """الحصول على الاتجاه الحالي"""
        try:
            trend = self.current_trend.get(symbol)
            if trend:
                return trend

            if self.redis_enabled:
                saved = self.redis.get_trend(symbol)
                if saved:
                    self.current_trend[symbol] = saved
                    return saved

            return "UNKNOWN"
        except Exception as e:
            self._handle_error("get_current_trend", e)
            return "UNKNOWN"

    def update_trend(self, symbol: str, classification: str, signal_data: Dict) -> Tuple[bool, str, List[str]]:
        """🎯 تحديث الاتجاه - لا يرسل إشعار إلا عند تحديد اتجاه واضح"""
        try:
            # تحديد اتجاه الإشارة
            direction = self._determine_trend_direction_enhanced(signal_data, classification)
            if not direction:
                logger.info(f"📭 إشارة بدون اتجاه واضح: {signal_data.get('signal_type')}")
                return False, self.get_current_trend(symbol), []

            with self.trend_lock:
                old_trend = self.get_current_trend(symbol)
                pool = self.trend_pool[symbol]

                signal_type = (signal_data.get("signal_type") or "").strip()
                if not signal_type:
                    return False, old_trend, []

                required = self.config.get("TREND_REQUIRED_SIGNALS", 2)
                
                # 🎯 التحقق من التعارض مع الإشارات الموجودة
                existing_directions = []
                for sig_info in pool["signals"].values():
                    existing_directions.append(sig_info.get("direction"))
                
                if existing_directions:
                    # إذا كانت الإشارة الجديدة تتعارض مع الموجودة
                    if direction not in existing_directions:
                        logger.warning(f"⚠️ تعارض اتجاهات: {signal_type} -> {direction} يختلف عن {existing_directions}")
                        
                        # 🎯 حذف المجمع القديم وبدء جديد
                        self.trend_pool[symbol] = {"signals": {}, "count": 0}
                        pool = self.trend_pool[symbol]
                        
                        logger.info(f"🔄 تمت إعادة تعيين المجمع بسبب التعارض")
                
                # إضافة الإشارة الجديدة
                pool["signals"][signal_type] = {
                    "direction": direction,
                    "timestamp": saudi_time.now().isoformat()
                }
                pool["count"] = len(pool["signals"])
                
                logger.info(f"📥 تمت إضافة الإشارة: {signal_type} -> {direction}")
                
                # 🎯 التحقق مما إذا كان لدينا إشارات كافية في نفس الاتجاه
                direction_counts = {"bullish": 0, "bearish": 0}
                for sig_info in pool["signals"].values():
                    sig_direction = sig_info.get("direction")
                    if sig_direction in direction_counts:
                        direction_counts[sig_direction] += 1
                
                logger.info(f"📊 حالة المجمع: إشارات={pool['count']}, صاعدة={direction_counts['bullish']}, هابطة={direction_counts['bearish']}")
                
                # 🎯 القاعدة: ننتظر حتى نحصل على إشارتين في نفس الاتجاه
                new_direction = None
                signals_used = []
                
                if direction_counts["bullish"] >= required:
                    new_direction = "bullish"
                    signals_used = [sig for sig, info in pool["signals"].items() if info.get("direction") == "bullish"]
                    logger.info(f"✅ تم تحديد اتجاه صاعد: {direction_counts['bullish']} إشارة")
                    
                elif direction_counts["bearish"] >= required:
                    new_direction = "bearish"
                    signals_used = [sig for sig, info in pool["signals"].items() if info.get("direction") == "bearish"]
                    logger.info(f"✅ تم تحديد اتجاه هابط: {direction_counts['bearish']} إشارة")
                
                # 🎯 إذا لم نحصل على إشارات كافية في نفس الاتجاه
                if not new_direction:
                    logger.info(f"⏸️ إشارات غير كافية لاتجاه واضح: تحتاج {required} إشارة في نفس الاتجاه")
                    
                    # 🎯 إذا كان هناك تعارض (إشارات في اتجاهين مختلفين)
                    if direction_counts["bullish"] > 0 and direction_counts["bearish"] > 0:
                        logger.warning(f"⚠️ تعارض: إشارات في اتجاهين مختلفين - صاعدة: {direction_counts['bullish']}, هابطة: {direction_counts['bearish']}")
                        # 🎯 إعادة تعيين المجمع لبدء جديدة
                        self.trend_pool[symbol] = {"signals": {}, "count": 0}
                        logger.info(f"🧹 تم إعادة تعيين المجمع بسبب التعارض")
                    
                    # 🎯 لا نرسل إشعار عند عدم وجود اتجاه واضح
                    return False, old_trend, []
                
                # 🎯 إذا وصلنا هنا، فهذا يعني أن لدينا اتجاه واضح
                trend_changed = (old_trend != new_direction)
                
                if trend_changed:
                    # تحديث بيانات الاتجاه
                    self.previous_trend[symbol] = old_trend
                    self.current_trend[symbol] = new_direction
                    self.last_reported_trend[symbol] = new_direction
                    self.trend_strength[symbol] = len(signals_used)
                    
                    # تسجيل في التاريخ
                    self.trend_history[symbol].append({
                        "time": saudi_time.now().isoformat(),
                        "old": old_trend,
                        "new": new_direction,
                        "signals": signals_used,
                        "signal_count": len(signals_used),
                        "reason": f"تجميع {len(signals_used)} إشارة {new_direction}"
                    })
                    
                    # حفظ في Redis
                    if self.redis_enabled:
                        try:
                            self.redis.set_trend(symbol, new_direction)
                            self._redis_set_raw(
                                f"trend:{symbol}:updated_at",
                                saudi_time.now().isoformat()
                            )
                        except Exception as e:
                            logger.warning(f"⚠️ حفظ Redis فشل: {e}")
                    
                    # 🎯 مسح المجمع بعد تحديد الاتجاه
                    self.trend_pool[symbol] = {"signals": {}, "count": 0}
                    
                    logger.info(f"🎯 تم تغيير الاتجاه: {symbol} -> {old_trend} → {new_direction}")
                    return True, old_trend, signals_used
                else:
                    # نفس الاتجاه، لا تغيير
                    logger.info(f"⏸️ نفس الاتجاه: {symbol} -> {new_direction}")
                    
                    # 🎯 مسح المجمع بعد تأكيد الاتجاه
                    self.trend_pool[symbol] = {"signals": {}, "count": 0}
                    
                    return False, old_trend, signals_used

        except Exception as e:
            self._handle_error("update_trend", e)
            return False, self.get_current_trend(symbol), []

    def _determine_trend_direction_enhanced(self, signal_data: Dict, classification: str = None) -> Optional[str]:
        """تحديد اتجاه الإشارة بدقة"""
        try:
            signal_type = (signal_data.get("signal_type") or "").lower().strip()
            
            if not signal_type:
                return None
            
            # 🎯 قواعد تحديد الاتجاه
            if 'money_flow_down' in signal_type:
                return "bearish"
            if 'money_flow_up' in signal_type:
                return "bullish"
            if 'trend_catcher_bullish' in signal_type:
                return "bullish"
            if 'trend_catcher_bearish' in signal_type:
                return "bearish"
            
            # الكلمات المفتاحية
            if any(word in signal_type for word in ['bull', 'up', 'buy', 'long', 'rise']):
                return "bullish"
            if any(word in signal_type for word in ['bear', 'down', 'sell', 'short', 'fall']):
                return "bearish"
            
            return None
            
        except Exception as e:
            self._handle_error("_determine_trend_direction_enhanced", e)
            return None

    # ======================================================
    # 🧹 CLEANUP & HELPERS
    # ======================================================
    def _redis_set_raw(self, key: str, value: str):
        if not self.redis_enabled or not self.redis:
            return
        try:
            if hasattr(self.redis, "set_raw"):
                self.redis.set_raw(key, value)
            elif hasattr(self.redis, "client"):
                self.redis.client.set(key, value)
        except Exception as e:
            logger.warning(f"⚠️ Redis raw set failed: {e}")

    def _load_trends_from_redis(self):
        if not self.redis_enabled or not self.redis:
            return
        try:
            if hasattr(self.redis, "get_all_trends"):
                for symbol, trend in self.redis.get_all_trends().items():
                    self.current_trend[symbol] = trend
        except Exception as e:
            logger.warning(f"⚠️ Redis load trends failed: {e}")

    def cleanup_memory(self):
        """تنظيف الذاكرة"""
        try:
            cutoff = saudi_time.now() - timedelta(days=7)
            for symbol, hist in list(self.trend_history.items()):
                self.trend_history[symbol] = deque(
                    [
                        h for h in hist
                        if h.get("time") >= cutoff.isoformat()
                    ],
                    maxlen=200
                )
        except Exception as e:
            self._handle_error("cleanup_memory", e)

    def _handle_error(self, where: str, exc: Exception):
        """معالجة الأخطاء"""
        logger.error(f"{where}: {exc}")
        self._error_log.append({
            "time": saudi_time.now().isoformat(),
            "where": where,
            "error": str(exc)
        })

    def get_error_log(self) -> List[dict]:
        return list(self._error_log)
