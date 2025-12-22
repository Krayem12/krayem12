# core/trade_manager.py
# ==========================================================
# ✅ TradeManager – FINAL & COMPATIBLE VERSION
# ==========================================================

import logging
import threading
from datetime import timedelta
from typing import Dict, List, Optional
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

    ✔ يدير الاتجاهات (Trend)
    ✔ متوافق بالكامل مع GroupManager و TradingSystem
    ✔ يحتوي جميع الدوال المتوقعة (Contracts)
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
        """
        Count open trades for a symbol within a trading mode.
        """
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
        """
        Count all open trades for a symbol, or total trades if no symbol.
        """
        try:
            with self.trade_lock:
                if symbol:
                    return sum(
                        1 for trade in self.active_trades.values()
                        if trade.get("symbol") == symbol
                    )
                else:
                    # 🔧 FIXED: إرجاع إجمالي عدد الصفقات عندما لا يتم تمرير رمز
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
        """
        Close all trades for a symbol.
        """
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
                logger.info(
                    f"🔚 Closed {closed} trades for {symbol} - {reason}"
                )
        except Exception as e:
            logger.error(f"handle_exit_signal failed: {e}")

        return closed

    # ======================================================
    # 📈 TREND HANDLING
    # ======================================================
    def get_current_trend(self, symbol: str) -> str:
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

    def update_trend(
        self, symbol: str, classification: str, signal_data: Dict
    ) -> (bool, str, List[str]):

        try:
            direction = self._determine_trend_direction(signal_data)
            if not direction:
                return False, self.get_current_trend(symbol), []

            with self.trend_lock:
                old_trend = self.get_current_trend(symbol)
                pool = self.trend_pool[symbol]

                signal_type = (signal_data.get("signal_type") or "").strip()
                if signal_type:
                    pool["signals"][signal_type] = True

                required = int(
                    self.config.get("TREND_CHANGE_THRESHOLD", 2)
                )
                if len(pool["signals"]) < required:
                    return False, old_trend, []

                # Confirm change
                self.previous_trend[symbol] = old_trend
                self.current_trend[symbol] = direction
                self.last_reported_trend[symbol] = direction
                self.trend_strength[symbol] += 1

                self.trend_history[symbol].append({
                    "time": saudi_time.now().isoformat(),
                    "old": old_trend,
                    "new": direction,
                    "signals": list(pool["signals"].keys())
                })

                if self.redis_enabled:
                    try:
                        self.redis.set_trend(symbol, direction)
                        self._redis_set_raw(
                            f"trend_updated_at:{symbol}",
                            saudi_time.now().isoformat()
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Redis save failed: {e}")

                used = list(pool["signals"].keys())
                self.trend_pool[symbol] = {"signals": {}, "count": 0}

                return old_trend != direction, old_trend, used

        except Exception as e:
            self._handle_error("update_trend", e)
            return False, self.get_current_trend(symbol), []

    def _determine_trend_direction(self, signal_data: Dict) -> Optional[str]:
        """🎯 تحديد اتجاه الإشارة بدقة باستخدام قوائم الإشارات من الإعدادات"""
        try:
            signal_type = (signal_data.get("signal_type") or "").lower().strip()
            
            if not signal_type:
                logger.warning("⚠️ نوع الإشارة فارغ")
                return None
            
            logger.debug(f"🔍 فحص اتجاه الإشارة: '{signal_type}'")
            
            # الحصول على قوائم الإشارات من الإعدادات
            config = getattr(self, 'config', {})
            
            # تحليل إشارات TREND من الإعدادات
            trend_signals_str = config.get('TREND_SIGNALS', '')
            trend_signals = [s.strip() for s in trend_signals_str.split(',') if s.strip()]
            
            # فصل الإشارات الصاعدة والهابطة
            bullish_trend_signals = []
            bearish_trend_signals = []
            
            for signal in trend_signals:
                signal_lower = signal.lower()
                if 'bull' in signal_lower or 'up' in signal_lower:
                    bullish_trend_signals.append(signal_lower)
                elif 'bear' in signal_lower or 'down' in signal_lower:
                    bearish_trend_signals.append(signal_lower)
            
            # تحقق من إشارات الصعود المحددة
            if signal_type in bullish_trend_signals:
                logger.info(f"🎯 إشارة صعود محددة: {signal_type} -> bullish")
                return "bullish"
            
            # تحقق من إشارات الهبوط المحددة
            if signal_type in bearish_trend_signals:
                logger.info(f"🎯 إشارة هبوط محددة: {signal_type} -> bearish")
                return "bearish"
            
            # التحقق من الكلمات المفتاحية
            bullish_keywords_str = config.get('BULLISH_KEYWORDS', 'bullish,buy,long,up,rise,increase')
            bearish_keywords_str = config.get('BEARISH_KEYWORDS', 'bearish,sell,short,down,fall,decrease')
            
            bullish_keywords = [k.strip().lower() for k in bullish_keywords_str.split(',') if k.strip()]
            bearish_keywords = [k.strip().lower() for k in bearish_keywords_str.split(',') if k.strip()]
            
            # التحقق من الكلمات المفتاحية للصعود
            for keyword in bullish_keywords:
                if keyword and keyword in signal_type:
                    logger.info(f"🎯 كلمة صعود مفتاحية: '{keyword}' في '{signal_type}' -> bullish")
                    return "bullish"
            
            # التحقق من الكلمات المفتاحية للهبوط
            for keyword in bearish_keywords:
                if keyword and keyword in signal_type:
                    logger.info(f"🎯 كلمة هبوط مفتاحية: '{keyword}' في '{signal_type}' -> bearish")
                    return "bearish"
            
            # التحقق العام (كخطة احتياطية)
            if 'bull' in signal_type or 'up' in signal_type or 'buy' in signal_type:
                logger.info(f"🎯 اكتشاف صعود عام: {signal_type} -> bullish")
                return "bullish"
            
            if 'bear' in signal_type or 'down' in signal_type or 'sell' in signal_type:
                logger.info(f"🎯 اكتشاف هبوط عام: {signal_type} -> bearish")
                return "bearish"
            
            # 🔍 تسجيل إشارات الاتجاه المتاحة للمساعدة في التصحيح
            logger.debug(f"📋 إشارات الصعود المتاحة: {bullish_trend_signals}")
            logger.debug(f"📋 إشارات الهبوط المتاحة: {bearish_trend_signals}")
            logger.debug(f"📋 كلمات الصعود المفتاحية: {bullish_keywords}")
            logger.debug(f"📋 كلمات الهبوط المفتاحية: {bearish_keywords}")
            
            logger.warning(f"⚠️ اتجاه غير محدد للإشارة: {signal_type}")
            return None
            
        except Exception as e:
            self._handle_error("_determine_trend_direction", e)
            return None

    # ======================================================
    # 🔴 REDIS HELPERS
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

    # ======================================================
    # 🧹 CLEANUP
    # ======================================================
    def cleanup_memory(self):
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

    # ======================================================
    # 🧾 ERROR LOG
    # ======================================================
    def _handle_error(self, where: str, exc: Exception):
        logger.error(f"{where}: {exc}")
        self._error_log.append({
            "time": saudi_time.now().isoformat(),
            "where": where,
            "error": str(exc)
        })

    def get_error_log(self) -> List[dict]:
        return list(self._error_log)
