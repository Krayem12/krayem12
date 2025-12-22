# core/trade_manager.py - النسخة المحدثة
# core/trade_manager.py
# ==========================================================
# ✅ TradeManager – النسخة المحدثة مع دعم GroupMapper
# ==========================================================

import logging
import threading
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque

# ✅ استيراد موحد
from utils.time_utils import saudi_time

# ----------------------------------------------------------
# 🔴 Redis Manager
# ----------------------------------------------------------
try:
    from utils.redis_manager import RedisManager
except ImportError:
    try:
        from core.redis_manager import RedisManager
    except ImportError:
        RedisManager = None

logger = logging.getLogger(__name__)

class TradeManager:
    """🎯 مدير التداول - مع دعم GroupMapper"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Locks
        self.trade_lock = threading.Lock()
        self.trend_lock = threading.RLock()
        
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
        
        # ✅ إضافة GroupMapper
        try:
            from .group_mapper import GroupMapper
            self.group_mapper = GroupMapper()
            logger.info("✅ TradeManager مع دعم GroupMapper")
        except ImportError as e:
            logger.warning(f"⚠️ GroupMapper غير متوفر: {e}")
            self.group_mapper = None
        
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
                self.redis_enabled = self.redis.is_enabled() if hasattr(self.redis, 'is_enabled') else False
                if self.redis_enabled:
                    self._load_trends_from_redis()
            except Exception as e:
                logger.warning(f"⚠️ Redis init failed: {e}")
                self.redis = None
                self.redis_enabled = False
        
        logger.info("✅ TradeManager المحدث جاهز – مع دعم GroupMapper 🇸🇦")
    
    # ======================================================
    # 🔗 Required by TradingSystem
    # ======================================================
    def set_group_manager(self, group_manager):
        self.group_manager = group_manager
    
    def set_notification_manager(self, notification_manager):
        self.notification_manager = notification_manager
    
    # ======================================================
    # 🔧 Required by GroupManager - ✅ المحدث مع GroupMapper
    # ======================================================
    def count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """✅ المحدث: عدد الصفقات المفتوحة للنمط مع دعم GroupMapper"""
        try:
            with self.trade_lock:
                count = 0
                
                # إذا كان GroupMapper متوفراً
                if self.group_mapper:
                    # استخراج القاعدة من mode_key
                    base_name, _ = self.group_mapper.extract_base_and_direction(mode_key)
                    
                    for trade in self.active_trades.values():
                        if trade.get("symbol") == symbol:
                            trade_mode = trade.get("mode", "")
                            trade_base, _ = self.group_mapper.extract_base_and_direction(trade_mode)
                            
                            if trade_base == base_name:
                                count += 1
                else:
                    # الطريقة القديمة (للتوافق)
                    count = sum(
                        1 for trade in self.active_trades.values()
                        if trade.get("symbol") == symbol
                        and trade.get("mode") == mode_key
                    )
                
                logger.debug(f"🔍 count_trades_by_mode: {symbol} -> {mode_key} = {count}")
                return count
                
        except Exception as e:
            self._handle_error("count_trades_by_mode failed", e)
            return 0
    
    def get_active_trades_count(self, symbol: str = None) -> int:
        """عدد الصفقات النشطة"""
        try:
            with self.trade_lock:
                if symbol:
                    return sum(
                        1 for trade in self.active_trades.values()
                        if trade.get("symbol") == symbol
                    )
                else:
                    return len(self.active_trades)
        except Exception as e:
            self._handle_error("get_active_trades_count failed", e)
            return 0
    
    def open_trade(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> bool:
        """✅ المحدث: فتح صفقة جديدة مع GroupMapper"""
        try:
            trade_id = f"{symbol}_{direction}_{saudi_time.now().strftime('%Y%m%d%H%M%S')}_{hash(strategy_type) % 10000:04d}"
            
            with self.trade_lock:
                # ✅ استخدام GroupMapper لتوحيد mode_key إذا كان متوفراً
                normalized_mode = mode_key
                if self.group_mapper:
                    normalized_mode = self.group_mapper.normalize_group_name(mode_key, direction)
                    logger.debug(f"🔍 توحيد mode_key: {mode_key} -> {normalized_mode}")
                
                trade_info = {
                    'id': trade_id,
                    'symbol': symbol,
                    'direction': direction,
                    'strategy_type': strategy_type,
                    'mode': normalized_mode,  # ✅ استخدام الاسم الموحد
                    'original_mode': mode_key,  # حفظ الاسم الأصلي
                    'opened_at': saudi_time.isoformat(),
                    'timezone': 'Asia/Riyadh 🇸🇦',
                    'group_mapper_used': self.group_mapper is not None
                }
                
                self.active_trades[trade_id] = trade_info
                self.symbol_trade_count[symbol] += 1
                self.total_trade_counter += 1
                self.metrics["trades_opened"] += 1
                
                logger.info(f"✅ تم فتح صفقة: {trade_id} (mode: {normalized_mode})")
                return True
                
        except Exception as e:
            self._handle_error("open_trade", e)
            return False
    
    def handle_exit_signal(self, symbol: str, reason: str = "") -> int:
        """إغلاق جميع صفقات الرمز"""
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
                logger.info(f"🔚 تم إغلاق {closed} صفقة لـ {symbol}: {reason}")
        
        except Exception as e:
            logger.error(f"handle_exit_signal failed: {e}")
        
        return closed
    
    # ======================================================
    # 📈 Trend Handling - النسخة النهائية
    # ======================================================
    def get_current_trend(self, symbol: str) -> str:
        """الحصول على الاتجاه الحالي"""
        try:
            trend = self.current_trend.get(symbol)
            if trend:
                return trend
            
            if self.redis_enabled and self.redis:
                saved = self.redis.get_trend(symbol)
                if saved:
                    self.current_trend[symbol] = saved
                    return saved
            
            return "UNKNOWN"
        except Exception as e:
            self._handle_error("get_current_trend", e)
            return "UNKNOWN"
    
    def update_trend(self, symbol: str, classification: str, signal_data: Dict) -> Tuple[bool, str, List[str]]:
        """🎯 تحديث الاتجاه - لا يرسل إشعار إلا عند تحديد اتجاه واضح"""
        try:
            # تحديد اتجاه الإشارة
            direction = self._determine_trend_direction(signal_data, classification)
            if not direction:
                logger.info(f"📭 إشارة بدون اتجاه واضح: {signal_data.get('signal_type')}")
                return False, self.get_current_trend(symbol), []
            
            with self.trend_lock:
                old_trend = self.get_current_trend(symbol)
                pool = self.trend_pool[symbol]
                
                signal_type = (signal_data.get("signal_type") or "").strip()
                if not signal_type:
                    return False, old_trend, []
                
                required_signals = self.config.get("TREND_REQUIRED_SIGNALS", 2)
                
                # 🎯 التحقق من التعارض مع الإشارات الموجودة
                existing_directions = []
                for sig_info in pool["signals"].values():
                    existing_directions.append(sig_info.get("direction"))
                
                # إذا كان هناك تعارض في الاتجاهات
                if existing_directions and direction not in existing_directions:
                    logger.warning(f"⚠️ تعارض اتجاهات: {signal_type} -> {direction} يختلف عن {existing_directions}")
                    logger.info(f"🔄 إعادة تعيين المجمع بسبب التعارض - تجاهل الإشارة الجديدة")
                    
                    # إعادة تعيين المجمع ولا نضيف الإشارة الجديدة
                    self.trend_pool[symbol] = {"signals": {}, "count": 0}
                    return False, old_trend, []
                
                # إضافة الإشارة إلى المجمع
                pool["signals"][signal_type] = {
                    "direction": direction,
                    "timestamp": saudi_time.isoformat()
                }
                pool["count"] = len(pool["signals"])
                
                logger.info(f"📥 تمت إضافة الإشارة: {signal_type} -> {direction}")
                
                # 🎯 حساب عدد الإشارات في كل اتجاه
                direction_counts = {"bullish": 0, "bearish": 0}
                for sig_info in pool["signals"].values():
                    sig_direction = sig_info.get("direction")
                    if sig_direction in direction_counts:
                        direction_counts[sig_direction] += 1
                
                logger.info(f"📊 حالة المجمع: إشارات={pool['count']}, صاعدة={direction_counts['bullish']}, هابطة={direction_counts['bearish']}")
                
                # 🎯 التحقق من وجود إشارات كافية في نفس الاتجاه
                new_direction = None
                signals_used = []
                
                if direction_counts["bullish"] >= required_signals:
                    new_direction = "bullish"
                    signals_used = [sig for sig, info in pool["signals"].items() if info.get("direction") == "bullish"]
                    logger.info(f"✅ تم تحديد اتجاه صاعد: {direction_counts['bullish']} إشارة")
                    
                elif direction_counts["bearish"] >= required_signals:
                    new_direction = "bearish"
                    signals_used = [sig for sig, info in pool["signals"].items() if info.get("direction") == "bearish"]
                    logger.info(f"✅ تم تحديد اتجاه هابط: {direction_counts['bearish']} إشارة")
                
                # 🎯 إذا لم نحصل على إشارات كافية في نفس الاتجاه
                if not new_direction:
                    logger.info(f"⏸️ إشارات غير كافية لاتجاه واضح: تحتاج {required_signals} إشارة في نفس الاتجاه")
                    return False, old_trend, []
                
                # 🎯 إذا وصلنا هنا، فهذا يعني أن لدينا اتجاه واضح
                trend_changed = (old_trend != new_direction)
                
                if trend_changed:
                    # تحديث بيانات الاتجاه
                    self.previous_trend[symbol] = old_trend
                    self.current_trend[symbol] = new_direction
                    self.last_reported_trend[symbol] = new_direction
                    self.trend_strength[symbol] = len(signals_used)
                    
                    # تسجيل في التاريخ
                    self.trend_history[symbol].append({
                        "time": saudi_time.isoformat(),
                        "old": old_trend,
                        "new": new_direction,
                        "signals": signals_used,
                        "signal_count": len(signals_used),
                        "reason": f"تجميع {len(signals_used)} إشارة {new_direction}"
                    })
                    
                    # حفظ في Redis
                    if self.redis_enabled and self.redis:
                        try:
                            self.redis.set_trend(symbol, new_direction)
                            self._redis_set_raw(
                                f"trend:{symbol}:updated_at",
                                saudi_time.isoformat()
                            )
                        except Exception as e:
                            logger.warning(f"⚠️ حفظ Redis فشل: {e}")
                    
                    # 🎯 مسح المجمع بعد تحديد الاتجاه
                    self.trend_pool[symbol] = {"signals": {}, "count": 0}
                    
                    logger.info(f"🎯 تم تغيير الاتجاه: {symbol} -> {old_trend} → {new_direction}")
                    return True, old_trend, signals_used
                else:
                    # نفس الاتجاه، لا تغيير
                    logger.info(f"⏸️ نفس الاتجاه: {symbol} -> {new_direction}")
                    
                    # 🎯 مسح المجمع بعد تأكيد الاتجاه
                    self.trend_pool[symbol] = {"signals": {}, "count": 0}
                    
                    return False, old_trend, signals_used
        
        except Exception as e:
            self._handle_error("update_trend", e)
            return False, self.get_current_trend(symbol), []
    
    def _determine_trend_direction(self, signal_data: Dict, classification: str = None) -> Optional[str]:
        """تحديد اتجاه الإشارة بدقة"""
        try:
            signal_type = (signal_data.get("signal_type") or "").lower().strip()
            
            if not signal_type:
                return None
            
            # 🎯 قراءة الكلمات المفتاحية من الإعدادات
            bullish_keywords = [
                k.strip().lower() for k in self.config.get('BULLISH_KEYWORDS', 'bullish,buy,long,up,rise,increase').split(',') 
                if k.strip()
            ]
            bearish_keywords = [
                k.strip().lower() for k in self.config.get('BEARISH_KEYWORDS', 'bearish,sell,short,down,fall,decrease').split(',') 
                if k.strip()
            ]
            
            # التحقق من الكلمات المفتاحية أولاً
            for keyword in bullish_keywords:
                if keyword and keyword in signal_type:
                    return "bullish"
            
            for keyword in bearish_keywords:
                if keyword and keyword in signal_type:
                    return "bearish"
            
            # ثم التحقق من الأنماط الثابتة
            if 'money_flow_down' in signal_type:
                return "bearish"
            if 'money_flow_up' in signal_type:
                return "bullish"
            if 'trend_catcher_bullish' in signal_type:
                return "bullish"
            if 'trend_catcher_bearish' in signal_type:
                return "bearish"
            
            # استخدام التصنيف إذا كان متاحاً
            if classification:
                classification_lower = classification.lower()
                if 'bullish' in classification_lower:
                    return "bullish"
                elif 'bearish' in classification_lower:
                    return "bearish"
            
            return None
            
        except Exception as e:
            self._handle_error("_determine_trend_direction", e)
            return None
    
    def get_redis_client(self):
        """الحصول على عميل Redis بشكل آمن"""
        if self.redis_enabled and self.redis:
            if hasattr(self.redis, "get_client"):
                return self.redis.get_client()
            elif hasattr(self.redis, "client"):
                return self.redis.client
        return None
    
    def get_trend_status(self, symbol: str) -> Dict:
        """الحصول على حالة الاتجاه المفصلة"""
        try:
            current_trend = self.get_current_trend(symbol)
            pool = self.trend_pool.get(symbol, {"signals": {}, "count": 0})
            
            signal_analysis = []
            for signal_name, signal_info in pool["signals"].items():
                direction = signal_info.get("direction", "UNKNOWN")
                signal_analysis.append({
                    "signal": signal_name,
                    "direction": direction,
                    "status": "✅ صاعد" if direction == "bullish" else "🔻 هابط" if direction == "bearish" else "❓ غير معروف"
                })
            
            return {
                "symbol": symbol,
                "current_trend": current_trend,
                "previous_trend": self.previous_trend.get(symbol, "UNKNOWN"),
                "trend_strength": self.trend_strength.get(symbol, 0),
                "signals_in_pool": len(pool["signals"]),
                "signal_analysis": signal_analysis,
                "required_signals": self.config.get("TREND_REQUIRED_SIGNALS", 2),
                "group_mapper_available": self.group_mapper is not None,
                "timestamp": saudi_time.isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦"
            }
        except Exception as e:
            self._handle_error("get_trend_status", e)
            return {"error": str(e)}
    
    def get_trend_history(self, symbol: str, limit: int = 10) -> List[Dict]:
        """الحصول على سجل الاتجاه"""
        try:
            history = list(self.trend_history.get(symbol, deque()))
            return history[-limit:] if history else []
        except Exception as e:
            self._handle_error("get_trend_history", e)
            return []
    
    def force_trend_change(self, symbol: str, direction: str) -> bool:
        """تغيير الاتجاه قسراً"""
        try:
            with self.trend_lock:
                old_trend = self.get_current_trend(symbol)
                self.previous_trend[symbol] = old_trend
                self.current_trend[symbol] = direction
                self.last_reported_trend[symbol] = direction
                self.trend_strength[symbol] = 1
                
                # مسح المجمع
                self.trend_pool[symbol] = {"signals": {}, "count": 0}
                
                # تسجيل في التاريخ
                self.trend_history[symbol].append({
                    "time": saudi_time.isoformat(),
                    "old": old_trend,
                    "new": direction,
                    "signals": ["MANUAL_FORCE"],
                    "directions": [direction]
                })
                
                # حفظ في Redis
                if self.redis_enabled and self.redis:
                    try:
                        self.redis.set_trend(symbol, direction)
                    except Exception as e:
                        logger.warning(f"⚠️ Redis save failed in force_trend_change: {e}")
                
                logger.info(f"🔧 تغيير اتجاه قسري: {symbol} -> {old_trend} → {direction}")
                return True
                
        except Exception as e:
            self._handle_error("force_trend_change", e)
            return False
    
    def clear_trend_data(self, symbol: str) -> bool:
        """مسح بيانات الاتجاه"""
        try:
            with self.trend_lock:
                self.current_trend.pop(symbol, None)
                self.previous_trend.pop(symbol, None)
                self.last_reported_trend.pop(symbol, None)
                self.trend_strength.pop(symbol, None)
                self.trend_pool.pop(symbol, None)
                self.trend_history.pop(symbol, None)
                
                # مسح من Redis
                if self.redis_enabled and self.redis:
                    try:
                        client = self.get_redis_client()
                        if client:
                            client.delete(f"trend:{symbol}")
                            client.delete(f"trend:{symbol}:updated_at")
                            client.delete(f"trend:{symbol}:signals")
                            # إزالة من مجموعة الرموز
                            client.srem("trend:symbols", symbol)
                    except Exception as e:
                        logger.warning(f"⚠️ Redis delete failed: {e}")
                
                logger.info(f"🧹 تم مسح بيانات الاتجاه لـ {symbol}")
                return True
                
        except Exception as e:
            self._handle_error("clear_trend_data", e)
            return False
    
    # ======================================================
    # 🔴 Redis Helpers
    # ======================================================
    def _redis_set_raw(self, key: str, value: str):
        if not self.redis_enabled or not self.redis:
            return
        try:
            client = self.get_redis_client()
            if client:
                client.set(key, value)
        except Exception as e:
            logger.warning(f"⚠️ Redis raw set failed: {e}")
    
    def _load_trends_from_redis(self):
        if not self.redis_enabled or not self.redis:
            return
        try:
            if hasattr(self.redis, "get_all_trends"):
                for symbol, trend in self.redis.get_all_trends().items():
                    self.current_trend[symbol] = trend
                    logger.info(f"📥 تم تحميل اتجاه من Redis: {symbol} -> {trend}")
        except Exception as e:
            logger.warning(f"⚠️ Redis load trends failed: {e}")
    
    # ======================================================
    # 🧹 Cleanup
    # ======================================================
    def cleanup_memory(self):
        """تنظيف الذاكرة"""
        try:
            cutoff = saudi_time.now() - timedelta(days=7)
            cleaned_count = 0
            
            for symbol, hist in list(self.trend_history.items()):
                initial_len = len(hist)
                self.trend_history[symbol] = deque(
                    [
                        h for h in hist
                        if h.get("time") >= cutoff.isoformat()
                    ],
                    maxlen=200
                )
                cleaned_count += (initial_len - len(self.trend_history[symbol]))
            
            # تنظيف المجمعات القديمة
            for symbol in list(self.trend_pool.keys()):
                pool = self.trend_pool[symbol]
                if pool["count"] == 0:
                    # إذا كان المجمع فارغاً لمدة طويلة، حذفه
                    del self.trend_pool[symbol]
            
            logger.info(f"🧹 تنظيف الذاكرة: تم تنظيف {cleaned_count} سجل اتجاه قديم")
            
        except Exception as e:
            self._handle_error("cleanup_memory", e)
    
    def get_system_stats(self) -> Dict:
        """الحصول على إحصائيات النظام"""
        try:
            return {
                'active_trades': len(self.active_trades),
                'current_trends': len(self.current_trend),
                'trend_pool_size': sum(len(pool["signals"]) for pool in self.trend_pool.values()),
                'total_trades_opened': self.metrics["trades_opened"],
                'total_trades_closed': self.metrics["trades_closed"],
                'redis_enabled': self.redis_enabled,
                'group_mapper_available': self.group_mapper is not None,
                'error_log_size': len(self._error_log),
                'timestamp': saudi_time.isoformat(),
                'timezone': 'Asia/Riyadh 🇸🇦'
            }
        except Exception as e:
            self._handle_error("get_system_stats", e)
            return {'error': str(e)}
    
    # ======================================================
    # 🧾 Error Log
    # ======================================================
    def _handle_error(self, where: str, exc: Exception):
        """معالجة الأخطاء"""
        logger.error(f"{where}: {exc}")
        self._error_log.append({
            "time": saudi_time.isoformat(),
            "where": where,
            "error": str(exc)
        })
    
    def get_error_log(self) -> List[dict]:
        return list(self._error_log)
