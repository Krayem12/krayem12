# core/trade_manager.py
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple  # أضفت Tuple هنا
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

class TradeManager:
    """🎯 مدير الصفقات مع تحسينات الأداء ومعالجة الأخطاء"""

    def __init__(self, config):
        self.config = config
        self.trade_lock = threading.RLock()
        
        # ✅ هياكل البيانات المحسنة
        self.active_trades = {}
        self.current_trend = {}
        self.previous_trend = {}
        self.last_reported_trend = {}
        self.symbol_trade_count = defaultdict(int)
        self.total_trade_counter = 0
        self.metrics = {"trades_opened": 0, "trades_closed": 0}
        self.group_manager = None
        self.notification_manager = None
        self._last_trend_notification = {}
        self._error_log = []

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append(full_error)

    def set_group_manager(self, group_manager) -> None:
        """تعيين GroupManager"""
        self.group_manager = group_manager

    def set_notification_manager(self, notification_manager) -> None:
        """تعيين NotificationManager"""
        self.notification_manager = notification_manager

    def open_trade(self, symbol: str, direction: str, strategy_type: str = "GROUP1", 
                   mode_key: str = "TRADING_MODE") -> bool:
        """فتح صفقة جديدة مع تحسينات الأداء"""
        with self.trade_lock:
            try:
                # التحقق من الحدود
                if len(self.active_trades) >= self.config['MAX_OPEN_TRADES']:
                    logger.warning(f"❌ تجاوز الحد الأقصى للصفقات المفتوحة")
                    return False

                if self.symbol_trade_count[symbol] >= self.config['MAX_TRADES_PER_SYMBOL']:
                    logger.warning(f"❌ تجاوز الحد الأقصى لصفقات الرمز {symbol}")
                    return False

                # إنشاء معرف الصفقة
                self.total_trade_counter += 1
                trade_id = f"{symbol}_{mode_key}_{self.total_trade_counter}_{datetime.now().strftime('%H%M%S')}"
                
                self.active_trades[trade_id] = {
                    "symbol": symbol, 
                    "side": direction,
                    "strategy_type": strategy_type,
                    "mode_key": mode_key,
                    "trade_type": self._get_trade_type(mode_key),
                    "opened_at": datetime.now().isoformat(),
                    "trade_id": trade_id
                }
                
                # تحديث العدادات
                self.symbol_trade_count[symbol] += 1
                self.metrics["trades_opened"] += 1
                
                logger.info(f"🚀 فتح صفقة: {symbol} | النمط: {mode_key} | الاستراتيجية: {strategy_type}")
                return True

            except Exception as e:
                self._handle_error(f"💥 خطأ في فتح الصفقة: {symbol}", e)
                return False

    def close_trade(self, trade_id: str) -> bool:
        """إغلاق صفقة بشكل آمن"""
        with self.trade_lock:
            try:
                if trade_id not in self.active_trades:
                    logger.warning(f"⚠️ الصفقة غير موجودة: {trade_id}")
                    return False

                symbol = self.active_trades[trade_id]["symbol"]
                
                # تحديث العداد
                if self.symbol_trade_count[symbol] > 0:
                    self.symbol_trade_count[symbol] -= 1
                else:
                    self.symbol_trade_count[symbol] = 0
                
                del self.active_trades[trade_id]
                self.metrics["trades_closed"] += 1
                
                logger.debug(f"✅ تم إغلاق الصفقة: {trade_id}")
                return True

            except Exception as e:
                self._handle_error(f"💥 خطأ في إغلاق الصفقة: {trade_id}", e)
                return False

    def update_trend(self, symbol: str, classification: str, signal_data: Dict) -> Tuple[bool, Optional[str]]:
        """تحديث اتجاه السهم"""
        try:
            direction = "bullish" if "bullish" in signal_data['signal_type'].lower() else "bearish"
            
            # حفظ الاتجاه السابق
            old_trend = self.current_trend.get(symbol)
            self.previous_trend[symbol] = old_trend
            
            # تحديث الاتجاه الحالي
            self.current_trend[symbol] = direction
            
            logger.debug(f"📈 تم تحديث الاتجاه: {symbol} -> {direction.upper()}")
            
            # إغلاق الصفقات المخالفة
            self.close_contrarian_trades(symbol, classification)
            
            # التحقق من الإبلاغ عن التغيير
            return self._should_report_trend_change(symbol, direction, old_trend), old_trend

        except Exception as e:
            self._handle_error(f"💥 خطأ في تحديث الاتجاه: {symbol}", e)
            return False, None

    def _should_report_trend_change(self, symbol: str, new_trend: str, old_trend: Optional[str]) -> bool:
        """التحقق من وجوب الإبلاغ عن تغيير الاتجاه"""
        if old_trend is None:
            self.last_reported_trend[symbol] = new_trend
            return True
            
        last_reported = self.last_reported_trend.get(symbol)
        if last_reported != new_trend:
            self.last_reported_trend[symbol] = new_trend
            return True
            
        return False

    def close_contrarian_trades(self, symbol: str, classification: str) -> None:
        """إغلاق الصفقات المخالفة للاتجاه"""
        if symbol not in self.current_trend:
            return

        trend = self.current_trend[symbol]
        trades_to_close = []

        for trade_id, trade in self.active_trades.items():
            if trade["symbol"] == symbol:
                if (trend == "bullish" and trade["side"] == "sell") or \
                   (trend == "bearish" and trade["side"] == "buy"):
                    trades_to_close.append(trade_id)

        for trade_id in trades_to_close:
            self.close_trade(trade_id)

    def get_active_trades_count(self, symbol: Optional[str] = None) -> int:
        """الحصول على عدد الصفقات النشطة"""
        if symbol:
            return self.symbol_trade_count.get(symbol, 0)
        return len(self.active_trades)

    def _get_trade_type(self, mode_key: str) -> str:
        """تحديد نوع الصفقة"""
        trade_types = {
            'TRADING_MODE': '🟦 أساسي',
            'TRADING_MODE1': '🟨 نمط 1', 
            'TRADING_MODE2': '🟪 نمط 2'
        }
        return trade_types.get(mode_key, '🟦 أساسي')

    def get_performance_metrics(self) -> Dict:
        """الحصول على مقاييس الأداء"""
        return {
            'active_trades': len(self.active_trades),
            'total_opened': self.metrics["trades_opened"],
            'total_closed': self.metrics["trades_closed"],
            'symbol_counts': dict(self.symbol_trade_count),
            'error_count': len(self._error_log)
        }

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()