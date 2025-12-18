import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
from collections import defaultdict, deque

# 🛠️ استيراد التوقيت السعودي
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
                self.timezone = pytz.timezone('Asia/Riyadh')

            def now(self):
                return datetime.now(self.timezone)

            def format_time(self, dt=None):
                if dt is None:
                    dt = self.now()
                return dt.strftime('%Y-%m-%d %I:%M:%S %p')

        saudi_time = SaudiTime()
        logging.warning("⚠️ استخدام SaudiTime البديل")

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
    🎯 TradeManager – Enhanced Trend System
    📌 يدعم:
    - اتجاهات ثابتة
    - تخزين Redis
    - وقت تحديث حقيقي بالتوقيت السعودي 🇸🇦
    """

    def __init__(self, config):
        self.config = config
        self.trade_lock = threading.RLock()

        self.active_trades = {}
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0
        self.metrics = {"trades_opened": 0, "trades_closed": 0}

        self.current_trend = {}
        self.previous_trend = {}
        self.last_reported_trend = {}
        self.trend_strength = {}
        self.trend_signals_count = defaultdict(int)
        self.trend_history = defaultdict(lambda: deque(maxlen=50))
        self.trend_pool = {}

        self.group_manager = None
        self.notification_manager = None
        self._error_log = deque(maxlen=500)

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

        logger.info("🎯 TradeManager جاهز – Redis + Saudi Time 🇸🇦")

    def set_group_manager(self, gm):
        self.group_manager = gm

    def set_notification_manager(self, nm):
        self.notification_manager = nm

    # =========================================================
    # 🔥 تحديث الاتجاه + حفظ وقت التحديث الحقيقي
    # =========================================================
    def update_trend(self, symbol: str, classification: str, signal_data: Dict):
        try:
            direction = self._determine_trend_direction(classification, signal_data)
            if not direction:
                return False, "UNKNOWN", []

            old_trend = self.current_trend.get(symbol, "UNKNOWN")
            trend_changed = old_trend != direction

            self.current_trend[symbol] = direction
            self.last_reported_trend[symbol] = direction
            self.trend_strength[symbol] += 1

            updated_at = saudi_time.now().isoformat()

            # ✅ حفظ الاتجاه + وقت التحديث في Redis
            if self.redis_enabled:
                self.redis.set(f"trend:{symbol}", direction)
                self.redis.set(f"trend:{symbol}:updated_at", updated_at)

                logger.info(
                    f"💾 REDIS | {symbol} → {RED}{direction.upper()}{RESET} | "
                    f"UpdatedAt={updated_at} 🇸🇦"
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

    # =========================================================
    # 🧠 استخراج الاتجاه
    # =========================================================
    def _determine_trend_direction(self, classification: str, signal_data: Dict) -> Optional[str]:
        st = signal_data.get("signal_type", "").lower()
        cl = classification.lower()

        if "bullish" in st or "bullish" in cl:
            return "bullish"
        if "bearish" in st or "bearish" in cl:
            return "bearish"
        return None

    # =========================================================
    # ⏱️ جلب وقت آخر تحديث (لصفحة الويب)
    # =========================================================
    def get_trend_updated_at(self, symbol: str) -> Optional[str]:
        try:
            if self.redis_enabled:
                val = self.redis.get(f"trend:{symbol}:updated_at")
                if val:
                    return val.decode() if isinstance(val, bytes) else str(val)
            return None
        except Exception as e:
            self._handle_error("⚠️ خطأ في قراءة updated_at", e)
            return None

    # =========================================================
    # 🔁 تحميل الاتجاهات عند بدء التشغيل
    # =========================================================
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

    # =========================================================
    # 🧹 إدارة الأخطاء
    # =========================================================
    def _handle_error(self, msg, exc=None):
        full = f"{msg}: {exc}" if exc else msg
        logger.error(full)
        self._error_log.append({
            "timestamp": saudi_time.now().isoformat(),
            "timezone": "Asia/Riyadh 🇸🇦",
            "error": full
        })

    # =========================================================
    # 📊 معلومات النظام
    # =========================================================
    def get_system_stats(self) -> Dict:
        return {
            "active_trades": len(self.active_trades),
            "current_trends": dict(self.current_trend),
            "redis_enabled": self.redis_enabled,
            "timestamp": saudi_time.now().isoformat(),
            "timezone": "Asia/Riyadh 🇸🇦"
        }
