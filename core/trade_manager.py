import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
from collections import defaultdict, deque

# 🛠️ التوقيت السعودي
try:
    from utils.time_utils import saudi_time
except ImportError:
    try:
        from ..utils.time_utils import saudi_time
    except ImportError:
        import pytz
        from datetime import datetime

        class SaudiTime:
            def __init__(self):
                self.timezone = pytz.timezone("Asia/Riyadh")

            def now(self):
                return datetime.now(self.timezone)

            def format_time(self, dt=None):
                if dt is None:
                    dt = self.now()
                return dt.strftime("%Y-%m-%d %H:%M:%S")

        saudi_time = SaudiTime()
        logging.warning("⚠️ SaudiTime fallback مستخدم")

logger = logging.getLogger(__name__)

RED = "\033[91m"
RESET = "\033[0m"

try:
    from utils.redis_helper import RedisManager
except ImportError:
    try:
        from ..utils.redis_helper import RedisManager
    except ImportError:
        RedisManager = None
        logger.warning("⚠️ RedisManager غير متوفر")


class TradeManager:
    """
    🎯 TradeManager – FINAL STABLE VERSION
    - Trend handling
    - Redis persistence
    - Saudi Time
    """

    def __init__(self, config):
        self.config = config
        self.trade_lock = threading.RLock()

        # Trades
        self.active_trades = {}
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0
        self.metrics = {"trades_opened": 0, "trades_closed": 0}

        # Trend state
        self.current_trend = {}
        self.previous_trend = {}
        self.last_reported_trend = {}
        self.trend_strength = defaultdict(int)
        self.trend_signals_count = defaultdict(int)
        self.trend_history = defaultdict(lambda: deque(maxlen=50))
        self.trend_pool = {}

        self.group_manager = None
        self.notification_manager = None
        self._error_log = deque(maxlen=500)

        # Redis
        self.redis = None
        self.redis_enabled = False
        try:
            if RedisManager:
                self.redis = RedisManager()
                self.redis_enabled = getattr(self.redis, "is_enabled", lambda: False)()
        except Exception:
            self.redis_enabled = False

        if self.redis_enabled:
            self._load_trends_from_redis()

        logger.info("✅ TradeManager FINAL جاهز – Redis + Saudi Time 🇸🇦")

    # ======================================================
    # 🔗 ربط المدراء
    # ======================================================
    def set_group_manager(self, gm):
        self.group_manager = gm

    def set_notification_manager(self, nm):
        self.notification_manager = nm

    # ======================================================
    # 🔎 الاتجاه الحالي (مطلوب للـ webhook_handler)
    # ======================================================
    def get_current_trend(self, symbol: str) -> str:
        try:
            trend = self.current_trend.get(symbol)
            if trend:
                return trend

            if self.redis_enabled:
                saved = self.redis.get(f"trend:{symbol}")
                if saved:
                    saved_trend = saved.decode() if isinstance(saved, bytes) else str(saved)
                    self.current_trend[symbol] = saved_trend
                    return saved_trend

            return "UNKNOWN"

        except Exception as e:
            self._handle_error(f"⚠️ خطأ في get_current_trend لـ {symbol}", e)
            return "UNKNOWN"

    # ======================================================
    # 📈 تحديث الاتجاه (مع حفظ الوقت الحقيقي)
    # ======================================================
    def update_trend(self, symbol: str, classification: str, signal_data: Dict):
        try:
            direction = self._determine_trend_direction(classification, signal_data)
            if not direction:
                return False, "UNKNOWN", []

            old_trend = self.get_current_trend(symbol)
            trend_changed = old_trend != direction

            self.current_trend[symbol] = direction
            self.last_reported_trend[symbol] = direction
            self.trend_strength[symbol] += 1

            updated_at = saudi_time.now().isoformat()

            if self.redis_enabled:
                self.redis.set(f"trend:{symbol}", direction)
                self.redis.set(f"trend:{symbol}:updated_at", updated_at)

                logger.info(
                    f"💾 REDIS | {symbol} → {RED}{direction.upper()}{RESET} | {updated_at} 🇸🇦"
                )

            self.trend_history[symbol].append({
                "timestamp": updated_at,
                "old_trend": old_trend,
                "new_trend": direction,
                "timezone": "Asia/Riyadh 🇸🇦"
            })

            return trend_changed, old_trend, []

        except Exception as e:
            self._handle_error("💥 خطأ في update_trend", e)
            return False, "UNKNOWN", []

    # ======================================================
    # 🧠 تحديد الاتجاه
    # ======================================================
    def _determine_trend_direction(self, classification: str, signal_data: Dict) -> Optional[str]:
        signal_type = signal_data.get("signal_type", "").lower()
        classification = classification.lower()

        bullish = ["bullish", "buy", "long", "up"]
        bearish = ["bearish", "sell", "short", "down"]

        if any(k in signal_type or k in classification for k in bullish):
            return "bullish"
        if any(k in signal_type or k in classification for k in bearish):
            return "bearish"

        return None

    # ======================================================
    # 🔁 تحميل الاتجاهات من Redis
    # ======================================================
    def _load_trends_from_redis(self):
        try:
            trends = self.redis.get_all_trends()
            for symbol, trend in trends.items():
                self.current_trend[symbol] = trend
                logger.info(
                    f"🔁 REDIS LOAD | {symbol} = {RED}{trend.upper()}{RESET}"
                )
        except Exception as e:
            self._handle_error("⚠️ خطأ تحميل الاتجاهات من Redis", e)

    # ======================================================
    # ⏱️ وقت آخر تحديث
    # ======================================================
    def get_trend_updated_at(self, symbol: str) -> Optional[str]:
        try:
            if self.redis_enabled:
                value = self.redis.get(f"trend:{symbol}:updated_at")
                if value:
                    return value.decode() if isinstance(value, bytes) else str(value)
            return None
        except Exception as e:
            self._handle_error("⚠️ خطأ قراءة updated_at", e)
            return None

    # ======================================================
    # 🧹 الأخطاء
    # ======================================================
    def _handle_error(self, msg, exc=None):
        full = f"{msg}: {exc}" if exc else msg
        logger.error(full)
        self._error_log.append({
            "timestamp": saudi_time.now().isoformat(),
            "timezone": "Asia/Riyadh 🇸🇦",
            "error": full
        })

    # ======================================================
    # 📊 إحصائيات
    # ======================================================
    def get_system_stats(self) -> Dict:
        return {
            "active_trades": len(self.active_trades),
            "current_trends": dict(self.current_trend),
            "redis_enabled": self.redis_enabled,
            "timestamp": saudi_time.now().isoformat(),
            "timezone": "Asia/Riyadh 🇸🇦"
        }
