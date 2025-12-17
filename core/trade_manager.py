import logging
from datetime import datetime, timedelta  # ✅ FIX: إضافة timedelta (كان مستخدمًا بدون استيراد)
from typing import Dict, List, Optional
import threading
from collections import defaultdict, deque

# 🛠️ الإصلاح: استيراد صحيح لـ saudi_time
try:
    from utils.time_utils import saudi_time
except ImportError:
    try:
        from ..utils.time_utils import saudi_time
    except ImportError:
        # ✅ بديل إذا فشل الاستيراد
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
        logging.warning("⚠️ استخدام SaudiTime البديل بسبب مشكلة الاستيراد")

logger = logging.getLogger(__name__)

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
    🎯 نظام اتجاه محسّن - بالتوقيت السعودي - الإصدار المصحح
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
        self.previous_trend = {}  # ✅ تم الإضافة
        self.last_reported_trend = {}
        self.trend_strength = {}
        self.trend_signals_count = defaultdict(int)
        self.trend_history = defaultdict(lambda: deque(maxlen=50))  # 🔧 FIXED: حد أقصى 50 سجل

        # Trend pool
        self.trend_pool = {}

        self.group_manager = None
        self.notification_manager = None
        self._error_log = deque(maxlen=500)  # 🔧 FIXED: حد أقصى 500 خطأ

        # 🔗 تكامل Redis لتخزين الاتجاهات بشكل دائم
        self.redis = None
        self.redis_enabled = False
        try:
            if RedisManager is not None:
                self.redis = RedisManager()
                # 🔧 FIXED: القيمة الافتراضية الصحيحة هي False
                self.redis_enabled = getattr(self.redis, "is_enabled", lambda: False)()
        except Exception as e:
            logger.error("⚠️ تعذر تهيئة RedisManager", exc_info=True)
            self.redis = None
            self.redis_enabled = False

        # تحميل الاتجاهات السابقة من Redis عند بدء التشغيل
        if self.redis_enabled:
            self._load_trends_from_redis()

        logger.info("🎯 TradeManager المصحح جاهز: Enhanced Trend System - التوقيت السعودي 🇸🇦")

    def set_group_manager(self, gm):
        self.group_manager = gm

    def set_notification_manager(self, nm):
        self.notification_manager = nm

    def open_trade(self, symbol, direction, strategy_type="GROUP1", mode_key="TRADING_MODE"):
        """🔧 FIXED: فتح صفقة مع تحديث العدادات فقط بعد النجاح"""
        with self.trade_lock:
            try:
                # 🔴 استخدام القيم من الإعدادات فقط بدون افتراضيات
                max_open_trades = self.config.get("MAX_OPEN_TRADES", 20)
                max_per_symbol = self.config.get("MAX_TRADES_PER_SYMBOL", 20)

                # التحقق من الحدود العالمية
                current_total = len(self.active_trades)
                if current_total >= max_open_trades:
                    logger.warning(f"🚫 وصل الحد الأقصى للصفقات المفتوحة: {current_total}/{max_open_trades}")
                    return False

                # 🔴 استخدام العداد المخصص بدقة
                current_symbol_count = self.symbol_trade_count.get(symbol, 0)
                if current_symbol_count >= max_per_symbol:
                    logger.warning(f"🚫 وصل الحد الأقصى للصفقات للرمز {symbol}: {current_symbol_count}/{max_per_symbol}")
                    return False

                # إنشاء معرف فريد للصفقة بالتوقيت السعودي
                self.total_trade_counter += 1
                timestamp = saudi_time.now().strftime('%Y%m%d_%H%M%S_%f')
                trade_id = f"{symbol}_{mode_key}_{self.total_trade_counter}_{timestamp}"

                # 🔧 FIXED: إنشاء بيانات الصفقة أولاً
                trade_data = {
                    "symbol": symbol,
                    "side": direction,
                    "strategy_type": strategy_type,
                    "mode_key": mode_key,
                    "trade_type": self._get_trade_type(mode_key),
                    "opened_at": saudi_time.now().isoformat(),
                    "trade_id": trade_id,
                    "timezone": "Asia/Riyadh 🇸🇦"
                }

                # محاولة فتح الصفقة (يمكن إضافة منطق تنفيذ حقيقي هنا)
                open_success = self._execute_trade_open(trade_data)

                if not open_success:
                    logger.error(f"❌ فشل تنفيذ فتح الصفقة: {symbol}")
                    return False

                # 🔧 FIXED: فقط بعد نجاح فتح الصفقة نقوم بالتحديث
                self.active_trades[trade_id] = trade_data
                self.symbol_trade_count[symbol] = current_symbol_count + 1
                self.metrics["trades_opened"] += 1

                logger.info(f"✅ فتح صفقة: {symbol} - {direction} - {strategy_type} (العدد: {self.symbol_trade_count[symbol]}) - التوقيت السعودي 🇸🇦")
                return True

            except Exception as e:
                self._handle_error("💥 خطأ في فتح الصفقة", e)
                return False

    def _execute_trade_open(self, trade_data: Dict) -> bool:
        """🔧 NEW: تنفيذ فتح الصفقة الفعلي (يمكن تخصيصه حسب الوسيط)"""
        try:
            # هنا يمكن إضافة منطق الاتصال بالوسيط
            # للآن نعيد True كنموذج
            logger.debug(f"📤 تنفيذ فتح الصفقة: {trade_data['symbol']} - {trade_data['side']}")
            return True
        except Exception as e:
            self._handle_error("💥 خطأ في تنفيذ فتح الصفقة", e)
            return False

    def close_trade(self, trade_id):
        with self.trade_lock:
            try:
                if trade_id not in self.active_trades:
                    logger.warning(f"⚠️ محاولة إغلاق صفقة غير موجودة: {trade_id}")
                    return False

                symbol = self.active_trades[trade_id]["symbol"]
                del self.active_trades[trade_id]

                # 🔴 تحديث العداد مع التحقق من الوجود
                if symbol in self.symbol_trade_count:
                    self.symbol_trade_count[symbol] = max(0, self.symbol_trade_count[symbol] - 1)
                else:
                    logger.warning(f"⚠️ رمز غير موجود في العدادات: {symbol}")

                self.metrics["trades_closed"] += 1

                logger.info(f"❎ إغلاق الصفقة: {trade_id} - التوقيت السعودي 🇸🇦")
                return True

            except Exception as e:
                self._handle_error("💥 خطأ في إغلاق الصفقة", e)
                return False

    def handle_exit_signal(self, symbol: str, signal_type: str) -> int:
        """🎯 معالجة إشارات الخروج وإرجاع عدد الصفقات المغلقة"""
        with self.trade_lock:
            try:
                trades_to_close = []
                for trade_id, trade in self.active_trades.items():
                    if trade.get('symbol') == symbol:
                        trades_to_close.append(trade_id)

                closed_count = 0
                for trade_id in trades_to_close:
                    if self.close_trade(trade_id):
                        closed_count += 1

                logger.info(f"🚪 تم إغلاق {closed_count} صفقة لـ {symbol} بناءً على إشارة خروج: {signal_type} - التوقيت السعودي 🇸🇦")
                return closed_count
            except Exception as e:
                self._handle_error(f"💥 خطأ في معالجة إشارة الخروج لـ {symbol}", e)
                return 0

    def update_trend(self, symbol: str, classification: str, signal_data: Dict):
        """🎯 نظام اتجاه محسّن ومصحح بالكامل بالتوقيت السعودي"""
        try:
            direction = self._determine_trend_direction(classification, signal_data)
            if not direction:
                logger.warning(f"⚠️ لا يمكن تحديد اتجاه للإشارة: {classification} - {signal_data.get('signal_type')}")
                return False, "UNKNOWN", []

            signal_type = signal_data["signal_type"]
            logger.info(f"🎯 معالجة إشارة اتجاه لـ {symbol}: {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")

            # 🔧 FIXED: تهيئة المخزن إذا لم يكن موجوداً
            if symbol not in self.trend_pool:
                self.trend_pool[symbol] = {
                    "direction": direction,
                    "signals": {}
                }

            pool = self.trend_pool[symbol]
            old_trend = self.current_trend.get(symbol, "UNKNOWN")

            # 🔄 إعادة التعيين إذا كانت الإشارة معاكسة
            if pool["direction"] != direction:
                logger.info(f"🔄 تغيير اتجاه: {symbol} من {pool['direction']} إلى {direction} - التوقيت السعودي 🇸🇦")
                pool["direction"] = direction
                pool["signals"] = {}
                self.trend_signals_count[symbol] = 0

            # ➕ إضافة الإشارة الجديدة
            if signal_type not in pool["signals"]:
                pool["signals"][signal_type] = {
                    "signal_type": signal_type,
                    "direction": direction,
                    "classification": classification,
                    "timestamp": saudi_time.now(),
                    "timezone": "Asia/Riyadh 🇸🇦"
                }
                # 🔧 FIXED: التحقق من وجود signals قبل حساب الطول
                if pool.get("signals"):
                    self.trend_signals_count[symbol] = len(pool["signals"])
                logger.info(f"➕ إضافة إشارة جديدة: {signal_type} (الإجمالي: {self.trend_signals_count[symbol]}) - التوقيت السعودي 🇸🇦")

            # ✅ التحقق من اكتمال الاتجاه
            required_signals = self.config.get('TREND_CHANGE_THRESHOLD', 2)

            # 🔧 FIXED: التحقق من وجود signals وحساب الطول بشكل آمن
            current_signals_count = len(pool.get("signals", {}))

            if current_signals_count >= required_signals:
                new_trend = direction
                trend_changed = old_trend != new_trend

                self.current_trend[symbol] = new_trend
                self.last_reported_trend[symbol] = new_trend

                # ✅ FIX: عند تغيّر الاتجاه فعلياً، أغلق الصفقات المفتوحة للرمز لبدء دورة جديدة
                if trend_changed:
                    try:
                        self.handle_exit_signal(symbol, "TREND_CHANGE")
                    except Exception as e:
                        self._handle_error(f"⚠️ خطأ في إغلاق الصفقات عند تغيّر الاتجاه لـ {symbol}", e)

                # حفظ الاتجاه بشكل دائم في Redis + ✅ LOG واضح
                if self.redis_enabled:
                    try:
                        self.redis.set_trend(symbol, new_trend)

                        # ✅ المطلوب: Log واضح عند الحفظ
                        logger.info(
                            f"💾 تم حفظ الاتجاه في Redis | Symbol={symbol} | Trend={new_trend.upper()} | Time={saudi_time.now().isoformat()} 🇸🇦"
                        )

                    except Exception as e:
                        self._handle_error(f"⚠️ خطأ في حفظ الاتجاه في Redis لـ {symbol}", e)

                used_signals = list(pool.get("signals", {}).values())

                # 📝 تسجيل تاريخ الاتجاه
                self.trend_history[symbol].append({
                    'timestamp': saudi_time.now(),
                    'old_trend': old_trend,
                    'new_trend': new_trend,
                    'signals_used': [s.get('signal_type', '') for s in used_signals],
                    'timezone': 'Asia/Riyadh 🇸🇦'
                })

                if trend_changed:
                    logger.info(f"📈 تغيير اتجاه مكتمل: {symbol} → {new_trend} ({current_signals_count} إشارات) - التوقيت السعودي 🇸🇦")
                else:
                    logger.info(f"📊 تأكيد اتجاه: {symbol} → {new_trend} ({current_signals_count} إشارات) - التوقيت السعودي 🇸🇦")

                # 🧹 إعادة التعيين بعد اكتمال الاتجاه
                pool["signals"] = {}
                self.trend_strength[symbol] = current_signals_count

                return trend_changed, old_trend, used_signals

            # ⏳ لم يكتمل الاتجاه بعد
            return False, old_trend, []

        except Exception as e:
            self._handle_error("💥 خطأ في تحديث الاتجاه", e)
            return False, "UNKNOWN", []

    def _determine_trend_direction(self, classification: str, signal_data: Dict) -> Optional[str]:
        """🎯 تحديد اتجاه محسّن مع التعامل مع الحالات غير المعروفة"""
        try:
            signal_type = signal_data.get('signal_type', '').lower().strip()
            classification_lower = classification.lower().strip()

            # خريطة قرار واضحة للاتجاهات
            direction_map = {
                # إشارات صاعدة
                'entry_bullish': 'bullish',
                'entry_bullish1': 'bullish',
                'group3_bullish': 'bullish',
                'group4_bullish': 'bullish',
                'group5_bullish': 'bullish',

                # إشارات هابطة
                'entry_bearish': 'bearish',
                'entry_bearish1': 'bearish',
                'group3_bearish': 'bearish',
                'group4_bearish': 'bearish',
                'group5_bearish': 'bearish',

                # إشارات الاتجاه
                'trend': self._extract_direction_from_signal(signal_type),
                'trend_confirm': self._extract_direction_from_signal(signal_type)
            }

            # البحث في خريطة التصنيف أولاً
            if classification_lower in direction_map:
                direction = direction_map[classification_lower]
                if direction:
                    return direction

            # إذا لم يتم العثور، البحث في نص الإشارة
            return self._extract_direction_from_signal(signal_type)

        except Exception as e:
            logger.error(f"💥 خطأ في تحديد الاتجاه: {e}")
            return None

    def _extract_direction_from_signal(self, signal_type: str) -> Optional[str]:
        """استخراج الاتجاه من نص الإشارة"""
        if not signal_type:
            return None

        bullish_keywords = ['bullish', 'up', 'buy', 'long', 'bull', 'rise', 'increase']
        bearish_keywords = ['bearish', 'down', 'sell', 'short', 'bear', 'fall', 'decrease']

        if any(keyword in signal_type for keyword in bullish_keywords):
            return 'bullish'
        if any(keyword in signal_type for keyword in bearish_keywords):
            return 'bearish'

        return None

    def _reset_trend_pool(self, symbol):
        """إعادة تعيين مخزن الاتجاه"""
        if symbol in self.trend_pool:
            del self.trend_pool[symbol]
        logger.debug(f"🧹 Reset كامل لاتجاه {symbol} - التوقيت السعودي 🇸🇦")

    def close_contrarian_trades(self, symbol, classification):
        """إغلاق الصفقات المخالفة للاتجاه"""
        trend = self.current_trend.get(symbol)
        if not trend:
            return

        to_close = []
        for trade_id, trade in self.active_trades.items():
            if trade.get("symbol") != symbol:
                continue

            if trend == "bullish" and trade.get("side") == "sell":
                to_close.append(trade_id)
            elif trend == "bearish" and trade.get("side") == "buy":
                to_close.append(trade_id)

        for trade_id in to_close:
            self.close_trade(trade_id)

        if to_close:
            logger.info(f"🚪 تم إغلاق {len(to_close)} صفقة مخالفة للاتجاه لـ {symbol} - التوقيت السعودي 🇸🇦")

    # دوال مساعدة محسنة
    def get_active_trades_count(self, symbol: str = None) -> int:
        """الحصول على عدد الصفقات النشطة"""
        with self.trade_lock:
            try:
                if symbol:
                    count = sum(1 for trade in self.active_trades.values()
                                if trade.get('symbol') == symbol)
                    return count
                else:
                    return len(self.active_trades)
            except Exception as e:
                self._handle_error("💥 خطأ في عد الصفقات النشطة", e)
                return 0

    def get_active_trades(self, symbol: str = None) -> Dict:
        """الحصول على الصفقات النشطة"""
        with self.trade_lock:
            try:
                if symbol:
                    return {tid: trade for tid, trade in self.active_trades.items()
                            if trade.get('symbol') == symbol}
                else:
                    return self.active_trades.copy()
            except Exception as e:
                self._handle_error("💥 خطأ في الحصول على الصفقات النشطة", e)
                return {}

    def count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """عد الصفقات حسب النمط"""
        with self.trade_lock:
            try:
                count = 0
                for trade in self.active_trades.values():
                    if (trade.get('symbol') == symbol and
                        trade.get('mode_key') == mode_key):
                        count += 1
                return count
            except Exception as e:
                self._handle_error("💥 خطأ في عد الصفقات حسب النمط", e)
                return 0

    def _get_trade_type(self, mode_key):
        """الحصول على نوع الصفقة"""
        trade_types = {
            "TRADING_MODE": "🟦 أساسي",
            "TRADING_MODE1": "🟨 نمط 1",
            "TRADING_MODE2": "🟪 نمط 2",
        }
        return trade_types.get(mode_key, "🟦 أساسي")

    def _handle_error(self, msg, exc=None):
        """معالجة الأخطاء بالتوقيت السعودي"""
        full = f"{msg}: {exc}" if exc else msg
        logger.error(full)
        self._error_log.append({
            'timestamp': saudi_time.now().isoformat(),
            'timezone': 'Asia/Riyadh 🇸🇦',
            'error': full
        })

        # 🔧 FIXED: تنظيف error_log إذا تجاوز الحد
        if len(self._error_log) > 500:
            excess = len(self._error_log) - 500
            for _ in range(excess):
                if self._error_log:
                    self._error_log.popleft()

    def get_error_log(self):
        return list(self._error_log)

    def get_trend_status(self, symbol: str) -> Dict:
        """الحصول على حالة الاتجاه المفصلة بالتوقيت السعودي"""
        try:
            pool_signals = self.trend_pool.get(symbol, {}).get('signals', {})
            return {
                'symbol': symbol,
                'current_trend': self.current_trend.get(symbol, "UNKNOWN"),
                'last_reported': self.last_reported_trend.get(symbol, "UNKNOWN"),
                'trend_strength': self.trend_strength.get(symbol, 0),
                'signals_count': self.trend_signals_count.get(symbol, 0),
                'trend_pool_size': len(pool_signals),
                'active_trades': self.get_active_trades_count(symbol),
                'trend_history_count': len(self.trend_history.get(symbol, [])),
                'redis_enabled': self.redis_enabled,
                'timezone': 'Asia/Riyadh 🇸🇦'
            }
        except Exception as e:
            self._handle_error(f"💥 خطأ في الحصول على حالة الاتجاه لـ {symbol}", e)
            return {'error': str(e), 'symbol': symbol}

    def force_trend_change(self, symbol: str, new_trend: str) -> bool:
        """تغيير الاتجاه قسراً"""
        try:
            if new_trend not in ['bullish', 'bearish']:
                logger.error(f"❌ اتجاه غير صالح: {new_trend}")
                return False

            old_trend = self.current_trend.get(symbol, "UNKNOWN")
            self.current_trend[symbol] = new_trend
            self.last_reported_trend[symbol] = new_trend
            self._reset_trend_pool(symbol)

            # حفظ الاتجاه القسري في Redis + ✅ LOG واضح
            if self.redis_enabled:
                try:
                    self.redis.set_trend(symbol, new_trend)
                    logger.info(
                        f"💾 تم حفظ الاتجاه في Redis | Symbol={symbol} | Trend={new_trend.upper()} | (FORCED) | Time={saudi_time.now().isoformat()} 🇸🇦"
                    )
                except Exception as e:
                    self._handle_error(f"⚠️ خطأ في حفظ الاتجاه القسري في Redis لـ {symbol}", e)

            logger.info(f"🔧 تغيير اتجاه قسري: {symbol} {old_trend} → {new_trend} - التوقيت السعودي 🇸🇦")
            return True
        except Exception as e:
            self._handle_error(f"💥 خطأ في تغيير الاتجاه القسري لـ {symbol}", e)
            return False

    def get_trend_history(self, symbol: str, limit: int = 5) -> List[Dict]:
        """الحصول على سجل الاتجاه"""
        try:
            history = self.trend_history.get(symbol, deque())
            history_list = list(history)
            return history_list[-limit:] if limit and history_list else history_list
        except Exception as e:
            self._handle_error(f"💥 خطأ في الحصول على سجل الاتجاه لـ {symbol}", e)
            return []

    def clear_trend_data(self, symbol: str) -> bool:
        """مسح بيانات الاتجاه لرمز معين"""
        try:
            keys_to_clear = [
                self.current_trend, self.previous_trend, self.last_reported_trend,
                self.trend_strength, self.trend_signals_count,
                self.trend_pool
            ]

            for data_dict in keys_to_clear:
                if symbol in data_dict:
                    del data_dict[symbol]

            # مسح trend_history
            if symbol in self.trend_history:
                del self.trend_history[symbol]

            # مسح بيانات الاتجاه من Redis أيضاً
            if self.redis_enabled:
                try:
                    self.redis.clear_trend(symbol)
                except Exception as e:
                    self._handle_error(f"⚠️ خطأ في مسح الاتجاه من Redis لـ {symbol}", e)

            logger.info(f"🧹 تم مسح جميع بيانات الاتجاه لـ {symbol} - التوقيت السعودي 🇸🇦")
            return True
        except Exception as e:
            self._handle_error(f"💥 خطأ في مسح بيانات الاتجاه لـ {symbol}", e)
            return False

    def _load_trends_from_redis(self) -> None:
        """تحميل الاتجاهات المحفوظة من Redis عند بدء التشغيل"""
        try:
            if not self.redis_enabled:
                return
            trends = self.redis.get_all_trends()
            if not trends:
                logger.info("ℹ️ لا توجد اتجاهات محفوظة مسبقاً في Redis")
                return
            for symbol, trend in trends.items():
                self.current_trend[symbol] = trend
            logger.info(f"✅ تم تحميل {len(trends)} اتجاه(ات) من Redis عند بدء التشغيل")
        except Exception as e:
            self._handle_error("⚠️ خطأ في تحميل الاتجاهات من Redis", e)

    def get_current_trend(self, symbol: str) -> str:
        """الحصول على الاتجاه الحالي مع استخدام Redis كمصدر دائم"""
        try:
            trend = self.current_trend.get(symbol, "UNKNOWN")
            if trend == "UNKNOWN" and self.redis_enabled:
                saved = self.redis.get_trend(symbol)
                if saved:
                    self.current_trend[symbol] = saved
                    trend = saved
            return trend
        except Exception as e:
            self._handle_error(f"⚠️ خطأ في قراءة الاتجاه الحالي من Redis لـ {symbol}", e)
            return self.current_trend.get(symbol, "UNKNOWN")

    def get_trading_limits(self, symbol: str) -> Dict:
        """الحصول على حدود التداول الحالية"""
        return {
            'symbol': symbol,
            'current_trades': self.symbol_trade_count.get(symbol, 0),
            'max_per_symbol': self.config.get("MAX_TRADES_PER_SYMBOL", 20),
            'total_trades': len(self.active_trades),
            'max_total_trades': self.config.get("MAX_OPEN_TRADES", 20),
            'can_open_more': self.symbol_trade_count.get(symbol, 0) < self.config.get("MAX_TRADES_PER_SYMBOL", 20),
            'redis_enabled': self.redis_enabled,
            'timezone': 'Asia/Riyadh 🇸🇦'
        }

    def cleanup_memory(self) -> Dict:
        """🧹 تنظيف الذاكرة وإدارة التخزين"""
        try:
            # تنظيف trend_history القديم
            cleaned_history = 0
            current_time = saudi_time.now()
            one_week_ago = current_time - timedelta(days=7)

            for symbol in list(self.trend_history.keys()):
                history = self.trend_history[symbol]
                initial_count = len(history)

                # الاحتفاظ فقط بالسجلات الحديثة (آخر 50)
                while len(history) > 50:
                    history.popleft()

                cleaned_history += (initial_count - len(history))

            # تنظيف error_log
            error_log_cleaned = 0
            if len(self._error_log) > 500:
                error_log_cleaned = len(self._error_log) - 500
                for _ in range(error_log_cleaned):
                    if self._error_log:
                        self._error_log.popleft()

            # تنظيف trend_pool القديم
            pool_cleaned = 0
            for symbol in list(self.trend_pool.keys()):
                pool = self.trend_pool[symbol]
                signals = pool.get('signals', {})

                # حذف الإشارات القديمة جداً
                old_signals = []
                for signal_key, signal_data in signals.items():
                    timestamp = signal_data.get('timestamp')
                    if timestamp and hasattr(timestamp, 'timestamp'):
                        if timestamp.timestamp() < one_week_ago.timestamp():
                            old_signals.append(signal_key)

                for signal_key in old_signals:
                    del signals[signal_key]
                    pool_cleaned += 1

                # إذا كانت الإشارات فارغة، حذف الرمز
                if not signals:
                    del self.trend_pool[symbol]

            logger.info(f"🧹 تنظيف الذاكرة: تم تنظيف {cleaned_history} سجل اتجاه، {error_log_cleaned} خطأ، {pool_cleaned} إشارة - التوقيت السعودي 🇸🇦")

            return {
                'history_cleaned': cleaned_history,
                'error_log_cleaned': error_log_cleaned,
                'pool_signals_cleaned': pool_cleaned,
                'timestamp': current_time.isoformat(),
                'timezone': 'Asia/Riyadh 🇸🇦'
            }

        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف الذاكرة", e)
            return {'error': str(e)}

    def get_system_stats(self) -> Dict:
        """📊 الحصول على إحصائيات النظام"""
        return {
            'active_trades': len(self.active_trades),
            'symbol_trade_counts': dict(self.symbol_trade_count),
            'total_trades_counter': self.total_trade_counter,
            'metrics': self.metrics,
            'current_trends_count': len(self.current_trend),
            'trend_history_total': sum(len(history) for history in self.trend_history.values()),
            'error_log_size': len(self._error_log),
            'redis_enabled': self.redis_enabled,
            'timestamp': saudi_time.now().isoformat(),
            'timezone': 'Asia/Riyadh 🇸🇦'
        }
