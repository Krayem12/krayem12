import logging
from datetime import datetime, timedelta
import hashlib
from typing import Dict, List, Optional, Tuple
import threading
from collections import defaultdict, deque
from functools import lru_cache

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

class GroupManager:
    """🎯 نظام إدارة المجموعات بالتوقيت السعودي - جميع الإعدادات ديناميكية من .env"""

    def __init__(self, config, trade_manager):
        self.config = config
        self.trade_manager = trade_manager
        
        # تخزين الإشارات المؤقتة
        self.pending_signals = defaultdict(lambda: defaultdict(lambda: deque(maxlen=200)))
        
        # إحصائيات النظام
        self.error_log = deque(maxlen=1000)
        self.mode_performance = {}
        
        # قفل لإدارة التزامن
        self.signal_lock = threading.RLock()
        
        # 🎯 FIXED: استخدام إعدادات منع التكرار من ملف .env فقط
        self.duplicate_block_time = self.config.get('DUPLICATE_SIGNAL_BLOCK_TIME', 15)
        self.duplicate_cleanup_interval = self.config.get('DUPLICATE_CLEANUP_INTERVAL', 30)
        
        # 🔥 NEW: جميع العوامل الزمنية من .env
        self.cleanup_factor = self.config.get('CLEANUP_FACTOR', 1.5)
        self.signal_retention_factor = self.config.get('SIGNAL_RETENTION_FACTOR', 2.0)
        self.trade_cooldown_factor = self.config.get('TRADE_COOLDOWN_FACTOR', 1.2)
        self.signal_ttl_minutes = self.config.get('SIGNAL_TTL_MINUTES', 10)
        self.signal_cleanup_threshold = self.config.get('SIGNAL_CLEANUP_THRESHOLD_SECONDS', 60)
        
        # تحسين الأداء
        self.signal_hashes = {}
        self.last_hash_cleanup = saudi_time.now()
        
        # 🎯 NEW: تتبع الإشارات المستخدمة في الصفقات المفتوحة
        self.used_signals_for_trades = defaultdict(set)
        
        # 🎯 FIXED: إضافة متغيرات المراقبة
        self.memory_usage_log = deque(maxlen=100)
        self.last_cleanup_time = saudi_time.now()
        
        logger.info(f"🎯 نظام المجموعات المصحح جاهز - جميع الإعدادات من .env - التوقيت السعودي 🇸🇦")
        logger.info(f"⏰ إعدادات التوقيت: Block={self.duplicate_block_time}s, Cleanup={self.duplicate_cleanup_interval}s")
        logger.info(f"🔧 العوامل: Cleanup={self.cleanup_factor}, Retention={self.signal_retention_factor}")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None, 
                     extra_data: Optional[Dict] = None) -> None:
        """🎯 معالجة الأخطاء بالتوقيت السعودي"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        if extra_data:
            full_error += f" | Extra: {extra_data}"
        logger.error(full_error)
        
        error_entry = {
            'timestamp': saudi_time.now().isoformat(),
            'timezone': 'Asia/Riyadh 🇸🇦',
            'error': full_error
        }
        self.error_log.append(error_entry)

    def _is_group_enabled(self, group_type: str) -> bool:
        """التحقق من تفعيل المجموعة"""
        try:
            # 🔧 FIXED: تحسين معالجة نوع المجموعة
            if not group_type or not isinstance(group_type, str):
                return False
                
            group_key = group_type.split('_')[0].upper()
            enabled_key = f"{group_key}_ENABLED"
            is_enabled = self.config.get(enabled_key, False)
            
            logger.debug(f"🔍 حالة المجموعة {group_key}: {'✅ مفعلة' if is_enabled else '❌ معطلة'}")
            return is_enabled
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق من تفعيل المجموعة", e)
            return False

    def route_signal(self, symbol: str, signal_data: Dict, classification: str) -> List[Dict]:
        """🎯 توجيه الإشارة للمجموعة المناسبة بالتوقيت السعودي"""
        
        logger.info(f"🎯 بدء توجيه الإشارة: {symbol} -> {classification} -> {signal_data.get('signal_type')} - التوقيت السعودي 🇸🇦")
        
        if not self._validate_input(symbol, signal_data, classification):
            return []

        # ======================================================
        # 🔴 FORCE EXIT: تصفير الصفقات فعليًا عند إشارات الخروج (من .env)
        # ======================================================
        signal_type = (signal_data.get("signal_type") or "").lower().strip()

        exit_signals = [
            s.strip().lower()
            for s in (self.config.get("EXIT_SIGNALS", "") or "").split(",")
            if s.strip()
        ]

        exit_keywords = [
            k.strip().lower()
            for k in (self.config.get("EXIT_KEYWORDS", "") or "").split(",")
            if k.strip()
        ]

        is_exit_signal = (
            signal_type in exit_signals
            or any(k in signal_type for k in exit_keywords)
        )

        if is_exit_signal:
            logger.warning(
                f"🚪 EXIT SIGNAL DETECTED | {symbol} | {signal_type} → تصفير الصفقات فعليًا"
            )

            closed = 0
            try:
                closed = self.trade_manager.handle_exit_signal(symbol, signal_type.upper())
            except Exception as e:
                logger.error(f"💥 خطأ أثناء تصفير الصفقات عند الخروج لـ {symbol}: {e}", exc_info=True)

            logger.warning(
                f"🧹 EXIT RESET DONE | {symbol} | closed_trades={closed}"
            )
            return []

        try:
            # تنظيف الإشارات المنتهية
            self.cleanup_expired_signals(symbol)

            # تحديد المجموعة والاتجاه
            group_type, direction = self._determine_group_and_direction_enhanced(classification, signal_data)
            if not group_type or not direction:
                logger.error(f"❌ لا يمكن تحديد المجموعة أو الاتجاه للتصنيف: {classification}")
                return []

            logger.info(f"🎯 تم تحديد: {symbol} -> {group_type} -> {direction} - التوقيت السعودي 🇸🇦")

            # ✅ FIXED: التحقق من تفعيل المجموعة أولاً
            if not self._is_group_enabled(group_type):
                logger.warning(f"🚫 المجموعة {group_type} معطلة - تجاهل الإشارة")
                return []

            # 🎯 FIXED: استخدام وقت منع التكرار من الإعدادات فقط
            if self._is_duplicate_signal_optimized(symbol, signal_data, group_type):
                logger.info(f"🔁 إشارة مكررة - تم تجاهلها: {symbol} -> {signal_data.get('signal_type')} - التوقيت السعودي 🇸🇦")
                return []

            # استخدام القفل لمنع التزامن
            with self.signal_lock:
                # إضافة الإشارة للمجموعة
                self._add_signal_to_group(symbol, signal_data, group_type, direction, classification)

                # التحقق من محاذاة الاتجاه
                trend_check_result = self._check_trend_alignment_enhanced(symbol, direction, group_type)
                if not trend_check_result:
                    self._handle_contrarian_signal(symbol, group_type, signal_data)
                    return []

                # تقييم شروط الدخول
                trade_results = self._evaluate_entry_conditions(symbol, direction)
                
                if trade_results:
                    logger.info(f"✅ تم فتح {len(trade_results)} صفقة لـ {symbol} - التوقيت السعودي 🇸🇦")
                else:
                    logger.info(f"⏸️ لم يتم فتح صفقات لـ {symbol} - الشروط غير متحققة - التوقيت السعودي 🇸🇦")
                
                return trade_results

        except Exception as e:
            self._handle_error(f"💥 خطأ في توجيه الإشارة: {symbol}", e, 
                             {'classification': classification, 'signal_type': signal_data.get('signal_type')})
            return []

    def _check_trend_alignment_enhanced(self, symbol: str, direction: str, group_type: str) -> bool:
        """✅ FIXED: التحقق من محاذاة الاتجاه بشكل آمن مع التحقق من وجود trade_manager"""
        
        try:
            # 🔧 FIXED: التحقق من وجود trade_manager
            if not hasattr(self, 'trade_manager') or self.trade_manager is None:
                logger.error("❌ trade_manager غير متوفر للتحقق من الاتجاه")
                return False
            
            group_key = group_type.split('_')[0]
            
            if not group_key or not self._is_group_enabled(group_type):
                logger.warning(f"🚫 المجموعة {group_key} معطلة أو غير صالحة - تجاهل الإشارة")
                return False
            
            trend_mode_key = f"{group_key.upper()}_TREND_MODE"
            group_trend_mode = self.config.get(trend_mode_key, self.config.get('GROUP1_TREND_MODE', 'ONLY_TREND'))
            
            current_trend = self.trade_manager.get_current_trend(symbol)
            
            if group_trend_mode == 'ALLOW_COUNTER_TREND':
                logger.info(f"🔓 فتح الصفقة بدون قيود اتجاه: {symbol} -> {direction.upper()} (المجموعة: {group_key}) - التوقيت السعودي 🇸🇦")
                return True
            
            if current_trend == 'UNKNOWN':
                logger.warning(f"⏸️ تجاهل الإشارة - اتجاه غير معروف: {symbol} للمجموعة {group_key} - التوقيت السعودي 🇸🇦")
                return False
            
            is_aligned = (
                (current_trend == 'bullish' and direction == 'buy') or
                (current_trend == 'bearish' and direction == 'sell')
            )
            
            if not is_aligned:
                logger.warning(f"🚫 الإشارة مخالفة للاتجاه: {direction.upper()} vs {current_trend.upper()} (المجموعة: {group_key}) - التوقيت السعودي 🇸🇦")
                return False
            
            logger.info(f"✅ الإشارة متوافقة مع الاتجاه: {direction.upper()} vs {current_trend.upper()} - التوقيت السعودي 🇸🇦")
            return True
            
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق من محاذاة الاتجاه", e)
            return False

    def _determine_group_and_direction_enhanced(self, classification: str, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """✅ FIXED: تحديد المجموعة والاتجاه بشكل آمن مع تحسين الأداء"""
        
        try:
            direct_classification_map = {
                'entry_bullish': ('group1_bullish', 'buy'),
                'entry_bearish': ('group1_bearish', 'sell'),
                'entry_bullish1': ('group2_bullish', 'buy') if self._is_group_enabled('group2') else (None, None),
                'entry_bearish1': ('group2_bearish', 'sell') if self._is_group_enabled('group2') else (None, None),
            }
            
            if classification in direct_classification_map:
                result = direct_classification_map[classification]
                if all(result):
                    logger.info(f"🎯 تم تحديد المجموعة مباشرة: {classification} -> {result} - التوقيت السعودي 🇸🇦")
                    return result
            
            group_classification_map = {
                'group3': self._get_group_direction(3, signal_data) if self._is_group_enabled('group3') else (None, None),
                'group3_bullish': ('group3_bullish', 'buy') if self._is_group_enabled('group3') else (None, None),
                'group3_bearish': ('group3_bearish', 'sell') if self._is_group_enabled('group3') else (None, None),
                
                'group4': self._get_group_direction(4, signal_data) if self._is_group_enabled('group4') else (None, None),
                'group4_bullish': ('group4_bullish', 'buy') if self._is_group_enabled('group4') else (None, None),
                'group4_bearish': ('group4_bearish', 'sell') if self._is_group_enabled('group4') else (None, None),
                
                'group5': self._get_group_direction(5, signal_data) if self._is_group_enabled('group5') else (None, None),
                'group5_bullish': ('group5_bullish', 'buy') if self._is_group_enabled('group5') else (None, None),
                'group5_bearish': ('group5_bearish', 'sell') if self._is_group_enabled('group5') else (None, None),
                
                'trend': self._handle_trend_signal(signal_data),
                'trend_confirm': self._handle_trend_signal(signal_data)
            }
            
            if classification in group_classification_map:
                result = group_classification_map[classification]
                if result and all(result):
                    logger.info(f"🎯 تم تحديد المجموعة: {classification} -> {result} - التوقيت السعودي 🇸🇦")
                    return result
            
            logger.error(f"❌ تصنيف غير معروف أو المجموعة معطلة: {classification} - التوقيت السعودي 🇸🇦")
            return None, None
                
        except Exception as e:
            self._handle_error("💥 خطأ في تحديد المجموعة والاتجاه", e)
            return None, None

    def _handle_trend_signal(self, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """معالجة إشارات الاتجاه"""
        try:
            signal_type = signal_data.get('signal_type', '').lower()
            if 'bullish' in signal_type or 'up' in signal_type or 'buy' in signal_type:
                return 'trend_bullish', 'buy'
            elif 'bearish' in signal_type or 'down' in signal_type or 'sell' in signal_type:
                return 'trend_bearish', 'sell'
            return None, None
        except Exception as e:
            self._handle_error("💥 خطأ في معالجة إشارة الاتجاه", e)
            return None, None

    def _get_group_direction(self, group_num: int, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """✅ OPTIMIZED: دالة محسنة لتحديد اتجاه المجموعات"""
        try:
            group_name = f'group{group_num}'
            if not self._is_group_enabled(group_name):
                return None, None
                
            signal_type = signal_data.get('signal_type', '').lower()
            
            # ✅ FIX: Safe access to signals configuration
            signals_config = self.config.get('signals', {})
            group_bullish = [s.lower().strip() for s in signals_config.get(f'group{group_num}_bullish', [])]
            group_bearish = [s.lower().strip() for s in signals_config.get(f'group{group_num}_bearish', [])]
            
            if signal_type in group_bullish:
                return f'group{group_num}_bullish', 'buy'
            elif signal_type in group_bearish:
                return f'group{group_num}_bearish', 'sell'
            
            logger.debug(f"🔍 إشارة غير معروفة للمجموعة {group_num}: {signal_type} - التوقيت السعودي 🇸🇦")
            return None, None
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في تحديد اتجاه المجموعة {group_num}", e)
            return None, None

    def _validate_input(self, symbol: str, signal_data: Dict, classification: str) -> bool:
        """التحقق من صحة بيانات الإدخال"""
        if not symbol or not isinstance(symbol, str) or symbol.strip() == '' or symbol == 'UNKNOWN':
            logger.error("❌ رمز غير صالح")
            return False
        
        if not signal_data or not isinstance(signal_data, dict) or 'signal_type' not in signal_data:
            logger.error("❌ بيانات الإشارة غير صالحة")
            return False
        
        valid_classifications = {
            'entry_bullish', 'entry_bearish', 'entry_bullish1', 'entry_bearish1', 
            'group3', 'group4', 'group5', 'group3_bullish', 'group3_bearish',
            'group4_bullish', 'group4_bearish', 'group5_bullish', 'group5_bearish',
            'trend', 'trend_confirm'
        }
        
        if classification not in valid_classifications:
            logger.error(f"❌ تصنيف غير معروف: {classification}")
            return False
        
        return True

    def _add_signal_to_group(self, symbol: str, signal_data: Dict, group_type: str, 
                           direction: str, classification: str) -> None:
        """إضافة الإشارة للمجموعة بالتوقيت السعودي"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                all_group_types = [
                    'group1_bullish', 'group1_bearish', 'group2_bullish', 'group2_bearish',
                    'group3_bullish', 'group3_bearish', 'group4_bullish', 'group4_bearish',
                    'group5_bullish', 'group5_bearish', 'trend_bullish', 'trend_bearish'
                ]
                for gt in all_group_types:
                    self.pending_signals[group_key][gt] = deque(maxlen=200)
                
                self.pending_signals[group_key]["_meta"] = {"created_at": saudi_time.now(), "updated_at": saudi_time.now()}
            
            signal_info = {
                'hash': hashlib.md5(
                    f"{signal_data['signal_type']}_{classification}_{symbol}_{saudi_time.now().strftime('%Y%m%d%H%M%S')}".encode()
                ).hexdigest(),
                'signal_type': signal_data['signal_type'],
                'classification': classification,
                'timestamp': saudi_time.now(),
                'direction': direction,
                'symbol': symbol,
                'group_type': group_type,
                'timezone': 'Asia/Riyadh 🇸🇦'
            }
            
            self.pending_signals[group_key][group_type].append(signal_info)
            self.pending_signals[group_key].setdefault("_meta", {})["updated_at"] = saudi_time.now()
            
            logger.info(f"📥 إشارة مضافة: {symbol} -> {signal_data['signal_type']} → {group_type} - التوقيت السعودي 🇸🇦")
            
        except Exception as e:
            self._handle_error("💥 خطأ في إضافة الإشارة للمجموعة", e)

    def _is_duplicate_signal_optimized(self, symbol: str, signal_data: Dict, group_type: str) -> bool:
        """🎯 FIXED: منع التكرار حسب المجموعة - لا تسمح بنفس الإشارة لنفس المجموعة"""
        try:
            signal_type = signal_data.get('signal_type', '').lower().strip()
            if not signal_type:
                return False
                
            # 🔥 التعديل: استخدام رمز + إشارة + مجموعة لمنع التكرار داخل نفس المجموعة
            signal_key = f"{symbol}_{signal_type}_{group_type}"
            current_time = saudi_time.now()
            
            with self.signal_lock:
                # 🔍 البحث عن إشارات مكررة حديثة لنفس الرمز ونفس الإشارة ونفس المجموعة
                for existing_key, timestamp in list(self.signal_hashes.items()):
                    # تنظيف الإشارات القديمة تلقائياً
                    if (current_time - timestamp).total_seconds() > self.duplicate_block_time:
                        del self.signal_hashes[existing_key]
                        continue
                    
                    # 🔥 التعديل: إذا كانت نفس الإشارة لنفس الرمز ونفس المجموعة
                    if existing_key == signal_key:
                        logger.warning(f"🚫 إشارة مكررة لنفس المجموعة: {symbol} -> {signal_type} -> {group_type}")
                        return True
            
                # ✅ إضافة الإشارة الجديدة
                self.signal_hashes[signal_key] = current_time
                logger.info(f"🔓 السماح بالإشارة: {symbol} -> {signal_type} -> {group_type}")
                return False
                
        except Exception as e:
            self._handle_error("💥 خطأ في فحص التكرار", e)
            return False

    def _cleanup_old_hashes(self):
        """🎯 FIXED: تنظيف التجزئات القديمة باستخدام الإعدادات من .env فقط"""
        try:
            current_time = saudi_time.now()
            with self.signal_lock:
            
                if (current_time - self.last_hash_cleanup).total_seconds() > self.duplicate_cleanup_interval:
                    initial_count = len(self.signal_hashes)
                
                    # 🔥 التعديل: استخدام عامل التنظيف من .env بدلاً من القيمة الثابتة
                    max_age = self.duplicate_block_time * self.cleanup_factor
                
                    expired_hashes = [
                        hash_key for hash_key, timestamp in self.signal_hashes.items()
                        if (current_time - timestamp).total_seconds() > max_age
                    ]
                
                    for hash_key in expired_hashes:
                        del self.signal_hashes[hash_key]
                
                    cleaned_count = len(expired_hashes)
                    if cleaned_count > 0:
                        logger.info(f"🧹 تم تنظيف {cleaned_count} تجزئة قديمة من أصل {initial_count} - التوقيت السعودي 🇸🇦")
                
                    self.last_hash_cleanup = current_time
                
        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف التجزئات", e)

    def _handle_contrarian_signal(self, symbol: str, group_type: str, signal_data: Dict) -> None:
        """معالجة الإشارة المخالفة للاتجاه"""
        store_contrarian = self.config.get('STORE_CONTRARIAN_SIGNALS', False)
        if store_contrarian:
            logger.info(f"📦 الإشارة مخالفة للاتجاه - تم تخزينها: {symbol} → {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")
        else:
            logger.info(f"🚫 الإشارة مخالفة للاتجاه - تم تجاهلها: {symbol} → {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")

    def _evaluate_entry_conditions(self, symbol: str, direction: str) -> List[Dict]:
        """✅ FIXED: تقييم شروط الدخول بشكل آمن"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                logger.warning(f"⚠️ لا توجد إشارات للرمز: {symbol}")
                return []
            
            # ✅ FIXED: التحقق من وجود المجموعات المطلوبة
            signal_counts = self._count_signals_by_direction(group_key, direction)
            if not signal_counts:
                logger.warning(f"⚠️ لا توجد إشارات للاتجاه {direction} في {symbol}")
                return []
            
            logger.info(f"📊 إحصائيات {symbol} [{direction.upper()}]: G1={signal_counts['g1']}, G2={signal_counts['g2']}, G3={signal_counts['g3']}, G4={signal_counts['g4']}, G5={signal_counts['g5']} - التوقيت السعودي 🇸🇦")
            
            active_modes = self._get_active_modes()
            trade_results = []
            
            for mode_key in active_modes:
                trade_result = self._evaluate_single_mode(mode_key, symbol, direction, signal_counts)
                if trade_result:
                    trade_results.append(trade_result)
            return trade_results
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في تقييم شروط الدخول: {symbol}", e)
            return []

    def _count_signals_by_direction(self, group_key: str, direction: str) -> Dict[str, int]:
        """✅ FIXED: حساب عدد الإشارات بشكل آمن"""
        try:
            if group_key not in self.pending_signals:
                return {}
                
            groups = self.pending_signals[group_key]
            
            if direction == "buy":
                return {
                    'g1': len(groups.get("group1_bullish", [])),
                    'g2': len(groups.get("group2_bullish", [])),
                    'g3': len(groups.get("group3_bullish", [])),
                    'g4': len(groups.get("group4_bullish", [])),
                    'g5': len(groups.get("group5_bullish", []))
                }
            else:
                return {
                    'g1': len(groups.get("group1_bearish", [])),
                    'g2': len(groups.get("group2_bearish", [])),
                    'g3': len(groups.get("group3_bearish", [])),
                    'g4': len(groups.get("group4_bearish", [])),
                    'g5': len(groups.get("group5_bearish", []))
                }
        except Exception as e:
            self._handle_error("💥 خطأ في حساب الإشارات", e)
            return {}

    def _get_active_modes(self) -> List[str]:
        """الحصول على الأنماط المفعلة"""
        active_modes = ['TRADING_MODE']
        
        if self.config.get('TRADING_MODE1_ENABLED', False):
            active_modes.append('TRADING_MODE1')
        if self.config.get('TRADING_MODE2_ENABLED', False):
            active_modes.append('TRADING_MODE2')
        
        logger.info(f"🎯 الأنماط المفعلة: {active_modes} - التوقيت السعودي 🇸🇦")
        return active_modes

    def _evaluate_single_mode(self, mode_key: str, symbol: str, direction: str, signal_counts: Dict) -> Optional[Dict]:
        """🎯 FIXED: تقييم نمط تداول فردي مع منع الإشارات المكررة من نفس المجموعة"""
        try:
            if not self._can_open_trade(symbol, mode_key):
                logger.warning(f"🚫 لا يمكن فتح صفقة لـ {symbol} - حدود النمط {mode_key} - التوقيت السعودي 🇸🇦")
                return None
            
            trading_mode = self.config.get(mode_key)
            if not trading_mode:
                logger.warning(f"🚫 لا يوجد إعدادات للنمط {mode_key}")
                return None

            # التحقق من أن الإشارات كافية
            conditions_met, required_groups = self._check_strategy_conditions(trading_mode, signal_counts)
            
            # 🔥 التعديل الجديد: التحقق من أن الإشارات من مجموعات مختلفة وغير مكررة
            signals_diverse = self._are_signals_different_and_from_different_groups(symbol, required_groups, direction)
            
            if conditions_met and signals_diverse:
                logger.info(f"✅ تحققت شروط النمط {mode_key} لـ {symbol} - إشارات من مجموعات مختلفة - جاهز لفتح الصفقة - التوقيت السعودي 🇸🇦")
                
                if self._open_trade(symbol, direction, trading_mode, mode_key):
                    trade_info = self._collect_trade_signals(symbol, direction, required_groups)
                    trade_info.update({
                        'symbol': symbol,
                        'direction': direction,
                        'strategy_type': trading_mode,
                        'mode_key': mode_key,
                        'trade_timestamp': saudi_time.now().isoformat(),
                        'timezone': 'Asia/Riyadh 🇸🇦'
                    })
                    
                    # تنظيف الإشارات المستخدمة بعد فتح الصفقة بنجاح
                    self._reset_used_signals_after_trade(symbol, direction, required_groups)
                    
                    return trade_info
                else:
                    logger.error(f"❌ فشل فتح الصفقة رغم تحقق الشروط لـ {symbol} - التوقيت السعودي 🇸🇦")
            else:
                if conditions_met and not signals_diverse:
                    logger.info(f"⏸️ الشروط متحققة لكن الإشارات مكررة أو من مجموعة واحدة لـ {symbol} - التوقيت السعودي 🇸🇦")
                else:
                    logger.info(f"⏸️ لم تتحقق شروط النمط {mode_key} لـ {symbol} - التوقيت السعودي 🇸🇦")
            
            return None
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في تقييم النمط {mode_key}", e)
            return None

    def _are_signals_different_and_from_different_groups(self, symbol: str, required_groups: List[str], direction: str) -> bool:
        """🎯 NEW: التحقق من أن الإشارات من مجموعات مختلفة وغير مكررة"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return False
            
            groups = self.pending_signals[group_key]
            used_signals = set()
            groups_used = set()
            
            for group in required_groups:
                if not group:
                    continue
                    
                group_type = f"{group.lower()}_bullish" if direction == 'buy' else f"{group.lower()}_bearish"
                
                if group_type in groups and groups[group_type]:
                    # أخذ آخر إشارة من كل مجموعة
                    latest_signal = groups[group_type][-1]['signal_type']
                    
                    # 🔥 التحقق من عدم تكرار الإشارة
                    if latest_signal in used_signals:
                        logger.warning(f"🚫 إشارة مكررة من مجموعات مختلفة: {latest_signal}")
                        return False
                    
                    used_signals.add(latest_signal)
                    groups_used.add(group)
            
            # 🔥 التأكد من وجود إشارات من مجموعتين مختلفتين على الأقل
            if len(groups_used) < 2:
                logger.warning(f"🚫 الإشارات من مجموعة واحدة فقط: {groups_used}")
                return False
                
            logger.info(f"✅ إشارات من مجموعات مختلفة: {groups_used} -> {used_signals}")
            return True
                
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق من تنوع الإشارات", e)
            return False

    def _can_open_trade(self, symbol: str, mode_key: str) -> bool:
        """التحقق من إمكانية فتح صفقة جديدة"""
        try:
            # 🔧 FIXED: التحقق من وجود trade_manager
            if not hasattr(self, 'trade_manager') or self.trade_manager is None:
                logger.error("❌ trade_manager غير متوفر للتحقق من إمكانية فتح الصفقة")
                return False
            
            # 🔧 FIXED: دعم نسخ TradeManager المختلفة (قد تختلف أسماء الدوال)
            get_count = getattr(self.trade_manager, 'get_active_trades_count', None)
            active_trades = getattr(self.trade_manager, 'active_trades', {}) or {}

            if callable(get_count):
                current_count = int(get_count(symbol))
                total_trades = int(get_count())
            else:
                # ✅ fallback إذا لم تتوفر الدالة في TradeManager
                current_count = sum(1 for t in active_trades.values() if t.get('symbol') == symbol)
                total_trades = len(active_trades)

            max_per_symbol = self.config.get('MAX_TRADES_PER_SYMBOL', 20)
            if current_count >= max_per_symbol:
                logger.warning(f"🚫 وصل الحد الأقصى للصفقات للرمز {symbol}: {current_count}/{max_per_symbol} - التوقيت السعودي 🇸🇦")
                return False

            max_open_trades = self.config.get('MAX_OPEN_TRADES', 20)
            if total_trades >= max_open_trades:
                logger.warning(f"🚫 وصل الحد الأقصى الإجمالي للصفقات: {total_trades}/{max_open_trades} - التوقيت السعودي 🇸🇦")
                return False
                return False
            
            mode_limits = {
                'TRADING_MODE': self.config.get('MAX_TRADES_MODE_MAIN', 20),
                'TRADING_MODE1': self.config.get('MAX_TRADES_MODE1', 5),
                'TRADING_MODE2': self.config.get('MAX_TRADES_MODE2', 5)
            }
            
            current_mode_trades = self.trade_manager.count_trades_by_mode(symbol, mode_key)
            mode_limit = mode_limits.get(mode_key, 2)
            
            if current_mode_trades >= mode_limit:
                logger.warning(f"🚫 وصل الحد الأقصى للنمط {mode_key}: {current_mode_trades}/{mode_limit} - التوقيت السعودي 🇸🇦")
                return False
            
            return True
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في التحقق من إمكانية فتح الصفقة", e)
            return False

    def _check_strategy_conditions(self, trading_mode: str, signal_counts: Dict) -> Tuple[bool, List[str]]:
        """✅ FIXED: التحقق من شروط الاستراتيجية مع منع الإشارات المكررة من نفس المجموعة"""
        try:
            if not trading_mode or not isinstance(trading_mode, str):
                return False, []
                
            required_groups = trading_mode.split('_') if trading_mode else []
            conditions_met = True
            
            logger.info(f"🔍 فحص شروط الاستراتيجية: {trading_mode} -> {required_groups} - التوقيت السعودي 🇸🇦")
            
            # 🔥 التعديل: التحقق من وجود إشارات من مجموعات مختلفة وغير مكررة
            unique_groups_with_signals = 0
            
            for group in required_groups:
                if not group:
                    continue
                    
                group_key = group.lower()
                
                group_enabled_key = f"{group}_ENABLED"
                if not self.config.get(group_enabled_key, False):
                    logger.warning(f"🚫 المجموعة {group} غير مفعلة - التوقيت السعودي 🇸🇦")
                    conditions_met = False
                    break
                
                confirmations_key = f"REQUIRED_CONFIRMATIONS_{group}"
                required_confirmations = self.config.get(confirmations_key, 1)
                
                signal_count_key = f"g{group_key[-1]}" if group_key and group_key[-1].isdigit() else "g1"
                current_signals = signal_counts.get(signal_count_key, 0)
                
                if current_signals < required_confirmations:
                    logger.warning(f"🚫 إشارات غير كافية للمجموعة {group}: {current_signals}/{required_confirmations} - التوقيت السعودي 🇸🇦")
                    conditions_met = False
                    break
                else:
                    logger.info(f"✅ شروط المجموعة {group} متحققة: {current_signals}/{required_confirmations} - التوقيت السعودي 🇸🇦")
                    unique_groups_with_signals += 1
            
            # 🔥 التعديل الجديد: التأكد من وجود إشارات من مجموعتين مختلفتين على الأقل
            if len(required_groups) >= 2 and unique_groups_with_signals < 2:
                logger.warning(f"🚫 لا توجد إشارات كافية من مجموعات مختلفة: {unique_groups_with_signals} مجموعة فقط")
                conditions_met = False
            
            return conditions_met, required_groups
            
        except Exception as e:
            self._handle_error("💥 خطأ في فحص شروط الاستراتيجية", e)
            return False, []

    def _collect_trade_signals(self, symbol: str, direction: str, required_groups: List[str]) -> Dict:
        """جمع الإشارات المستخدمة في الصفقة"""
        try:
            group_key = symbol.upper().strip()
            groups = self.pending_signals.get(group_key, {})
            
            trade_info = {}
            
            for group in required_groups:
                if not group:
                    continue
                    
                group_type = f"{group.lower()}_bullish" if direction == 'buy' else f"{group.lower()}_bearish"
                
                if group_type in groups:
                    trade_info[f'{group.lower()}_signals'] = [signal['signal_type'] for signal in groups[group_type]]
                else:
                    trade_info[f'{group.lower()}_signals'] = []
            
            return trade_info
            
        except Exception as e:
            self._handle_error("💥 خطأ في جمع إشارات الصفقة", e)
            return {}

    def _open_trade(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> bool:
        """فتح صفقة جديدة"""
        try:
            # 🔧 FIXED: التحقق من وجود trade_manager
            if not hasattr(self, 'trade_manager') or self.trade_manager is None:
                logger.error("❌ trade_manager غير متوفر لفتح الصفقة")
                return False
            
            success = self.trade_manager.open_trade(symbol, direction, strategy_type, mode_key)
            
            if success:
                if mode_key not in self.mode_performance:
                    self.mode_performance[mode_key] = {'opened': 0, 'failed': 0}
                self.mode_performance[mode_key]['opened'] += 1
                logger.info(f"✅ تم فتح صفقة: {symbol} - {direction} - {strategy_type} - التوقيت السعودي 🇸🇦")
            else:
                if mode_key not in self.mode_performance:
                    self.mode_performance[mode_key] = {'opened': 0, 'failed': 0}
                self.mode_performance[mode_key]['failed'] += 1
                logger.error(f"❌ فشل فتح صفقة: {symbol} - {direction} - {strategy_type} - التوقيت السعودي 🇸🇦")
                
            return success
            
        except Exception as e:
            self._handle_error(f"💥 خطأ غير متوقع في فتح الصفقة", e)
            return False

    def _reset_used_signals_after_trade(self, symbol: str, direction: str, required_groups: List[str]) -> None:
        """🎯 تنظيف الإشارات المستخدمة بعد فتح الصفقة بنجاح - الإصدار المصحح"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return

            groups = self.pending_signals[group_key]
            
            for group in required_groups:
                if not group:
                    continue
                    
                group_type = f"{group.lower()}_bullish" if direction == 'buy' else f"{group.lower()}_bearish"
                
                if group_type in groups and groups[group_type]:
                    # 🧹 مسح جميع الإشارات المستخدمة في هذه الصفقة
                    original_count = len(groups[group_type])  # 🔧 FIXED: تعريف هنا
                    groups[group_type].clear()
                    logger.info(f"🧹 تم تنظيف {original_count} إشارة من {group_type} بعد فتح الصفقة")
            
            logger.info(f"✅ تم تنظيف الإشارات المستخدمة لـ {symbol} بعد فتح الصفقة بنجاح")
                
        except Exception as e:
            self._handle_error(f"⚠️ خطأ في تنظيف الإشارات بعد الصفقة", e)

    def _reset_used_signals(self, symbol: str, direction: str, trade_results: List[Dict]) -> None:
        """🎯 FIXED: إعادة تعيين الإشارات المستخدمة باستخدام الإعدادات من .env - الإصدار المصحح"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return

            groups = self.pending_signals[group_key]
            current_time = saudi_time.now()
            
            for trade in trade_results:
                required_groups = trade.get('strategy_type', '').split('_')
                
                for group in required_groups:
                    if not group:
                        continue
                        
                    group_type = f"{group.lower()}_bullish" if direction == 'buy' else f"{group.lower()}_bearish"
                    
                    if group_type in groups and groups[group_type]:
                        # 🎯 استخدام عتبة التنظيف من .env بدلاً من القيمة الثابتة
                        retention_threshold = self.signal_cleanup_threshold
                        
                        # 🔧 FIXED: تعريف original_count هنا
                        original_count = len(groups[group_type])
                        
                        groups[group_type] = deque(
                            [signal for signal in groups[group_type]
                             if (current_time - signal.get('timestamp', current_time)).total_seconds() >= retention_threshold],
                            maxlen=200
                        )
                        cleaned_count = original_count - len(groups[group_type])
                        
                        if cleaned_count > 0:
                            logger.info(f"🔄 تنظيف {cleaned_count} إشارة مستخدمة من {group_type}")
            
            logger.info(f"✅ تم تنظيف الإشارات المستخدمة لـ {symbol} - جاهز لإشارات جديدة")
                
        except Exception as e:
            self._handle_error(f"⚠️ خطأ في معالجة الإشارات المستخدمة", e)

    def cleanup_expired_signals(self, symbol: str) -> None:
        """🎯 FIXED: تنظيف الإشارات المنتهية باستخدام الإعدادات من .env"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return

            # ⏰ استخدام وقت انتهاء الصلاحية من .env
            ttl_minutes = self.signal_ttl_minutes
            expiration_time = saudi_time.now() - timedelta(minutes=ttl_minutes)

            with self.signal_lock:
                cleaned_count = 0
                for group_type in list(self.pending_signals[group_key].keys()):
                    if group_type == "_meta":
                        continue
                    
                    if group_type in self.pending_signals[group_key]:
                        original_count = len(self.pending_signals[group_key][group_type])
                        self.pending_signals[group_key][group_type] = deque(
                            [signal for signal in self.pending_signals[group_key][group_type]
                             if signal.get('timestamp', saudi_time.now()) > expiration_time],
                            maxlen=200
                        )
                        cleaned_count += (original_count - len(self.pending_signals[group_key][group_type]))

                if cleaned_count > 0:
                    logger.info(f"🧹 تم تنظيف {cleaned_count} إشارة منتهية لـ {symbol} (TTL: {ttl_minutes} دقيقة) - التوقيت السعودي 🇸🇦")

        except Exception as e:
            self._handle_error(f"⚠️ خطأ في تنظيف الإشارات المنتهية الصلاحية", e)

    def get_group_stats(self, symbol: str) -> Optional[Dict]:
        """✅ FIXED: الحصول على إحصائيات المجموعات"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                return None
                
            groups = self.pending_signals[group_key]
            
            return {
                'symbol': symbol,
                'group1_bullish': len(groups.get('group1_bullish', [])),
                'group1_bearish': len(groups.get('group1_bearish', [])),
                'group2_bullish': len(groups.get('group2_bullish', [])),
                'group2_bearish': len(groups.get('group2_bearish', [])),
                'group3_bullish': len(groups.get('group3_bullish', [])),
                'group3_bearish': len(groups.get('group3_bearish', [])),
                'group4_bullish': len(groups.get('group4_bullish', [])),
                'group4_bearish': len(groups.get('group4_bearish', [])),
                'group5_bullish': len(groups.get('group5_bullish', [])),
                'group5_bearish': len(groups.get('group5_bearish', [])),
                'total_signals': sum(len(groups[gt]) for gt in groups if gt != "_meta" and isinstance(groups[gt], deque)),
                'created_at': groups.get('_meta', {}).get('created_at'),
                'updated_at': groups.get('_meta', {}).get('updated_at'),
                'timezone': 'Asia/Riyadh 🇸🇦'
            }
        except Exception as e:
            self._handle_error(f"⚠️ خطأ في إحصائيات المجموعات", e)
            return None

    def get_performance_metrics(self) -> Dict:
        """الحصول على مقاييس الأداء بالتوقيت السعودي"""
        return {
            'error_count': len(self.error_log),
            'mode_performance': self.mode_performance.copy(),
            'signal_hashes_count': len(self.signal_hashes),
            'last_hash_cleanup': self.last_hash_cleanup.isoformat(),
            'used_signals_count': sum(len(signals) for signals in self.used_signals_for_trades.values()),
            'timezone': 'Asia/Riyadh 🇸🇦',
            'timing_settings': {
                'duplicate_block_time': self.duplicate_block_time,
                'duplicate_cleanup_interval': self.duplicate_cleanup_interval,
                'cleanup_factor': self.cleanup_factor,
                'signal_ttl_minutes': self.signal_ttl_minutes,
                'signal_cleanup_threshold': self.signal_cleanup_threshold
            },
            'memory_usage': {
                'pending_signals_count': len(self.pending_signals),
                'error_log_size': len(self.error_log),
                'signal_hashes_size': len(self.signal_hashes)
            }
        }

    def force_open_trade(self, symbol: str, direction: str, strategy_type: str = "MANUAL", mode_key: str = "TRADING_MODE") -> bool:
        """فتح صفقة قسراً بالتوقيت السعودي"""
        try:
            logger.info(f"🔧 محاولة فتح صفقة قسراً: {symbol} - {direction} - {strategy_type} - التوقيت السعودي 🇸🇦")
            
            # 🔧 FIXED: التحقق من وجود trade_manager
            if not hasattr(self, 'trade_manager') or self.trade_manager is None:
                logger.error("❌ trade_manager غير متوفر لفتح الصفقة القسرية")
                return False
                
            success = self.trade_manager.open_trade(symbol, direction, strategy_type, mode_key)
            
            if success:
                logger.info(f"✅ تم فتح الصفقة القسرية بنجاح: {symbol} - التوقيت السعودي 🇸🇦")
            else:
                logger.error(f"❌ فشل فتح الصفقة القسرية: {symbol} - التوقيت السعودي 🇸🇦")
                
            return success
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في فتح الصفقة القسرية لـ {symbol}", e)
            return False

    def cleanup_memory(self) -> Dict:
        """🧹 تنظيف الذاكرة وإدارة التخزين"""
        try:
            initial_total = sum(
                len(self.pending_signals[symbol][gt]) 
                for symbol in self.pending_signals 
                for gt in self.pending_signals[symbol] 
                if gt != "_meta"
            )
            
            # تنظيف الإشارات المنتهية لكل رمز
            for symbol in list(self.pending_signals.keys()):
                self.cleanup_expired_signals(symbol)
            
            # تنظيف تجزئات الإشارات القديمة
            self._cleanup_old_hashes()
            
            # تنظيف error_log القديم
            if len(self.error_log) > 500:
                excess = len(self.error_log) - 500
                for _ in range(excess):
                    if self.error_log:
                        self.error_log.popleft()
            
            # تنظيف mode_performance القديم
            current_time = saudi_time.now()
            for mode_key in list(self.mode_performance.keys()):
                if mode_key not in self._get_active_modes():
                    # حذف بيانات الأنماط غير المفعلة
                    del self.mode_performance[mode_key]
            
            final_total = sum(
                len(self.pending_signals[symbol][gt]) 
                for symbol in self.pending_signals 
                for gt in self.pending_signals[symbol] 
                if gt != "_meta"
            )
            
            cleaned = initial_total - final_total
            
            logger.info(f"🧹 تنظيف الذاكرة: تم تنظيف {cleaned} إشارة - التوقيت السعودي 🇸🇦")
            
            return {
                'initial_count': initial_total,
                'final_count': final_total,
                'cleaned': cleaned,
                'timestamp': current_time.isoformat(),
                'timezone': 'Asia/Riyadh 🇸🇦'
            }
            
        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف الذاكرة", e)
            return {'error': str(e)}
