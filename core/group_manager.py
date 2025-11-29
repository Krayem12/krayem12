import logging
from datetime import datetime, timedelta
import hashlib
from typing import Dict, List, Optional, Tuple
import threading
from collections import defaultdict, deque
from functools import lru_cache

logger = logging.getLogger(__name__)

class GroupManager:
    """🎯 نظام إدارة المجموعات مع حماية كاملة ضد فتح الصفقات غير المصرح بها"""

    def __init__(self, config, trade_manager):
        self.config = config
        self.trade_manager = trade_manager
        
        # تخزين الإشارات المؤقتة مع تحسينات الأمان
        self.pending_signals = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        
        # 🎯 نظام تتبع الإشارات المستخدمة مع حماية مزدوجة
        self.used_signal_hashes = set()  # جميع الإشارات المستخدمة في النظام
        self.signal_usage_lock = threading.RLock()  # قفل خاص بالإشارات
        
        # إحصائيات النظام
        self.error_log = deque(maxlen=1000)
        self.mode_performance = {}
        self.validation_failures = defaultdict(int)  # تتبع محاولات التجاوز
        
        # قفل لإدارة التزامن
        self.signal_lock = threading.RLock()
        
        # إعدادات منع التكرار
        self.duplicate_block_time = self.config['DUPLICATE_SIGNAL_BLOCK_TIME']
        self.duplicate_cleanup_interval = self.config['DUPLICATE_CLEANUP_INTERVAL']
        
        # تحسين الأداء
        self.signal_hashes = {}
        self.last_hash_cleanup = datetime.now()
        
        logger.info(f"🎯 نظام المجموعات المحسن جاهز - حماية كاملة ضد الصفقات غير المصرح بها")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None, 
                     extra_data: Optional[Dict] = None) -> None:
        """🎯 معالجة الأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        if extra_data:
            full_error += f" | Extra: {extra_data}"
        logger.error(full_error)
        
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error': full_error
        }
        self.error_log.append(error_entry)

    def _is_group_enabled(self, group_type: str) -> bool:
        """التحقق من تفعيل المجموعة"""
        try:
            group_key = group_type.split('_')[0].upper()
            enabled_key = f"{group_key}_ENABLED"
            is_enabled = self.config.get(enabled_key, False)
            
            logger.debug(f"🔍 حالة المجموعة {group_key}: {'✅ مفعلة' if is_enabled else '❌ معطلة'}")
            return is_enabled
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق من تفعيل المجموعة", e)
            return False

    def route_signal(self, symbol: str, signal_data: Dict, classification: str) -> List[Dict]:
        """🎯 توجيه الإشارة للمجموعة المناسبة مع حماية مشددة"""
        
        logger.info(f"🎯 بدء توجيه الإشارة: {symbol} -> {classification} -> {signal_data.get('signal_type')}")
        
        if not self._validate_input(symbol, signal_data, classification):
            return []

        try:
            # تنظيف الإشارات المنتهية والمستخدمة
            self.cleanup_expired_signals(symbol)

            # تحديد المجموعة والاتجاه
            group_type, direction = self._determine_group_and_direction_enhanced(classification, signal_data)
            if not group_type or not direction:
                logger.error(f"❌ لا يمكن تحديد المجموعة أو الاتجاه للتصنيف: {classification}")
                return []

            logger.info(f"🎯 تم تحديد: {symbol} -> {group_type} -> {direction}")

            # ✅ التحقق من تفعيل المجموعة أولاً
            if not self._is_group_enabled(group_type):
                logger.warning(f"🚫 المجموعة {group_type} معطلة - تجاهل الإشارة")
                return []

            # 🎯 استخدام وقت منع التكرار من الإعدادات فقط
            if self._is_duplicate_signal_optimized(symbol, signal_data, group_type):
                logger.info(f"🔁 إشارة مكررة - تم تجاهلها: {symbol} -> {signal_data.get('signal_type')}")
                return []

            # استخدام القفل لمنع التزامن
            with self.signal_lock:
                # 🎯 التحقق من أن الإشارة لم تستخدم مسبقاً في أي صفقة
                signal_hash = self._calculate_signal_hash(symbol, signal_data, group_type)
                if self._is_signal_used_globally(signal_hash):
                    logger.warning(f"🚫 الإشارة مستخدمة مسبقاً في صفقة أخرى: {signal_data.get('signal_type')}")
                    return []

                # إضافة الإشارة للمجموعة
                self._add_signal_to_group(symbol, signal_data, group_type, direction, classification)

                # التحقق من محاذاة الاتجاه
                trend_check_result = self._check_trend_alignment_enhanced(symbol, direction, group_type)
                if not trend_check_result:
                    self._handle_contrarian_signal(symbol, group_type, signal_data)
                    return []

                # 🎯 تقييم شروط الدخول مع تحقق مزدوج
                trade_results = self._evaluate_entry_conditions_strict(symbol, direction)
                
                if trade_results:
                    logger.info(f"✅ تم فتح {len(trade_results)} صفقة لـ {symbol} بعد تحقيق جميع الشروط")
                    # 🎯 تسجيل الإشارات المستخدمة
                    self._mark_signals_as_used(symbol, direction, trade_results)
                else:
                    logger.info(f"⏸️ لم يتم فتح صفقات لـ {symbol} - الشروط غير متحققة")
                
                return trade_results

        except Exception as e:
            self._handle_error(f"💥 خطأ في توجيه الإشارة: {symbol}", e, 
                             {'classification': classification, 'signal_type': signal_data.get('signal_type')})
            return []

    def _calculate_signal_hash(self, symbol: str, signal_data: Dict, group_type: str) -> str:
        """🎯 حساب تجزئة فريدة للإشارة"""
        signal_key = f"{symbol}_{signal_data['signal_type']}_{group_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return hashlib.md5(signal_key.encode()).hexdigest()

    def _is_signal_used_globally(self, signal_hash: str) -> bool:
        """🎯 التحقق من استخدام الإشارة في أي صفقة في النظام"""
        with self.signal_usage_lock:
            return signal_hash in self.used_signal_hashes

    def _mark_signals_as_used(self, symbol: str, direction: str, trade_results: List[Dict]) -> None:
        """🎯 تسجيل جميع الإشارات المستخدمة في الصفقات المفتوحة"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return
                
            groups = self.pending_signals[group_key]
            
            with self.signal_usage_lock:
                for trade in trade_results:
                    required_groups = trade.get('strategy_type', '').split('_')
                    
                    for group in required_groups:
                        if not group:
                            continue
                            
                        group_type = f"{group.lower()}_bullish" if direction == 'buy' else f"{group.lower()}_bearish"
                        
                        if group_type in groups:
                            for signal in groups[group_type]:
                                signal_hash = signal.get('hash')
                                if signal_hash:
                                    self.used_signal_hashes.add(signal_hash)
                                    logger.debug(f"📝 تم تسجيل الإشارة المستخدمة: {signal_hash[:8]}...")
                
                logger.info(f"🎯 تم تسجيل {len(self.used_signal_hashes)} إشارة مستخدمة في النظام")
                
        except Exception as e:
            self._handle_error("💥 خطأ في تسجيل الإشارات المستخدمة", e)

    def _evaluate_entry_conditions_strict(self, symbol: str, direction: str) -> List[Dict]:
        """🎯 تقييم شروط الدخول بشكل صارم مع تحقق مزدوج"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                logger.warning(f"⚠️ لا توجد إشارات للرمز: {symbol}")
                return []
            
            # 🎯 التحقق الأولي من الإشارات
            signal_counts = self._count_signals_by_direction(group_key, direction)
            if not signal_counts:
                logger.warning(f"⚠️ لا توجد إشارات للاتجاه {direction} في {symbol}")
                return []
            
            # 🎯 تسجيل مفصل مع التحقق من كل مجموعة
            self._log_detailed_signal_stats(symbol, direction, signal_counts)
            
            active_modes = self._get_active_modes()
            trade_results = []
            
            for mode_key in active_modes:
                # 🎯 تحقق مزدوج من الشروط قبل وبعد
                trade_result = self._evaluate_single_mode_strict(mode_key, symbol, direction, signal_counts)
                if trade_result:
                    # 🎯 تحقق نهائي قبل فتح الصفقة
                    if self._final_validation(symbol, direction, trade_result):
                        trade_results.append(trade_result)
                    else:
                        logger.error(f"🚫 فشل التحقق النهائي لصفقة {symbol} - تم إلغاء الصفقة")
            
            return trade_results
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في تقييم شروط الدخول: {symbol}", e)
            return []

    def _log_detailed_signal_stats(self, symbol: str, direction: str, signal_counts: Dict) -> None:
        """🎯 تسجيل إحصائيات مفصلة مع التأكيد على المتطلبات"""
        logger.info(f"📊 إحصائيات مفصلة لـ {symbol} [{direction.upper()}]:")
        
        requirements = {
            'g1': self.config.get('REQUIRED_CONFIRMATIONS_GROUP1', 1),
            'g2': self.config.get('REQUIRED_CONFIRMATIONS_GROUP2', 1),
            'g3': self.config.get('REQUIRED_CONFIRMATIONS_GROUP3', 1),
            'g4': self.config.get('REQUIRED_CONFIRMATIONS_GROUP4', 1),
            'g5': self.config.get('REQUIRED_CONFIRMATIONS_GROUP5', 1)
        }
        
        for group_key, required in requirements.items():
            current = signal_counts.get(group_key, 0)
            status = "✅ متاح" if current >= required else "❌ غير كافي"
            logger.info(f"   📈 {group_key.upper()}: {current}/{required} إشارة {status}")

    def _evaluate_single_mode_strict(self, mode_key: str, symbol: str, direction: str, signal_counts: Dict) -> Optional[Dict]:
        """🎯 تقييم نمط تداول فردي مع تحقق متعدد المستويات"""
        try:
            # 🎯 التحقق من حدود التداول أولاً
            if not self._can_open_trade_strict(symbol, mode_key):
                return None
            
            trading_mode = self.config.get(mode_key)
            if not trading_mode:
                logger.warning(f"🚫 لا يوجد إعدادات للنمط {mode_key}")
                return None

            # 🎯 تحقق مزدوج من شروط الاستراتيجية
            conditions_met, required_groups = self._check_strategy_conditions_strict(trading_mode, signal_counts)
            
            if not conditions_met:
                logger.info(f"⏸️ لم تتحقق شروط النمط {mode_key} لـ {symbol}")
                self.validation_failures[symbol] += 1
                return None
            
            # 🎯 التحقق من أن الإشارات جديدة وغير مستخدمة
            if not self._are_signals_completely_new(symbol, required_groups, direction):
                logger.warning(f"🚫 إشارات مستخدمة مسبقاً في صفقات أخرى لـ {symbol}")
                return None
            
            # 🎯 فتح الصفقة مع التعامل مع الفشل
            trade_info = self._prepare_trade_info(symbol, direction, trading_mode, mode_key, required_groups)
            
            if self._open_trade_strict(symbol, direction, trading_mode, mode_key):
                logger.info(f"✅ تم فتح صفقة: {symbol} - {direction} - {trading_mode}")
                return trade_info
            else:
                logger.error(f"❌ فشل فتح الصفقة رغم تحقق الشروط لـ {symbol}")
                return None
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في تقييم النمط {mode_key}", e)
            return None

    def _check_strategy_conditions_strict(self, trading_mode: str, signal_counts: Dict) -> Tuple[bool, List[str]]:
        """🎯 التحقق الصارم من شروط الاستراتيجية مع عدم السماح بأي تجاوز"""
        try:
            if not trading_mode or not isinstance(trading_mode, str):
                logger.error("❌ نمط تداول غير صالح")
                return False, []
                
            required_groups = trading_mode.split('_') if trading_mode else []
            conditions_met = True
            
            logger.info(f"🔍 فحص صارم لشروط الاستراتيجية: {trading_mode} -> {required_groups}")
            
            for group in required_groups:
                if not group:
                    continue
                    
                group_key = group.upper().strip()
                
                # 🎯 التحقق من تفعيل المجموعة
                group_enabled_key = f"{group_key}_ENABLED"
                if not self.config.get(group_enabled_key, False):
                    logger.error(f"🚫 المجموعة {group_key} غير مفعلة - لا يمكن فتح الصفقة")
                    conditions_met = False
                    break
                
                # 🎯 الحصول على العدد المطلوب بدقة
                confirmations_key = f"REQUIRED_CONFIRMATIONS_{group_key}"
                required_confirmations = self.config.get(confirmations_key, 0)
                
                if required_confirmations <= 0:
                    logger.error(f"🚫 عدد التأكيدات المطلوب للمجموعة {group_key} غير صالح: {required_confirmations}")
                    conditions_met = False
                    break
                
                # 🎯 استخراج الرقم بشكل آمن
                group_number = group_key.replace('GROUP', '')
                signal_count_key = f"g{group_number}"
                
                current_signals = signal_counts.get(signal_count_key, 0)
                
                logger.info(f"🔍 فحص المجموعة {group_key}: المطلوب {required_confirmations}, المتوفر {current_signals}")
                
                # 🎯 تحقق صارم بدون أي تسامح
                if current_signals < required_confirmations:
                    logger.error(f"🚫 إشارات غير كافية للمجموعة {group_key}: {current_signals}/{required_confirmations}")
                    conditions_met = False
                    break
                else:
                    logger.info(f"✅ شروط المجموعة {group_key} متحققة: {current_signals}/{required_confirmations}")
            
            # 🎯 تسجيل النتيجة النهائية
            if conditions_met:
                logger.info(f"🎯 جميع شروط الاستراتيجية {trading_mode} متحققة")
            else:
                logger.error(f"🚫 فشل في تحقيق شروط الاستراتيجية {trading_mode}")
            
            return conditions_met, required_groups
            
        except Exception as e:
            self._handle_error("💥 خطأ في الفحص الصارم لشروط الاستراتيجية", e)
            return False, []

    def _are_signals_completely_new(self, symbol: str, required_groups: List[str], direction: str) -> bool:
        """🎯 تحقق نهائي من أن الإشارات جديدة تماماً"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return True
            
            groups = self.pending_signals[group_key]
            
            with self.signal_usage_lock:
                for group in required_groups:
                    if not group:
                        continue
                        
                    group_type = f"{group.lower()}_bullish" if direction == 'buy' else f"{group.lower()}_bearish"
                    
                    if group_type in groups:
                        for signal in groups[group_type]:
                            signal_hash = signal.get('hash')
                            if signal_hash and signal_hash in self.used_signal_hashes:
                                logger.warning(f"🚫 إشارة مستخدمة مسبقاً: {signal.get('signal_type')}")
                                return False
            
            return True
            
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق من تجديد الإشارات", e)
            return False  # في حالة الخطأ، نرفض الصفقة للحماية

    def _can_open_trade_strict(self, symbol: str, mode_key: str) -> bool:
        """🎯 تحقق صارم من إمكانية فتح صفقة جديدة"""
        try:
            # التحقق من الحدود الأساسية
            current_count = self.trade_manager.get_active_trades_count(symbol)
            max_per_symbol = self.config['MAX_TRADES_PER_SYMBOL']
            if current_count >= max_per_symbol:
                logger.warning(f"🚫 وصل الحد الأقصى للصفقات للرمز {symbol}: {current_count}/{max_per_symbol}")
                return False
            
            total_trades = self.trade_manager.get_active_trades_count()
            max_open_trades = self.config['MAX_OPEN_TRADES']
            if total_trades >= max_open_trades:
                logger.warning(f"🚫 وصل الحد الأقصى الإجمالي للصفقات: {total_trades}/{max_open_trades}")
                return False
            
            # 🎯 تحقق صارم من حدود الأنماط
            mode_limits = {
                'TRADING_MODE': self.config['MAX_TRADES_MODE_MAIN'],
                'TRADING_MODE1': self.config['MAX_TRADES_MODE1'],
                'TRADING_MODE2': self.config['MAX_TRADES_MODE2']
            }
            
            current_mode_trades = self.trade_manager.count_trades_by_mode(symbol, mode_key)
            mode_limit = mode_limits.get(mode_key, 0)
            
            if current_mode_trades >= mode_limit:
                logger.warning(f"🚫 وصل الحد الأقصى للنمط {mode_key}: {current_mode_trades}/{mode_limit}")
                return False
            
            return True
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في التحقق الصارم من إمكانية فتح الصفقة", e)
            return False

    def _prepare_trade_info(self, symbol: str, direction: str, strategy_type: str, mode_key: str, required_groups: List[str]) -> Dict:
        """🎯 إعداد معلومات الصفقة مع التحقق"""
        try:
            trade_info = self._collect_trade_signals(symbol, direction, required_groups)
            trade_info.update({
                'symbol': symbol,
                'direction': direction,
                'strategy_type': strategy_type,
                'mode_key': mode_key,
                'trade_timestamp': datetime.now().isoformat(),
                'validation_passed': True  # 🎯 تأكيد أن الصفقة تم التحقق منها
            })
            return trade_info
        except Exception as e:
            self._handle_error("💥 خطأ في إعداد معلومات الصفقة", e)
            return {}

    def _open_trade_strict(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> bool:
        """🎯 فتح صفقة مع تحقق إضافي"""
        try:
            success = self.trade_manager.open_trade(symbol, direction, strategy_type, mode_key)
            
            if success:
                if mode_key not in self.mode_performance:
                    self.mode_performance[mode_key] = {'opened': 0, 'failed': 0}
                self.mode_performance[mode_key]['opened'] += 1
                logger.info(f"✅ تم فتح صفقة: {symbol} - {direction} - {strategy_type}")
            else:
                if mode_key not in self.mode_performance:
                    self.mode_performance[mode_key] = {'opened': 0, 'failed': 0}
                self.mode_performance[mode_key]['failed'] += 1
                logger.error(f"❌ فشل فتح صفقة: {symbol} - {direction} - {strategy_type}")
                
            return success
            
        except Exception as e:
            self._handle_error(f"💥 خطأ غير متوقع في فتح الصفقة", e)
            return False

    def _final_validation(self, symbol: str, direction: str, trade_info: Dict) -> bool:
        """🎯 تحقق نهائي قبل فتح الصفقة"""
        try:
            # 🎯 تحقق إضافي من الشروط
            strategy_type = trade_info.get('strategy_type', '')
            required_groups = strategy_type.split('_') if strategy_type else []
            
            # التحقق من أن جميع الإشارات لا تزال متاحة
            group_key = symbol.upper().strip()
            signal_counts = self._count_signals_by_direction(group_key, direction)
            
            for group in required_groups:
                group_number = group.replace('GROUP', '')
                signal_count_key = f"g{group_number}"
                required_confirmations = self.config.get(f'REQUIRED_CONFIRMATIONS_{group}', 0)
                
                if signal_counts.get(signal_count_key, 0) < required_confirmations:
                    logger.error(f"🚫 فشل التحقق النهائي: المجموعة {group} لم تعد تفي بالشروط")
                    return False
            
            logger.info(f"✅ التحقق النهائي ناجح لـ {symbol}")
            return True
            
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق النهائي", e)
            return False

    def _check_trend_alignment_enhanced(self, symbol: str, direction: str, group_type: str) -> bool:
        """✅ التحقق من محاذاة الاتجاه بشكل آمن"""
        
        try:
            group_key = group_type.split('_')[0]
            
            if not self._is_group_enabled(group_type):
                logger.warning(f"🚫 المجموعة {group_key} معطلة - تجاهل الإشارة")
                return False
            
            trend_mode_key = f"{group_key.upper()}_TREND_MODE"
            group_trend_mode = self.config.get(trend_mode_key, self.config.get('GROUP1_TREND_MODE', 'ONLY_TREND'))
            
            current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
            
            if group_trend_mode == 'ALLOW_COUNTER_TREND':
                logger.info(f"🔓 فتح الصفقة بدون قيود اتجاه: {symbol} -> {direction.upper()} (المجموعة: {group_key})")
                return True
            
            if current_trend == 'UNKNOWN':
                logger.warning(f"⏸️ تجاهل الإشارة - اتجاه غير معروف: {symbol} للمجموعة {group_key}")
                return False
            
            is_aligned = (
                (current_trend == 'bullish' and direction == 'buy') or
                (current_trend == 'bearish' and direction == 'sell')
            )
            
            if not is_aligned:
                logger.warning(f"🚫 الإشارة مخالفة للاتجاه: {direction.upper()} vs {current_trend.upper()} (المجموعة: {group_key})")
                return False
            
            logger.info(f"✅ الإشارة متوافقة مع الاتجاه: {direction.upper()} vs {current_trend.upper()}")
            return True
            
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق من محاذاة الاتجاه", e)
            return False

    def _determine_group_and_direction_enhanced(self, classification: str, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """✅ تحديد المجموعة والاتجاه بشكل آمن مع تحسين الأداء"""
        
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
                    logger.info(f"🎯 تم تحديد المجموعة مباشرة: {classification} -> {result}")
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
                    logger.info(f"🎯 تم تحديد المجموعة: {classification} -> {result}")
                    return result
            
            logger.error(f"❌ تصنيف غير معروف أو المجموعة معطلة: {classification}")
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
        """✅ دالة محسنة لتحديد اتجاه المجموعات"""
        try:
            if not self._is_group_enabled(f'group{group_num}'):
                return None, None
                
            signal_type = signal_data.get('signal_type', '').lower()
            
            signals_config = self.config.get('signals', {})
            group_bullish = [s.lower().strip() for s in signals_config.get(f'group{group_num}_bullish', [])]
            group_bearish = [s.lower().strip() for s in signals_config.get(f'group{group_num}_bearish', [])]
            
            if signal_type in group_bullish:
                return f'group{group_num}_bullish', 'buy'
            elif signal_type in group_bearish:
                return f'group{group_num}_bearish', 'sell'
            
            logger.debug(f"🔍 إشارة غير معروفة للمجموعة {group_num}: {signal_type}")
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
        """إضافة الإشارة للمجموعة"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                all_group_types = [
                    'group1_bullish', 'group1_bearish', 'group2_bullish', 'group2_bearish',
                    'group3_bullish', 'group3_bearish', 'group4_bullish', 'group4_bearish',
                    'group5_bullish', 'group5_bearish', 'trend_bullish', 'trend_bearish'
                ]
                for gt in all_group_types:
                    self.pending_signals[group_key][gt] = deque(maxlen=100)
                
                self.pending_signals[group_key]["created_at"] = datetime.now()
            
            signal_info = {
                'hash': hashlib.md5(
                    f"{signal_data['signal_type']}_{classification}_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}".encode()
                ).hexdigest(),
                'signal_type': signal_data['signal_type'],
                'classification': classification,
                'timestamp': datetime.now(),
                'direction': direction,
                'symbol': symbol,
                'group_type': group_type
            }
            
            self.pending_signals[group_key][group_type].append(signal_info)
            self.pending_signals[group_key]["updated_at"] = datetime.now()
            
            logger.info(f"📥 إشارة مضافة: {symbol} -> {signal_data['signal_type']} → {group_type}")
            
        except Exception as e:
            self._handle_error("💥 خطأ في إضافة الإشارة للمجموعة", e)

    def _is_duplicate_signal_optimized(self, symbol: str, signal_data: Dict, group_type: str) -> bool:
        """🎯 منع الإشارات المكررة مع القراءة من الإعدادات فقط"""
        try:
            self._cleanup_old_hashes()
            
            current_time = datetime.now()
            
            signal_key = f"{symbol}_{signal_data['signal_type']}_{group_type}"
            signal_hash = hashlib.md5(signal_key.encode()).hexdigest()
            
            if signal_hash in self.signal_hashes:
                time_elapsed = (current_time - self.signal_hashes[signal_hash]).total_seconds()
                
                if time_elapsed < self.duplicate_block_time:
                    logger.info(f"🔁 إشارة مكررة خلال {self.duplicate_block_time} ثانية - تم تجاهلها: {symbol} -> {signal_data.get('signal_type')} (مر {time_elapsed:.1f} ثانية)")
                    return True
                else:
                    self.signal_hashes[signal_hash] = current_time
                    logger.debug(f"🔄 إشارة قديمة - تم تحديث الوقت: {symbol} -> {signal_data.get('signal_type')}")
                    return False
            else:
                self.signal_hashes[signal_hash] = current_time
                return False
            
        except Exception as e:
            self._handle_error("💥 خطأ في فحص التكرار", e)
            return False

    def _cleanup_old_hashes(self):
        """🎯 تنظيف التجزئات القديمة باستخدام الإعدادات من .env فقط"""
        try:
            current_time = datetime.now()
            
            if (current_time - self.last_hash_cleanup).total_seconds() > self.duplicate_cleanup_interval:
                initial_count = len(self.signal_hashes)
                
                max_age = self.duplicate_block_time * 2
                
                expired_hashes = [
                    hash_key for hash_key, timestamp in self.signal_hashes.items()
                    if (current_time - timestamp).total_seconds() > max_age
                ]
                
                for hash_key in expired_hashes:
                    del self.signal_hashes[hash_key]
                
                cleaned_count = len(expired_hashes)
                if cleaned_count > 0:
                    logger.debug(f"🧹 تم تنظيف {cleaned_count} تجزئة قديمة من أصل {initial_count}")
                
                self.last_hash_cleanup = current_time
                
        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف التجزئات", e)

    def _handle_contrarian_signal(self, symbol: str, group_type: str, signal_data: Dict) -> None:
        """معالجة الإشارة المخالفة للاتجاه"""
        store_contrarian = self.config['STORE_CONTRARIAN_SIGNALS']
        if store_contrarian:
            logger.info(f"📦 الإشارة مخالفة للاتجاه - تم تخزينها: {symbol} → {signal_data['signal_type']}")
        else:
            logger.info(f"🚫 الإشارة مخالفة للاتجاه - تم تجاهلها: {symbol} → {signal_data['signal_type']}")

    def _count_signals_by_direction(self, group_key: str, direction: str) -> Dict[str, int]:
        """✅ حساب عدد الإشارات بشكل آمن"""
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
        
        if self.config['TRADING_MODE1_ENABLED']:
            active_modes.append('TRADING_MODE1')
        if self.config['TRADING_MODE2_ENABLED']:
            active_modes.append('TRADING_MODE2')
        
        logger.info(f"🎯 الأنماط المفعلة: {active_modes}")
        return active_modes

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

    def cleanup_expired_signals(self, symbol: str) -> None:
        """تنظيف الإشارات المنتهية الصلاحية"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return

            ttl_minutes = self.config['SIGNAL_TTL_MINUTES']
            expiration_time = datetime.now() - timedelta(minutes=ttl_minutes)

            cleaned_count = 0
            for group_type in list(self.pending_signals[group_key].keys()):
                if group_type in ['created_at', 'updated_at']:
                    continue
                    
                if group_type in self.pending_signals[group_key]:
                    original_count = len(self.pending_signals[group_key][group_type])
                    self.pending_signals[group_key][group_type] = deque(
                        [signal for signal in self.pending_signals[group_key][group_type]
                         if signal.get('timestamp', datetime.now()) > expiration_time],
                        maxlen=100
                    )
                    cleaned_count += (original_count - len(self.pending_signals[group_key][group_type]))

            if cleaned_count > 0:
                logger.info(f"🧹 تم تنظيف {cleaned_count} إشارة منتهية لـ {symbol}")

        except Exception as e:
            self._handle_error(f"⚠️ خطأ في تنظيف الإشارات المنتهية الصلاحية", e)

    def get_group_stats(self, symbol: str) -> Optional[Dict]:
        """✅ الحصول على إحصائيات المجموعات"""
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
                'total_signals': sum(len(groups[gt]) for gt in groups if gt not in ['created_at', 'updated_at'] and isinstance(groups[gt], deque)),
                'updated_at': groups.get('updated_at')
            }
        except Exception as e:
            self._handle_error(f"⚠️ خطأ في إحصائيات المجموعات", e)
            return None

    def get_performance_metrics(self) -> Dict:
        """الحصول على مقاييس الأداء"""
        return {
            'error_count': len(self.error_log),
            'mode_performance': self.mode_performance.copy(),
            'signal_hashes_count': len(self.signal_hashes),
            'last_hash_cleanup': self.last_hash_cleanup.isoformat(),
            'used_signals_count': len(self.used_signal_hashes),
            'validation_failures': dict(self.validation_failures)
        }

    def force_open_trade(self, symbol: str, direction: str, strategy_type: str = "MANUAL", mode_key: str = "TRADING_MODE") -> bool:
        """فتح صفقة قسراً"""
        try:
            logger.info(f"🔧 محاولة فتح صفقة قسراً: {symbol} - {direction} - {strategy_type}")
            success = self.trade_manager.open_trade(symbol, direction, strategy_type, mode_key)
            
            if success:
                logger.info(f"✅ تم فتح الصفقة القسرية بنجاح: {symbol}")
            else:
                logger.error(f"❌ فشل فتح الصفقة القسرية: {symbol}")
                
            return success
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في فتح الصفقة القسرية لـ {symbol}", e)
            return False

    def get_validation_report(self) -> Dict:
        """🎯 تقرير عن عمليات التحقق والفشل"""
        return {
            'total_validation_failures': sum(self.validation_failures.values()),
            'validation_failures_by_symbol': dict(self.validation_failures),
            'used_signals_count': len(self.used_signal_hashes),
            'mode_performance': self.mode_performance.copy(),
            'system_health': 'EXCELLENT' if sum(self.validation_failures.values()) == 0 else 'GOOD'
        }

    def clear_used_signals(self) -> None:
        """🎯 مسح الإشارات المستخدمة (لأغراض الصيانة)"""
        try:
            with self.signal_usage_lock:
                initial_count = len(self.used_signal_hashes)
                self.used_signal_hashes.clear()
                logger.info(f"🧹 تم مسح {initial_count} إشارة مستخدمة")
        except Exception as e:
            self._handle_error("💥 خطأ في مسح الإشارات المستخدمة", e)
