# core/trade_manager.py
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

        # ✅ عداد أو مقاييس تشغيل النظام إن وجدت
        self.metrics = {
            "trades_opened": 0,
            "trades_closed": 0
        }

    def update_trend(self, symbol, classification, signal_data):
        """تحديث اتجاه السهم مع التحقق من الإشعارات"""
        direction = "bullish" if "bullish" in signal_data['signal_type'].lower() else "bearish"
        
        # 🆕 حفظ الاتجاه السابق قبل التحديث
        old_trend = self.current_trend.get(symbol)
        self.previous_trend[symbol] = old_trend  # 🆕 حفظ للعرض
        
        # تحديث الاتجاه الحالي
        self.current_trend[symbol] = direction
        
        print(f"📈 تم تحديث الاتجاه: {symbol} -> {direction.upper()} (سابقاً: {old_trend})")
        
        # التحقق مما إذا كان التغيير يستحق الإبلاغ
        should_report = self._should_report_trend_change(symbol, direction, old_trend)
        
        # إغلاق الصفقات المخالفة للاتجاه الجديد
        self.close_contrarian_trades(symbol, classification)
        
        return should_report, old_trend  # 🆕 إرجاع الاتجاه السابق

    def _should_report_trend_change(self, symbol, new_trend, old_trend):
        """التحقق مما إذا كان تغيير الاتجاه يستحق الإبلاغ"""
        # إذا لم يكن هناك اتجاه سابق، نبلغ عن التغيير
        if old_trend is None:
            self.last_reported_trend[symbol] = new_trend
            return True
            
        # إذا كان الاتجاه الجديد مختلف عن الأخير الذي تم الإبلاغ عنه
        last_reported = self.last_reported_trend.get(symbol)
        if last_reported != new_trend:
            self.last_reported_trend[symbol] = new_trend
            print(f"🔄 تغيير حقيقي في الاتجاه: {symbol} من {last_reported} إلى {new_trend}")
            return True
            
        # إذا كان نفس الاتجاه، لا نبلغ
        print(f"🔁 نفس الاتجاه - لا إشعار: {symbol} -> {new_trend}")
        return False

    def get_previous_trend(self, symbol):
        """الحصول على الاتجاه السابق للرمز"""
        return self.previous_trend.get(symbol, "UNKNOWN")

    def close_contrarian_trades(self, symbol, classification):
        """
        إغلاق الصفقات المخالفة مباشرة عند تغيير الاتجاه
        """
        if symbol not in self.current_trend:
            return

        trend = self.current_trend[symbol]
        print(f"🔍 فحص الصفقات المخالفة لـ {symbol} - الاتجاه: {trend}")

        trades_to_close = []
        for trade_id, trade in self.active_trades.items():
            if trade["symbol"] == symbol:
                if trend == "bullish" and trade["side"] == "sell":
                    trades_to_close.append(trade_id)
                    print(f"🔴 إغلاق صفقة بيع مخالفة للاتجاه: {trade_id}")
                elif trend == "bearish" and trade["side"] == "buy":
                    trades_to_close.append(trade_id)
                    print(f"🔴 إغلاق صفقة شراء مخالفة للاتجاه: {trade_id}")

        # إغلاق الصفقات المخالفة
        for trade_id in trades_to_close:
            self.close_trade(trade_id)

    def open_trade(self, symbol, direction):
        """فتح صفقة جديدة مع التحقق من الحدود"""
        # التحقق من الحد الأقصى للصفقات
        if len(self.active_trades) >= self.config['MAX_OPEN_TRADES']:
            print(f"❌ تجاوز الحد الأقصى للصفقات المفتوحة: {self.config['MAX_OPEN_TRADES']}")
            return False

        # التحقق من الحد الأقصى للصفقات لكل رمز
        symbol_trades = sum(1 for trade in self.active_trades.values() if trade["symbol"] == symbol)
        if symbol_trades >= self.config['MAX_TRADES_PER_SYMBOL']:
            print(f"❌ تجاوز الحد الأقصى لصفقات الرمز {symbol}: {self.config['MAX_TRADES_PER_SYMBOL']}")
            return False

        trade_id = f"{symbol}_{len(self.active_trades)+1}"
        self.active_trades[trade_id] = {
            "symbol": symbol, 
            "side": direction,
            "opened_at": self._get_current_timestamp()
        }
        self.metrics["trades_opened"] += 1
        print(f"🚀 فتح صفقة: {symbol} | الاتجاه: {direction.upper()} | معرف الصفقة: {trade_id}")
        return True

    def close_trade(self, trade_id):
        """إغلاق صفقة"""
        if trade_id in self.active_trades:
            print(f"✅ تم إغلاق الصفقة: {trade_id}")
            del self.active_trades[trade_id]
            self.metrics["trades_closed"] += 1
            return True
        else:
            print(f"⚠️ الصفقة غير موجودة: {trade_id}")
            return False

    def handle_exit_signal(self, symbol, signal_type):
        """معالجة إشارات الخروج"""
        print(f"📤 معالجة إشارة خروج لـ {symbol}: {signal_type}")
        trades_closed = 0
        
        for trade_id, trade in list(self.active_trades.items()):
            if trade["symbol"] == symbol:
                print(f"📤 إشارة خروج -> إغلاق الصفقة: {trade_id}")
                if self.close_trade(trade_id):
                    trades_closed += 1
        
        print(f"✅ تم إغلاق {trades_closed} صفقة لـ {symbol}")

    def _get_current_timestamp(self):
        """الحصول على الطابع الزمني الحالي"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_active_trades_count(self, symbol=None):
        """الحصول على عدد الصفقات النشطة"""
        if symbol:
            return sum(1 for trade in self.active_trades.values() if trade["symbol"] == symbol)
        return len(self.active_trades)