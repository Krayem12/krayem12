# core/group_manager.py
import logging
from datetime import datetime, timedelta
import hashlib
from typing import Dict, List, Optional, Tuple
import threading
from collections import defaultdict, deque
from functools import lru_cache

logger = logging.getLogger(__name__)

class GroupManager:
    """🎯 نظام إدارة المجموعات مع تحسينات الأداء والأمان"""

    def __init__(self, config, trade_manager):
        self.config = config
        self.trade_manager = trade_manager
        
        # 🔄 تخزين الإشارات المؤقتة مع حدود أمان
        self.pending_signals = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        
        # 📊 إحصائيات النظام مع حدود أمان
        self.error_log = deque(maxlen=1000)
        self.mode_performance = {}
        
        # 🛡️ قفل لإدارة التزامن
        self.signal_lock = threading.RLock()
        
        logger.info("🎯 نظام المجموعات المحسن جاهز")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """🎯 معالجة موحدة للأخطاء مع حدود أمان"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self.error_log.append(full_error)
        
        # منع نمو سجل الأخطاء بشكل غير محدود
        if len(self.error_log) > 1000:
            self.error_log.popleft()

    def route_signal(self, symbol: str, signal_data: Dict, classification: str) -> List[Dict]:
        """🎯 توجيه الإشارة للمجموعة المناسبة مع معالجة محسنة للأخطاء"""
        
        if not self._validate_input(symbol, signal_data, classification):
            return []

        try:
            # 🧹 تنظيف الإشارات المنتهية أولاً
            self.cleanup_expired_signals(symbol)

            # 🎯 تحديد المجموعة والاتجاه - محدث لدعم جميع التصنيفات
            group_type, direction = self._determine_group_and_direction_enhanced(classification, signal_data)
            if not group_type:
                logger.error(f"❌ لا يمكن تحديد المجموعة للتصنيف: {classification}")
                return []

            # 🚫 منع الإشارات المكررة
            if self._is_duplicate_signal(symbol, signal_data, group_type):
                return []

            # 🔒 استخدام القفل لمنع التزامن
            with self.signal_lock:
                # ➕ إضافة الإشارة للمجموعة
                self._add_signal_to_group(symbol, signal_data, group_type, direction, classification)

                # 🔍 التحقق من محاذاة الاتجاه - محدث لدعم ALLOW_COUNTER_TREND
                if not self._check_trend_alignment(symbol, direction):
                    self._handle_contrarian_signal(symbol, group_type, signal_data)
                    return []

                # 📊 تقييم شروط الدخول
                return self._evaluate_entry_conditions(symbol, direction)

        except Exception as e:
            self._handle_error(f"💥 خطأ في توجيه الإشارة: {symbol}", e)
            return []

    def _check_trend_alignment(self, symbol: str, direction: str) -> bool:
        """🔒 التحقق من محاذاة الإشارة مع الاتجاه الحالي - محدث لدعم ALLOW_COUNTER_TREND"""
        current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
        
        # 🎯 FIX: تطبيق ALLOW_COUNTER_TREND على جميع المجموعات
        if self.config['GROUP1_TREND_MODE'] == 'ALLOW_COUNTER_TREND':
            logger.debug(f"🔓 فتح الصفقة بدون قيود اتجاه: {symbol} -> {direction.upper()} (الاتجاه: {current_trend.upper()})")
            return True  # ⬅️ فتح جميع الصفقات بغض النظر عن الاتجاه
        
        if current_trend == 'UNKNOWN':
            logger.debug(f"⏸️ تجاهل الإشارة - اتجاه غير معروف: {symbol}")
            return False
        
        is_aligned = (
            (current_trend == 'bullish' and direction == 'buy') or
            (current_trend == 'bearish' and direction == 'sell')
        )
        
        if not is_aligned:
            logger.debug(f"🚫 الإشارة مخالفة للاتجاه: {direction.upper()} vs {current_trend.upper()}")
        
        return is_aligned

    def _determine_group_and_direction_enhanced(self, classification: str, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """🎯 تحديد المحسّن للمجموعة والاتجاه - يدعم جميع التصنيفات"""
        
        # 🆕 NEW: خريطة شاملة لجميع التصنيفات الممكنة
        classification_map = {
            # المجموعة 1
            'entry_bullish': ('group1_bullish', 'buy'),
            'entry_bearish': ('group1_bearish', 'sell'),
            
            # المجموعة 2  
            'entry_bullish1': ('group2_bullish', 'buy'),
            'entry_bearish1': ('group2_bearish', 'sell'),
            
            # المجموعة 3
            'group3': self._get_group3_direction(signal_data),
            'group3_bullish': ('group3_bullish', 'buy'),
            'group3_bearish': ('group3_bearish', 'sell'),
            
            # المجموعة 4
            'group4': self._get_group4_direction(signal_data),
            'group4_bullish': ('group4_bullish', 'buy'),
            'group4_bearish': ('group4_bearish', 'sell'),
            
            # المجموعة 5
            'group5': self._get_group5_direction(signal_data),
            'group5_bullish': ('group5_bullish', 'buy'),
            'group5_bearish': ('group5_bearish', 'sell')
        }
        
        result = classification_map.get(classification)
        
        if result:
            logger.debug(f"🎯 تم تحديد المجموعة: {classification} -> {result}")
            return result
        else:
            logger.error(f"❌ تصنيف غير معروف في group_manager: {classification}")
            return None, None

    def _get_group3_direction(self, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """تحديد اتجاه المجموعة 3"""
        signal_type = signal_data.get('signal_type', '').lower()
        
        group3_bullish = [s.lower().strip() for s in self.config['signals'].get('group3_bullish', [])]
        group3_bearish = [s.lower().strip() for s in self.config['signals'].get('group3_bearish', [])]
        
        if signal_type in group3_bullish:
            return 'group3_bullish', 'buy'
        elif signal_type in group3_bearish:
            return 'group3_bearish', 'sell'
        
        return None, None

    def _get_group4_direction(self, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """تحديد اتجاه المجموعة 4"""
        signal_type = signal_data.get('signal_type', '').lower()
        
        group4_bullish = [s.lower().strip() for s in self.config['signals'].get('group4_bullish', [])]
        group4_bearish = [s.lower().strip() for s in self.config['signals'].get('group4_bearish', [])]
        
        if signal_type in group4_bullish:
            return 'group4_bullish', 'buy'
        elif signal_type in group4_bearish:
            return 'group4_bearish', 'sell'
        
        return None, None

    def _get_group5_direction(self, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """تحديد اتجاه المجموعة 5"""
        signal_type = signal_data.get('signal_type', '').lower()
        
        group5_bullish = [s.lower().strip() for s in self.config['signals'].get('group5_bullish', [])]
        group5_bearish = [s.lower().strip() for s in self.config['signals'].get('group5_bearish', [])]
        
        if signal_type in group5_bullish:
            return 'group5_bullish', 'buy'
        elif signal_type in group5_bearish:
            return 'group5_bearish', 'sell'
        
        return None, None

    def _validate_input(self, symbol: str, signal_data: Dict, classification: str) -> bool:
        """التحقق من صحة بيانات الإدخال"""
        if not symbol or symbol == 'UNKNOWN':
            logger.error("❌ رمز غير صالح")
            return False
        
        if not signal_data or 'signal_type' not in signal_data:
            logger.error("❌ بيانات الإشارة غير صالحة")
            return False
        
        # 🆕 NEW: توسيع قائمة التصنيفات المقبولة
        valid_classifications = {
            'entry_bullish', 'entry_bearish', 'entry_bullish1', 'entry_bearish1', 
            'group3', 'group4', 'group5', 'group3_bullish', 'group3_bearish',
            'group4_bullish', 'group4_bearish', 'group5_bullish', 'group5_bearish'
        }
        
        if classification not in valid_classifications:
            logger.error(f"❌ تصنيف غير معروف: {classification}")
            return False
        
        return True

    def _add_signal_to_group(self, symbol: str, signal_data: Dict, group_type: str, 
                           direction: str, classification: str) -> None:
        """إضافة الإشارة للمجموعة مع التحكم بالسعة"""
        group_key = symbol.upper().strip()
        
        # إنشاء المجموعة إذا لم تكن موجودة
        if group_key not in self.pending_signals:
            # 🆕 NEW: جميع أنواع المجموعات الممكنة
            all_group_types = [
                'group1_bullish', 'group1_bearish', 'group2_bullish', 'group2_bearish',
                'group3_bullish', 'group3_bearish', 'group4_bullish', 'group4_bearish',
                'group5_bullish', 'group5_bearish'
            ]
            for gt in all_group_types:
                self.pending_signals[group_key][gt] = deque(maxlen=100)
            
            self.pending_signals[group_key]["created_at"] = datetime.now()
        
        # إنشاء معلومات الإشارة
        signal_info = {
            'hash': hashlib.md5(
                f"{signal_data['signal_type']}_{classification}_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}".encode()
            ).hexdigest(),
            'signal_type': signal_data['signal_type'],
            'classification': classification,
            'timestamp': datetime.now(),
            'direction': direction,
            'symbol': symbol
        }
        
        # إضافة الإشارة (سيتحكم deque تلقائياً بالحد الأقصى)
        self.pending_signals[group_key][group_type].append(signal_info)
        self.pending_signals[group_key]["updated_at"] = datetime.now()
        
        logger.debug(f"📥 إشارة مضافة: {signal_data['signal_type']} → {group_type}")

    def _is_duplicate_signal(self, symbol: str, signal_data: Dict, group_type: str) -> bool:
        """🚫 منع الإشارات المكررة"""
        group_key = symbol.upper().strip()
        
        # إنشاء hash فريد للإشارة
        signal_text = f"{signal_data['signal_type']}_{group_type}_{symbol}_{datetime.now().strftime('%Y%m%d%H')}"
        signal_hash = hashlib.md5(signal_text.encode()).hexdigest()
        
        # التحقق من التكرار في جميع المجموعات
        for gt in ['group1_bullish', 'group1_bearish', 'group2_bullish', 
                  'group2_bearish', 'group3_bullish', 'group3_bearish',
                  'group4_bullish', 'group4_bearish', 'group5_bullish', 'group5_bearish']:
            if group_key in self.pending_signals:
                for signal in self.pending_signals[group_key][gt]:
                    if signal.get('hash') == signal_hash:
                        logger.debug(f"🔁 إشارة مكررة - تم تجاهلها: {signal_data['signal_type']}")
                        return True
        
        return False

    def _handle_contrarian_signal(self, symbol: str, group_type: str, signal_data: Dict) -> None:
        """معالجة الإشارة المخالفة للاتجاه"""
        store_contrarian = self.config.get('STORE_CONTRARIAN_SIGNALS', False)
        if store_contrarian:
            logger.debug(f"📦 الإشارة مخالفة للاتجاه - تم تخزينها: {symbol} → {signal_data['signal_type']}")
        else:
            logger.debug(f"🚫 الإشارة مخالفة للاتجاه - تم تجاهلها: {symbol} → {signal_data['signal_type']}")

    def _evaluate_entry_conditions(self, symbol: str, direction: str) -> List[Dict]:
        """📊 تقييم شروط الدخول للصفقات"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                return []
            
            # 📈 حساب عدد الإشارات لكل مجموعة
            signal_counts = self._count_signals_by_direction(group_key, direction)
            
            logger.debug(f"📊 إحصائيات {symbol} [{direction.upper()}]: G1={signal_counts['g1']}, G2={signal_counts['g2']}, G3={signal_counts['g3']}, G4={signal_counts['g4']}, G5={signal_counts['g5']}")
            
            # 🎯 تقييم الأنماط المفعلة فقط
            active_modes = self._get_active_modes()
            trade_results = []
            
            for mode_key in active_modes:
                trade_result = self._evaluate_single_mode(mode_key, symbol, direction, signal_counts)
                if trade_result:
                    trade_results.append(trade_result)
            
            # 🧹 إعادة تعيين الإشارات المستخدمة
            if trade_results:
                self._reset_used_signals(symbol, direction, trade_results)
                logger.debug(f"✅ تم فتح {len(trade_results)} صفقة لـ {symbol}")
            
            return trade_results
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في تقييم شروط الدخول: {symbol}", e)
            return []

    def _count_signals_by_direction(self, group_key: str, direction: str) -> Dict[str, int]:
        """📈 حساب عدد الإشارات حسب الاتجاه"""
        groups = self.pending_signals[group_key]
        
        if direction == "buy":
            return {
                'g1': len(groups["group1_bullish"]),
                'g2': len(groups["group2_bullish"]),
                'g3': len(groups["group3_bullish"]),
                'g4': len(groups["group4_bullish"]),
                'g5': len(groups["group5_bullish"])
            }
        else:
            return {
                'g1': len(groups["group1_bearish"]),
                'g2': len(groups["group2_bearish"]),
                'g3': len(groups["group3_bearish"]),
                'g4': len(groups["group4_bearish"]),
                'g5': len(groups["group5_bearish"])
            }

    def _get_active_modes(self) -> List[str]:
        """🎯 الحصول على الأنماط المفعلة فقط"""
        active_modes = ['TRADING_MODE']
        
        if self.config.get('TRADING_MODE1_ENABLED', False):
            active_modes.append('TRADING_MODE1')
        if self.config.get('TRADING_MODE2_ENABLED', False):
            active_modes.append('TRADING_MODE2')
        
        return active_modes

    def _evaluate_single_mode(self, mode_key: str, symbol: str, direction: str, signal_counts: Dict) -> Optional[Dict]:
        """🎯 تقييم نمط تداول فردي"""
        try:
            if not self._can_open_trade(symbol, mode_key):
                return None
            
            trading_mode = self.config.get(mode_key)
            if not trading_mode:
                return None

            # ✅ التحقق من شروط الدخول حسب الاستراتيجية
            conditions_met, required_groups = self._check_strategy_conditions(trading_mode, signal_counts)
            
            if conditions_met:
                if self._open_trade(symbol, direction, trading_mode, mode_key):
                    trade_info = self._collect_trade_signals(symbol, direction, required_groups)
                    trade_info.update({
                        'symbol': symbol,
                        'direction': direction,
                        'strategy_type': trading_mode,
                        'mode_key': mode_key,
                        'trade_timestamp': datetime.now().isoformat()
                    })
                    return trade_info
            
            return None
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في تقييم النمط {mode_key}", e)
            return None

    def _can_open_trade(self, symbol: str, mode_key: str) -> bool:
        """📊 التحقق من إمكانية فتح صفقة جديدة"""
        try:
            # التحقق من الحدود العامة
            current_count = self.trade_manager.get_active_trades_count(symbol)
            if current_count >= self.config['MAX_TRADES_PER_SYMBOL']:
                return False
            
            # التحقق من الحدود الإجمالية
            total_trades = self.trade_manager.get_active_trades_count()
            if total_trades >= self.config['MAX_OPEN_TRADES']:
                return False
            
            # 🛠️ التحقق من حدود النمط
            mode_limits = {
                'TRADING_MODE': self.config.get('MAX_TRADES_MODE_MAIN', 5),
                'TRADING_MODE1': self.config.get('MAX_TRADES_MODE1', 3),
                'TRADING_MODE2': self.config.get('MAX_TRADES_MODE2', 3)
            }
            
            current_mode_trades = self._count_trades_by_mode(symbol, mode_key)
            mode_limit = mode_limits.get(mode_key, 2)
            
            if current_mode_trades >= mode_limit:
                return False
            
            return True
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في التحقق من إمكانية فتح الصفقة", e)
            return False

    def _check_strategy_conditions(self, trading_mode: str, signal_counts: Dict) -> Tuple[bool, List[str]]:
        """✅ التحقق من شروط الاستراتيجية"""
        required_groups = trading_mode.split('_') if trading_mode else []
        conditions_met = True
        
        for group in required_groups:
            group_key = group.lower()
            
            # التحقق من أن المجموعة مفعلة
            group_enabled_key = f"{group}_ENABLED"
            if not self.config.get(group_enabled_key, False):
                conditions_met = False
                break
            
            # التحقق من عدد التأكيدات المطلوبة
            confirmations_key = f"REQUIRED_CONFIRMATIONS_{group}"
            required_confirmations = self.config.get(confirmations_key, 1)
            
            # الحصول على عدد الإشارات الحالي للمجموعة
            signal_count_key = f"g{group_key[-1]}"
            current_signals = signal_counts.get(signal_count_key, 0)
            
            if current_signals < required_confirmations:
                conditions_met = False
                break
        
        return conditions_met, required_groups

    def _collect_trade_signals(self, symbol: str, direction: str, required_groups: List[str]) -> Dict:
        """📋 جمع الإشارات المستخدمة في الصفقة"""
        group_key = symbol.upper().strip()
        groups = self.pending_signals[group_key]
        
        trade_info = {}
        
        for group in required_groups:
            group_type = f"{group.lower()}_bullish" if direction == 'buy' else f"{group.lower()}_bearish"
            
            if group_type in groups:
                trade_info[f'{group.lower()}_signals'] = [signal['signal_type'] for signal in groups[group_type]]
            else:
                trade_info[f'{group.lower()}_signals'] = []
        
        return trade_info

    def _open_trade(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> bool:
        """💼 فتح صفقة جديدة"""
        try:
            success = self.trade_manager.open_trade(symbol, direction, strategy_type, mode_key)
            
            if success:
                if mode_key not in self.mode_performance:
                    self.mode_performance[mode_key] = {'opened': 0, 'failed': 0}
                self.mode_performance[mode_key]['opened'] += 1
            else:
                if mode_key not in self.mode_performance:
                    self.mode_performance[mode_key] = {'opened': 0, 'failed': 0}
                self.mode_performance[mode_key]['failed'] += 1
                
            return success
            
        except Exception as e:
            self._handle_error(f"💥 خطأ غير متوقع في فتح الصفقة", e)
            return False

    def _count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """📊 حساب الصفقات حسب النمط"""
        count = 0
        for trade_id, trade in self.trade_manager.active_trades.items():
            if trade.get('symbol') == symbol and trade.get('mode_key') == mode_key:
                count += 1
        return count

    def _reset_used_signals(self, symbol: str, direction: str, trade_results: List[Dict]) -> None:
        """🧹 إعادة تعيين الإشارات المستخدمة"""
        try:
            group_key = symbol.upper().strip()
            
            if not trade_results:
                return
            
            # 🎯 جمع جميع الإشارات المستخدمة
            used_signals = set()
            for trade in trade_results:
                for group in ['group1_signals', 'group2_signals', 'group3_signals', 'group4_signals', 'group5_signals']:
                    signals = trade.get(group, [])
                    used_signals.update(signals)
            
            if not used_signals:
                return
            
            # 🗑️ حذف الإشارات المستخدمة
            for group_type in ['group1_bullish', 'group1_bearish', 'group2_bullish', 
                              'group2_bearish', 'group3_bullish', 'group3_bearish',
                              'group4_bullish', 'group4_bearish', 'group5_bullish', 'group5_bearish']:
                self.pending_signals[group_key][group_type] = deque(
                    [signal for signal in self.pending_signals[group_key][group_type]
                     if signal['signal_type'] not in used_signals],
                    maxlen=100
                )
            
        except Exception as e:
            self._handle_error(f"⚠️ خطأ في إعادة تعيين الإشارات", e)

    def cleanup_expired_signals(self, symbol: str) -> None:
        """🧹 تنظيف الإشارات المنتهية الصلاحية"""
        try:
            group_key = symbol.upper().strip()
            if group_key not in self.pending_signals:
                return

            ttl_minutes = self.config.get('SIGNAL_TTL_MINUTES', 180)
            expiration_time = datetime.now() - timedelta(minutes=ttl_minutes)

            for group_type in self.pending_signals[group_key]:
                if group_type in ['created_at', 'updated_at']:
                    continue
                    
                self.pending_signals[group_key][group_type] = deque(
                    [signal for signal in self.pending_signals[group_key][group_type]
                     if signal.get('timestamp', datetime.now()) > expiration_time],
                    maxlen=100
                )

        except Exception as e:
            self._handle_error(f"⚠️ خطأ في تنظيف الإشارات المنتهية الصلاحية", e)

    def get_group_stats(self, symbol: str) -> Optional[Dict]:
        """📈 الحصول على إحصائيات المجموعات"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                return None
                
            groups = self.pending_signals[group_key]
            
            return {
                'symbol': symbol,
                'group1_bullish': len(groups['group1_bullish']),
                'group1_bearish': len(groups['group1_bearish']),
                'group2_bullish': len(groups['group2_bullish']),
                'group2_bearish': len(groups['group2_bearish']),
                'group3_bullish': len(groups['group3_bullish']),
                'group3_bearish': len(groups['group3_bearish']),
                'group4_bullish': len(groups['group4_bullish']),
                'group4_bearish': len(groups['group4_bearish']),
                'group5_bullish': len(groups['group5_bullish']),
                'group5_bearish': len(groups['group5_bearish']),
                'total_signals': sum(len(groups[gt]) for gt in groups if gt not in ['created_at', 'updated_at']),
                'updated_at': groups['updated_at']
            }
        except Exception as e:
            self._handle_error(f"⚠️ خطأ في إحصائيات المجموعات", e)
            return None

    def get_performance_metrics(self) -> Dict:
        """الحصول على مقاييس الأداء"""
        return {
            'error_count': len(self.error_log),
            'mode_performance': self.mode_performance.copy(),
            'total_signals': sum(
                len(signals) 
                for symbol_data in self.pending_signals.values() 
                for signals in symbol_data.values() 
                if isinstance(signals, deque)
            )
        }