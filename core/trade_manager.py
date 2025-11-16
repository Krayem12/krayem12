# core/trade_manager.py
import logging
from datetime import datetime
from typing import Dict, List, Optional
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

class TradeManager:
    """
    🎯 نظام اتجاه بإشارتين فقط – النسخة النهائية
    ✔️ لا TTL – لا وقت
    ✔️ إشارتان مختلفتان = اتجاه جديد
    ✔️ الإشارة المعاكسة = Reset فوري
    ✔️ لا إرسال للتلقرام إلا عند تغيير الاتجاه فعليًا
    ✔️ يعيد الإشارات بصيغة dictionaries لتوافق webhook_handler بالكامل
    """

    def __init__(self, config):
        self.config = config

        # Locks
        self.trade_lock = threading.RLock()

        # Trades
        self.active_trades = {}
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0
        self.metrics = {"trades_opened": 0, "trades_closed": 0}

        # Trend state
        self.current_trend = {}
        self.last_reported_trend = {}

        # 🟩 Pool structure:
        #
        # trend_pool[symbol] = {
        #     "direction": "bullish",
        #     "signals": {
        #         "bullish_tracer": {"signal_type": "...", "direction": "..."},
        #         "bullish_moneyflow_above_50": {"signal_type": "...", "direction": "..."}
        #     }
        # }
        #
        self.trend_pool = {}

        self.group_manager = None
        self.notification_manager = None
        self._error_log = []

        logger.info("🎯 TradeManager Loaded: 2-Signal Trend System with Change-Only Notifications")

    # ----------------------------------------------------------
    # Linking Managers
    # ----------------------------------------------------------
    def set_group_manager(self, gm):
        self.group_manager = gm

    def set_notification_manager(self, nm):
        self.notification_manager = nm

    # ----------------------------------------------------------
    # Open Trade
    # ----------------------------------------------------------
    def open_trade(self, symbol, direction, strategy_type="GROUP1", mode_key="TRADING_MODE"):
        with self.trade_lock:
            try:
                if len(self.active_trades) >= self.config["MAX_OPEN_TRADES"]:
                    return False

                if self.symbol_trade_count[symbol] >= self.config["MAX_TRADES_PER_SYMBOL"]:
                    return False

                self.total_trade_counter += 1
                trade_id = f"{symbol}_{mode_key}_{self.total_trade_counter}_{datetime.now().strftime('%H%M%S')}"

                self.active_trades[trade_id] = {
                    "symbol": symbol,
                    "side": direction,
                    "strategy_type": strategy_type,
                    "mode_key": mode_key,
                    "trade_type": self._get_trade_type(mode_key),
                    "opened_at": datetime.now().isoformat(),
                    "trade_id": trade_id,
                }

                self.symbol_trade_count[symbol] += 1
                self.metrics["trades_opened"] += 1

                logger.info(f"🚀 فتح صفقة: {symbol} - {direction}")
                return True

            except Exception as e:
                self._handle_error("💥 خطأ في فتح الصفقة", e)
                return False

    # ----------------------------------------------------------
    # Close Trade
    # ----------------------------------------------------------
    def close_trade(self, trade_id):
        with self.trade_lock:
            try:
                if trade_id not in self.active_trades:
                    return False

                symbol = self.active_trades[trade_id]["symbol"]

                if self.symbol_trade_count[symbol] > 0:
                    self.symbol_trade_count[symbol] -= 1

                del self.active_trades[trade_id]
                self.metrics["trades_closed"] += 1

                logger.info(f"❎ إغلاق الصفقة: {trade_id}")
                return True

            except Exception as e:
                self._handle_error("💥 خطأ في إغلاق الصفقة", e)
                return False

    # ----------------------------------------------------------
    # Trend System — 2 signals only
    # ----------------------------------------------------------
    def update_trend(self, symbol: str, classification: str, signal_data: Dict):
        """
        ✔️ الإشارة الأولى → تخزين
        ✔️ الإشارة الثانية (من نفس الاتجاه ونوع مختلف) → اتجاه جديد
        ✔️ الإشارة المعاكسة → Reset وبداية تجميع جديد
        ✔️ لا إرسال للتلقرام إلا إذا تغير الاتجاه فعليًا فقط
        """
        try:
            signal_type = signal_data["signal_type"]
            direction = "bullish" if "bullish" in signal_type.lower() else "bearish"

            pool = self.trend_pool.get(symbol)

            # 🟩 الحالة الأولى: لا يوجد مخزن
            if pool is None:
                self.trend_pool[symbol] = {
                    "direction": direction,
                    "signals": {
                        signal_type: {
                            "signal_type": signal_type,
                            "direction": direction
                        }
                    }
                }
                logger.debug(f"🟩 تخزين أول إشارة اتجاه {direction} لـ {symbol}")
                return False, None, []

            # 🟥 إشارة معاكسة → Reset كامل ثم تخزين الإشارة الجديدة
            if pool["direction"] != direction:
                logger.debug(f"🔄 Reset بسبب إشارة معاكسة: {pool['direction']} → {direction}")
                self._reset_trend_pool(symbol)

                self.trend_pool[symbol] = {
                    "direction": direction,
                    "signals": {
                        signal_type: {
                            "signal_type": signal_type,
                            "direction": direction
                        }
                    }
                }

                return False, None, []

            # 🟩 نفس الاتجاه → أضف نوع جديد من الإشارات
            if signal_type not in pool["signals"]:
                pool["signals"][signal_type] = {
                    "signal_type": signal_type,
                    "direction": direction
                }
                logger.debug(f"➕ إضافة إشارة جديدة: {signal_type}")
            else:
                logger.debug(f"🔁 إشارة مكررة: {signal_type}")
                return False, None, []

            # ------------------------------------------------------
            # 🟩 تحقق الاتجاه — إشارتين مختلفتين = اتجاه مكتمل
            # ------------------------------------------------------
            if len(pool["signals"]) >= 2:
                new_trend = direction
                old_trend = self.current_trend.get(symbol)

                self.current_trend[symbol] = new_trend

                used_signals = list(pool["signals"].values())

                logger.info(f"📈 اتجاه مكتمل: {symbol} → {new_trend}")

                # Reset بعد الاتجاه
                self._reset_trend_pool(symbol)

                # ------------------------------------------------------
                # 🔥 شرط أبو ريان:
                # لا يرسل للتلقرام إلا إذا تغير الاتجاه فعليًا
                # ------------------------------------------------------
                if old_trend == new_trend:
                    logger.debug(
                        f"🔕 تجاهل إشعار — الاتجاه لم يتغير: {symbol} = {new_trend}"
                    )
                    return False, old_trend, []

                # الاتجاه تغير فعليًا → يرسل إشعار
                return True, old_trend, used_signals

            # لم يكتمل الاتجاه بعد
            return False, self.current_trend.get(symbol), []

        except Exception as e:
            self._handle_error("💥 خطأ في تحديث الاتجاه", e)
            return False, None, []

    # ----------------------------------------------------------
    def _reset_trend_pool(self, symbol):
        if symbol in self.trend_pool:
            del self.trend_pool[symbol]
        logger.debug(f"🧹 Reset كامل لاتجاه {symbol}")

    # ----------------------------------------------------------
    def close_contrarian_trades(self, symbol, classification):
        trend = self.current_trend.get(symbol)
        if not trend:
            return

        to_close = []
        for trade_id, trade in self.active_trades.items():
            if trade["symbol"] != symbol:
                continue

            if trend == "bullish" and trade["side"] == "sell":
                to_close.append(trade_id)

            if trend == "bearish" and trade["side"] == "buy":
                to_close.append(trade_id)

        for t in to_close:
            self.close_trade(t)

    # ----------------------------------------------------------
    def _get_trade_type(self, mode_key):
        return {
            "TRADING_MODE": "🟦 أساسي",
            "TRADING_MODE1": "🟨 نمط 1",
            "TRADING_MODE2": "🟪 نمط 2",
        }.get(mode_key, "🟦 أساسي")

    def _handle_error(self, msg, exc=None):
        full = f"{msg}: {exc}" if exc else msg
        logger.error(full)
        self._error_log.append(full)

    def get_error_log(self):
        return self._error_log
