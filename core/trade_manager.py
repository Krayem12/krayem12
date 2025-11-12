# core/trade_manager.py
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

class TradeManager:
    def __init__(self, config):
        self.config = config
        
        # ✅ قائمة الصفقات النشطة
        self.active_trades = {}

        # ✅ الاتجاه الحالي لكل رمز
        self.current_trend = {}

        # ✅ الاتجاه السابق لكل رمز (للعرض فقط)
        self.previous_trend = {}

        # ✅ آخر اتجاه تم الإبلاغ عنه لكل رمز
        self.last_reported_trend = {}

        # 🆕 إضافة عداد منفصل لكل رمز
        self.symbol_trade_count = {}
        self.total_trade_counter = 0  # عداد إجمالي

        # ✅ عداد أو مقاييس تشغيل النظام إن وجدت
        self.metrics = {
            "trades_opened": 0,
            "trades_closed": 0
        }

        # 🆕 مرجع إلى GroupManager (سيتم تعيينه لاحقاً)
        self.group_manager = None

        # 🆕 مرجع إلى NotificationManager (سيتم تعيينه لاحقاً)
        self.notification_manager = None

        # 🛠️ الإصلاح: خاصية جديدة لمنع الإشعارات المكررة
        self._last_trend_notification = {}

    def set_group_manager(self, group_manager):
        """🆕 تعيين GroupManager للوصول المتبادل"""
        self.group_manager = group_manager

    def set_notification_manager(self, notification_manager):
        """🆕 تعيين NotificationManager للإشعارات"""
        self.notification_manager = notification_manager

    def update_trend(self, symbol, classification, signal_data):
        """تحديث اتجاه السهم بدون حذف الإشارات المخالفة"""
        direction = "bullish" if "bullish" in signal_data['signal_type'].lower() else "bearish"
        
        # 🆕 حفظ الاتجاه السابق قبل التحديث
        old_trend = self.current_trend.get(symbol)
        self.previous_trend[symbol] = old_trend
        
        # تحديث الاتجاه الحالي
        self.current_trend[symbol] = direction
        
        logger.debug(f"📈 تم تحديث الاتجاه: {symbol} -> {direction.upper()} (سابقاً: {old_trend})")
        
        # التحقق مما إذا كان التغيير يستحق الإبلاغ
        should_report = self._should_report_trend_change(symbol, direction, old_trend)
        
        # 🚫 تم إزالة تنظيف الإشارات المخالفة
        
        # إغلاق الصفقات المخالفة للاتجاه الجديد
        self.close_contrarian_trades(symbol, classification)
        
        # 🆕 إرسال إشعار بسيط عن تغيير الاتجاه
        if should_report and self.notification_manager:
            self._send_simple_trend_notification(symbol, direction, old_trend, signal_data)
        
        return should_report, old_trend

    def _send_simple_trend_notification(self, symbol: str, new_trend: str, old_trend: str, signal_data: Dict):
        """🆕 إرسال إشعار بسيط عن تغيير الاتجاه"""
        try:
            from notifications.message_formatter import MessageFormatter
            
            # 🛠️ الإصلاح: التحقق مما إذا كان قد تم الإرسال مسبقاً
            notification_key = f"{symbol}_{new_trend}"
            current_time = datetime.now()
            
            if (notification_key in self._last_trend_notification and 
                (current_time - self._last_trend_notification[notification_key]).total_seconds() < 10):
                logger.debug(f"🔇 منع إشعار مكرر لـ {symbol} - {new_trend}")
                return
            
            # 🆕 استخدام الدالة الأساسية
            try:
                trend_message = MessageFormatter.format_trend_message(
                    signal_data, 
                    new_trend,
                    old_trend or "UNKNOWN"
                )
            except AttributeError:
                # 🆕 إذا فشلت، استخدم الدالة المبسطة
                logger.debug("⚠️ استخدام الدالة البديلة format_simple_trend_message")
                trend_message = MessageFormatter.format_simple_trend_message(
                    symbol=symbol,
                    new_trend=new_trend,
                    old_trend=old_trend or "UNKNOWN",
                    trigger_signal=signal_data['signal_type']
                )
            
            # إرسال الإشعار
            if self.notification_manager and self.notification_manager.should_send_message('trend'):
                self.notification_manager.send_notifications(trend_message, 'trend')
                
                # 🛠️ حفظ معلومات آخر إشعار
                self._last_trend_notification[notification_key] = current_time
                
                logger.debug(f"📤 تم إرسال إشعار تغيير الاتجاه البسيط لـ {symbol}")
            else:
                logger.debug(f"🔕 إشعارات الاتجاه معطلة - لم يتم إرسال الإشعار لـ {symbol}")
                
        except Exception as e:
            logger.error(f"⚠️ خطأ في إرسال إشعار تغيير الاتجاه البسيط: {e}")

    def _should_report_trend_change(self, symbol, new_trend, old_trend):
        """التحقق مما إذا كان تغيير الاتجاه يستحق الإبلاغ"""
        # إذا لم يكن هناك اتجاه سابق، نبلغ عن التغيير
        if old_trend is None:
            self.last_reported_trend[symbol] = new_trend
            return True
            
        # إذا كان الاتجاه الجديد مختلف عن الأخير الذي تم الإبلاع عنه
        last_reported = self.last_reported_trend.get(symbol)
        if last_reported != new_trend:
            self.last_reported_trend[symbol] = new_trend
            logger.debug(f"🔄 تغيير حقيقي في الاتجاه: {symbol} من {last_reported} إلى {new_trend}")
            return True
            
        # إذا كان نفس الاتجاه، لا نبلغ
        logger.debug(f"🔁 نفس الاتجاه - لا إشعار: {symbol} -> {new_trend}")
        return False

    def get_previous_trend(self, symbol):
        """الحصول على الاتجاه السابق للرمز"""
        return self.previous_trend.get(symbol, "UNKNOWN")

    def close_contrarian_trades(self, symbol, classification):
        """إغلاق الصفقات المخالفة مباشرة عند تغيير الاتجاه"""
        if symbol not in self.current_trend:
            return

        trend = self.current_trend[symbol]
        logger.debug(f"🔍 فحص الصفقات المخالفة لـ {symbol} - الاتجاه: {trend}")

        trades_to_close = []
        for trade_id, trade in self.active_trades.items():
            if trade["symbol"] == symbol:
                if trend == "bullish" and trade["side"] == "sell":
                    trades_to_close.append(trade_id)
                    logger.debug(f"🔴 إغلاق صفقة بيع مخالفة للاتجاه: {trade_id}")
                elif trend == "bearish" and trade["side"] == "buy":
                    trades_to_close.append(trade_id)
                    logger.debug(f"🔴 إغلاق صفقة شراء مخالفة للاتجاه: {trade_id}")

        # إغلاق الصفقات المخالفة
        for trade_id in trades_to_close:
            self.close_trade(trade_id)

    def open_trade(self, symbol, direction, strategy_type="GROUP1", mode_key="TRADING_MODE"):
        """فتح صفقة جديدة مع إضافة نوع الاستراتيجية والنمط"""
        # التحقق من الحد الأقصى للصفقات الإجمالي
        if len(self.active_trades) >= self.config['MAX_OPEN_TRADES']:
            logger.warning(f"❌ تجاوز الحد الأقصى للصفقات المفتوحة: {self.config['MAX_OPEN_TRADES']}")
            return False

        # 🆕 تهيئة عداد الرمز إذا لم يكن موجوداً
        if symbol not in self.symbol_trade_count:
            self.symbol_trade_count[symbol] = 0

        # التحقق من الحد الأقصى للصفقات لكل رمز
        if self.symbol_trade_count[symbol] >= self.config['MAX_TRADES_PER_SYMBOL']:
            logger.warning(f"❌ تجاوز الحد الأقصى لصفقات الرمز {symbol}: {self.config['MAX_TRADES_PER_SYMBOL']}")
            return False

        # 🆕 إصلاح إنشاء معرف الصفقة
        self.total_trade_counter += 1
        trade_id = f"{symbol}_{mode_key}_{self.total_trade_counter}"
        
        self.active_trades[trade_id] = {
            "symbol": symbol, 
            "side": direction,
            "strategy_type": strategy_type,
            "mode_key": mode_key,
            "trade_type": self._get_trade_type(mode_key),
            "opened_at": self._get_current_timestamp()
        }
        
        # 🆕 تحديث العداد بشكل صحيح
        self.symbol_trade_count[symbol] += 1
        self.metrics["trades_opened"] += 1
        
        logger.debug(f"🚀 فتح صفقة: {symbol} | النمط: {mode_key} | الاستراتيجية: {strategy_type} | الاتجاه: {direction.upper()}")
        logger.debug(f"📊 صفقات {symbol}: {self.symbol_trade_count[symbol]}/{self.config['MAX_TRADES_PER_SYMBOL']}")
        logger.debug(f"📊 الصفقات الإجمالية: {len(self.active_trades)}/{self.config['MAX_OPEN_TRADES']}")
        
        return True

    def _get_trade_type(self, mode_key):
        """تحديد نوع الصفقة بناءً على المفتاح"""
        trade_types = {
            'TRADING_MODE': '🟦 أساسي',
            'TRADING_MODE1': '🟨 نمط 1', 
            'TRADING_MODE2': '🟪 نمط 2'
        }
        return trade_types.get(mode_key, '🟦 أساسي')

    def close_trade(self, trade_id):
        """إغلاق صفقة مع تحديث العداد بشكل آمن"""
        if trade_id in self.active_trades:
            symbol = self.active_trades[trade_id]["symbol"]
            mode_key = self.active_trades[trade_id].get("mode_key", "TRADING_MODE")
            strategy_type = self.active_trades[trade_id].get("strategy_type", "GROUP1")
            
            logger.debug(f"✅ تم إغلاق الصفقة: {trade_id} | النمط: {mode_key} | الاستراتيجية: {strategy_type}")
            
            # 🆕 تحديث العداد بشكل آمن
            if symbol in self.symbol_trade_count and self.symbol_trade_count[symbol] > 0:
                self.symbol_trade_count[symbol] -= 1
            else:
                # إذا كان العداد غير موجود أو صفر، نعيد تهيئته
                self.symbol_trade_count[symbol] = 0
            
            del self.active_trades[trade_id]
            self.metrics["trades_closed"] += 1
            
            logger.debug(f"📊 صفقات {symbol} المتبقية: {self.symbol_trade_count.get(symbol, 0)}/{self.config['MAX_TRADES_PER_SYMBOL']}")
            logger.debug(f"📊 الصفقات الإجمالية المتبقية: {len(self.active_trades)}/{self.config['MAX_OPEN_TRADES']}")
            return True
        else:
            logger.warning(f"⚠️ الصفقة غير موجودة: {trade_id}")
            return False

    def handle_exit_signal(self, symbol, signal_type):
        """معالجة إشارات الخروج"""
        logger.debug(f"📤 معالجة إشارة خروج لـ {symbol}: {signal_type}")
        trades_closed = 0
        
        for trade_id, trade in list(self.active_trades.items()):
            if trade["symbol"] == symbol:
                mode_key = trade.get("mode_key", "TRADING_MODE")
                logger.debug(f"📤 إشارة خروج -> إغلاق الصفقة: {trade_id} | النمط: {mode_key}")
                if self.close_trade(trade_id):
                    trades_closed += 1
        
        logger.debug(f"✅ تم إغلاق {trades_closed} صفقة لـ {symbol}")

    def _get_current_timestamp(self):
        """الحصول على الطابع الزمني الحالي"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_active_trades_count(self, symbol=None):
        """الحصول على عدد الصفقات النشطة - إصلاح"""
        if symbol:
            # 🆕 استخدام العداد المخصص للرمز
            return self.symbol_trade_count.get(symbol, 0)
        return len(self.active_trades)

    # 🚫 تم حذف الدوال التالية تماماً:
    # - _clean_contrarian_signals
    # - _clean_contrarian_signals_basic
    # - _send_detailed_trend_notification
    # - _get_remaining_signals
    # - _get_group_display_name