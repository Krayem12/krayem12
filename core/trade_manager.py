# core/trade_manager.py
# =========================================================
# FINAL TradeManager – FULLY COMPATIBLE WITH GroupManager
# =========================================================

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


class TradeManager:
    """
    TradeManager FINAL
    - يدير الصفقات
    - يدعم GroupManager
    - يدعم Redis
    """

    def __init__(self, config: dict):
        self.config = config

        self.trade_lock = threading.Lock()

        # 🔹 الصفقات المفتوحة
        self.active_trades: Dict[str, dict] = {}

        # 🔹 عدادات
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0

        # 🔹 Metrics
        self.metrics = {
            "trades_opened": 0,
            "trades_closed": 0,
        }

        logger.info("✅ TradeManager FINAL initialized – Saudi Time 🇸🇦")

    # ==========================================================
    # 🔧 REQUIRED BY group_manager.py (❗ VERY IMPORTANT)
    # ==========================================================
    def count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """
        ❗❗ هذه الدالة مطلوبة حرفيًا
        group_manager يستدعيها بهذا التوقيع
        """
        try:
            with self.trade_lock:
                return sum(
                    1
                    for trade in self.active_trades.values()
                    if isinstance(trade, dict)
                    and trade.get("symbol") == symbol
                    and trade.get("mode") == mode_key
                )
        except Exception as e:
            logger.error(f"count_trades_by_mode failed: {e}")
            return 0

    def get_active_trades_count(self, symbol: str) -> int:
        try:
            with self.trade_lock:
                return sum(
                    1
                    for trade in self.active_trades.values()
                    if trade.get("symbol") == symbol
                )
        except Exception:
            return 0

    # ==========================================================
    # ➕ OPEN TRADE
    # ==========================================================
    def open_trade(self, symbol: str, side: str, mode: str, group: str):
        with self.trade_lock:
            trade_id = f"{symbol}-{self.total_trade_counter}"
            self.total_trade_counter += 1

            self.active_trades[trade_id] = {
                "symbol": symbol,
                "side": side,
                "mode": mode,
                "group": group,
                "opened_at": saudi_time.now().isoformat(),
            }

            self.symbol_trade_count[symbol] += 1
            self.metrics["trades_opened"] += 1

            logger.info(
                f"📈 OPEN TRADE | {symbol} | {side.upper()} | {mode} | {group}"
            )

    # ==========================================================
    # 🔚 EXIT SIGNAL (Compatibility)
    # ==========================================================
    def handle_exit_signal(self, symbol: str, reason: str = "") -> int:
        closed = 0
        with self.trade_lock:
            to_close = [
                trade_id
                for trade_id, trade in list(self.active_trades.items())
                if trade.get("symbol") == symbol
            ]

            for trade_id in to_close:
                self.active_trades.pop(trade_id, None)
                closed += 1

        if closed:
            self.metrics["trades_closed"] += closed
            logger.info(f"🔚 Closed {closed} trades for {symbol} | {reason}")

        return closed
