import logging
import threading
from datetime import timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque

# ---------------------------------------
# 🕒 Saudi Time (Safe Import)
# ---------------------------------------
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

logger = logging.getLogger(__name__)

# ---------------------------------------
# 🔴 Redis Manager (Safe Import)
# ---------------------------------------
try:
    from utils.redis_helper import RedisManager
except Exception:
    try:
        from ..utils.redis_helper import RedisManager
    except Exception:
        RedisManager = None
        logger.warning("⚠️ RedisManager غير متوفر")

RED = "\033[91m"
RESET = "\033[0m"


class TradeManager:
    """
    🎯 FINAL TradeManager
    - Stable
    - Redis compatible
    - Saudi Time
    """

    def __init__(self, config: Dict):
        self.config = config
        self.trade_lock = threading.RLock()

        # Trades
        self.active_trades = {}
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0
        self.metrics = {"trades_opened": 0, "trades_closed": 0}

        # Trends
        self.current_trend = {}
        self.previous_trend = {}
        self.last_reported_trend = {}
        self.trend_strength = defaultdict(int)
        self.trend_signals_count = defaultdict(int)
        self.trend_history = defaultdict(lambda: deque(maxlen=50))
        self.trend_pool = {}

        # Managers
        self.group_manager = None
        self.notification_manager = None

        # Errors
        self._error_log = deque(maxlen=500)

        # Redis
        self.redis = None
        self.redis_enabled = False
        try:
            if RedisManager:
                self.redis = RedisManager()
                self.redis_enabled = getattr(self.redis, "is_enabled", lambda: False)()
        except Exception:
            self.redis = None
            self.redis_enabled = False

        if self.redis_enabled:
            self._load_trends_from_redis()

        logger.info("✅ TradeManager FINAL initialized – Saudi Time 🇸🇦")

    # ------------------------------------------------------------------
    # 🔗 External Managers
    # ------------------------------------------------------------------
    def set_group_manager(self, gm):
        self.group_manager = gm

    def set_notification_manager(self, nm):
        self.notification_manager = nm

    # ------------------------------------------------------------------
    # 🔎 Current Trend (Webhook compatible)
    # ------------------------------------------------------------------
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
            self._handle_error(f"get_current_trend error for {symbol}", e)
            return "UNKNOWN"

    # ------------------------------------------------------------------
    # 📈 Update Trend (CORE)
    # ------------------------------------------------------------------
    def update_trend(self, symbol: str, classification: str, signal_data: Dict):
        try:
            direction = self._determine_trend_direction(classification, signal_data)
            if not direction:
                return False, "UNKNOWN", []

            signal_type = signal_data.get("signal_type", "")
            old_trend = self.current_trend.get(symbol, "UNKNOWN")

            if symbol not in self.trend_pool:
                self.trend_pool[symbol] = {"direction": direction, "signals": {}}

            pool = self.trend_pool[symbol]

            # Direction flip
            if pool["direction"] != direction:
                pool["direction"] = direction
                pool["signals"].clear()
                self.trend_signals_count[symbol] = 0

            if signal_type not in pool["signals"]:
                pool["signals"][signal_type] = {
                    "signal_type": signal_type,
                    "timestamp": saudi_time.now(),
                }
                self.trend_signals_count[symbol] = len(pool["signals"])

            required = self.config.get("TREND_CHANGE_THRESHOLD", 2)
            if len(pool["signals"]) < required:
                return False, old_trend, []

            # ✅ Trend confirmed
            self.previous_trend[symbol] = old_trend
            self.current_trend[symbol] = direction
            self.last_reported_trend[symbol] = direction
            self.trend_strength[symbol] += 1

            updated_at = saudi_time.now().isoformat()

            if self.redis_enabled:
                self.redis.set_trend(symbol, direction)
                self._redis_set_raw(f"trend:{symbol}:updated_at", updated_at)

                logger.info(
                    f"💾 REDIS | {symbol} → {RED}{direction.upper()}{RESET} | {updated_at} 🇸🇦"
                )

            self.trend_history[symbol].append({
                "old": old_trend,
                "new": direction,
                "time": updated_at
            })

            pool["signals"].clear()
            return old_trend != direction, old_trend, []

        except Exception as e:
            self._handle_error("update_trend failed", e)
            return False, "UNKNOWN", []

    # ------------------------------------------------------------------
    # 🧠 Direction Resolver
    # ------------------------------------------------------------------
    def _determine_trend_direction(self, classification: str, signal_data: Dict) -> Optional[str]:
        text = signal_data.get("signal_type", "").lower()
        if "bull" in text or "up" in text:
            return "bullish"
        if "bear" in text or "down" in text:
            return "bearish"
        return None

    # ------------------------------------------------------------------
    # 🔴 Redis Raw Access (NO set() assumption)
    # ------------------------------------------------------------------
    def _redis_set_raw(self, key: str, value: str):
        try:
            if hasattr(self.redis, "client"):
                self.redis.client.set(key, value)
            elif hasattr(self.redis, "redis"):
                self.redis.redis.set(key, value)
        except Exception as e:
            self._handle_error(f"Redis raw set failed: {key}", e)

    def get_trend_updated_at(self, symbol: str) -> Optional[str]:
        try:
            if not self.redis_enabled:
                return None

            if hasattr(self.redis, "client"):
                v = self.redis.client.get(f"trend:{symbol}:updated_at")
            elif hasattr(self.redis, "redis"):
                v = self.redis.redis.get(f"trend:{symbol}:updated_at")
            else:
                return None

            return v.decode() if v else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 🔁 Redis Load on Startup
    # ------------------------------------------------------------------
    def _load_trends_from_redis(self):
        try:
            trends = self.redis.get_all_trends()
            for symbol, trend in trends.items():
                self.current_trend[symbol] = trend
                logger.info(
                    f"🔁 REDIS LOAD | {symbol} → {RED}{trend.upper()}{RESET} 🇸🇦"
                )
        except Exception as e:
            self._handle_error("Redis load failed", e)

    # ------------------------------------------------------------------
    # 🧹 Cleanup
    # ------------------------------------------------------------------
    def cleanup_memory(self):
        now = saudi_time.now()
        one_week_ago = now - timedelta(days=7)

        for symbol, history in self.trend_history.items():
            while history and history[0]["time"] < one_week_ago.isoformat():
                history.popleft()

    # ------------------------------------------------------------------
    # ❌ Errors
    # ------------------------------------------------------------------
    def _handle_error(self, msg, exc=None):
        logger.error(f"{msg}: {exc}")
        self._error_log.append({
            "time": saudi_time.now().isoformat(),
            "error": f"{msg}: {exc}"
        })

    def get_error_log(self):
        return list(self._error_log)
