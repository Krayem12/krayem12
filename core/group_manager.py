# core/group_manager.py
import logging
from datetime import datetime, timedelta
import hashlib
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class GroupManager:
    """🎯 نظام إدارة المجموعات المُبسط والمُحسّن - تقارير تفصيلية عن التنظيف"""

    def __init__(self, config, trade_manager):
        self.config = config
        self.trade_manager = trade_manager
        
        # 🔄 تخزين الإشارات المؤقتة
        self.pending_signals = {}
        
        # ⏰ التحكم بعمر الإشارات من .env
        self.signal_max_age = timedelta(minutes=config.get('SIGNAL_CLEANUP_INTERVAL_MINUTES', 30))
        
        # 📊 إحصائيات النظام
        self.error_log = []
        self.mode_performance = {}
        
        logger.info("🎯 نظام المجموعات المُحسّن جاهز - تقارير تفصيلية عن التنظيف")

    def clean_contrarian_signals_detailed(self, symbol: str, direction_to_remove: str) -> Dict:
        """🧹 مسح الإشارات المخالفة للاتجاه الحالي مع تفاصيل كاملة"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                return {'removed_count': 0, 'removed_signals': []}
            
            # تحديد المجموعات التي يجب مسحها
            groups_to_clear = []
            if direction_to_remove == 'bullish':
                groups_to_clear = ['group1_bullish', 'group2_bullish', 'group3_bullish']
            else:
                groups_to_clear = ['group1_bearish', 'group2_bearish', 'group3_bearish']
            
            # جمع المعلومات التفصيلية عن الإشارات التي سيتم مسحها
            removed_signals = []
            total_removed = 0
            
            for group_name in groups_to_clear:
                group_signals = self.pending_signals[group_key][group_name]
                
                for signal in group_signals:
                    # 🆕 جمع تفاصيل كاملة عن كل إشارة
                    signal_details = {
                        'signal_type': signal['signal_type'],
                        'group': self._get_group_display_name(group_name),
                        'original_group': group_name,
                        'classification': signal.get('classification', 'unknown'),
                        'direction': signal.get('direction', 'unknown'),
                        'timestamp': signal.get('timestamp', datetime.now()),
                        'age_minutes': self._calculate_signal_age(signal.get('timestamp'))
                    }
                    removed_signals.append(signal_details)
                    total_removed += 1
                
                # مسح الإشارات من المجموعة
                self.pending_signals[group_key][group_name] = []
            
            # تحديث وقت التحديث
            self.pending_signals[group_key]["updated_at"] = datetime.now()
            
            logger.debug(f"🧹 تم مسح {total_removed} إشارة {direction_to_remove} مخالفة لـ {symbol}")
            
            # 🆕 إرجاع تقرير تفصيلي
            return {
                'removed_count': total_removed,
                'removed_signals': removed_signals,
                'direction_removed': direction_to_remove,
                'symbol': symbol,
                'cleaning_time': datetime.now()
            }
            
        except Exception as e:
            error_msg = f"⚠️ خطأ في مسح الإشارات المخالفة: {e}"
            logger.error(error_msg)
            return {'removed_count': 0, 'removed_signals': []}

    def _get_group_display_name(self, group_name: str) -> str:
        """🆕 تحويل اسم المجموعة الداخلي إلى اسم مفهوم"""
        group_mapping = {
            'group1_bullish': '🟥 المجموعة 1 - صاعد',
            'group1_bearish': '🟥 المجموعة 1 - هابط',
            'group2_bullish': '🟦 المجموعة 2 - صاعد', 
            'group2_bearish': '🟦 المجموعة 2 - هابط',
            'group3_bullish': '🟩 المجموعة 3 - صاعد',
            'group3_bearish': '🟩 المجموعة 3 - هابط'
        }
        return group_mapping.get(group_name, group_name)

    def _calculate_signal_age(self, signal_timestamp) -> float:
        """🆕 حساب عمر الإشارة بالدقائق"""
        if not signal_timestamp:
            return 0.0
        
        if isinstance(signal_timestamp, str):
            try:
                signal_timestamp = datetime.fromisoformat(signal_timestamp.replace('Z', '+00:00'))
            except:
                return 0.0
        
        age_seconds = (datetime.now() - signal_timestamp).total_seconds()
        return round(age_seconds / 60, 1)

    def get_signal_statistics(self, symbol: str) -> Dict:
        """🆕 الحصول على إحصائيات تفصيلية عن الإشارات"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                return {'total_signals': 0, 'groups': {}}
            
            groups = self.pending_signals[group_key]
            stats = {
                'total_signals': 0,
                'groups': {},
                'by_direction': {'bullish': 0, 'bearish': 0}
            }
            
            for group_name in ['group1_bullish', 'group1_bearish', 'group2_bullish', 
                              'group2_bearish', 'group3_bullish', 'group3_bearish']:
                signal_count = len(groups[group_name])
                stats['total_signals'] += signal_count
                stats['groups'][group_name] = {
                    'count': signal_count,
                    'display_name': self._get_group_display_name(group_name),
                    'signals': [s['signal_type'] for s in groups[group_name]]
                }
                
                # إحصاء حسب الاتجاه
                if 'bullish' in group_name:
                    stats['by_direction']['bullish'] += signal_count
                else:
                    stats['by_direction']['bearish'] += signal_count
            
            return stats
            
        except Exception as e:
            logger.error(f"⚠️ خطأ في إحصائيات الإشارات: {e}")
            return {'total_signals': 0, 'groups': {}}

    def route_signal(self, symbol: str, signal_data: Dict, classification: str) -> List[Dict]:
        """🎯 توجيه الإشارة للمجموعة المناسبة مع التحقق الشامل"""
        try:
            # ✅ التحقق الأولي من صحة البيانات
            if not self._validate_input(symbol, signal_data, classification):
                return []

            # 🧹 تنظيف الإشارات القديمة أولاً
            self._clean_old_signals(symbol)

            # 🎯 تحديد المجموعة والاتجاه
            group_type, direction = self._determine_group_and_direction(classification, signal_data)
            if not group_type:
                return []

            # 🔒 التحقق من محاذاة الاتجاه
            if not self._check_trend_alignment(symbol, direction):
                return []

            # 🚫 منع الإشارات المكررة
            if self._is_duplicate_signal(symbol, signal_data, group_type):
                return []

            # ➕ إضافة الإشارة للمجموعة
            self._add_signal_to_group(symbol, signal_data, group_type, direction, classification)

            # 📊 تقييم شروط الدخول
            return self._evaluate_entry_conditions(symbol, direction)

        except Exception as e:
            error_msg = f"💥 خطأ في توجيه الإشارة: {symbol} | {str(e)}"
            logger.error(error_msg)
            self.error_log.append(error_msg)
            return []

    def _validate_input(self, symbol: str, signal_data: Dict, classification: str) -> bool:
        """✅ التحقق من صحة بيانات الإدخال"""
        if not symbol or symbol == 'UNKNOWN':
            logger.error("❌ رمز غير صالح")
            return False
        
        if not signal_data or 'signal_type' not in signal_data:
            logger.error("❌ بيانات الإشارة غير صالحة")
            return False
        
        valid_classifications = ['entry_bullish', 'entry_bearish', 'entry_bullish1', 'entry_bearish1', 'group3']
        if classification not in valid_classifications:
            logger.error(f"❌ تصنيف غير معروف: {classification}")
            return False
        
        return True

    def _clean_old_signals(self, symbol: str):
        """🧹 تنظيف الإشارات القديمة بناءً على إعدادات .env"""
        group_key = symbol.upper().strip()
        
        if group_key not in self.pending_signals:
            return
        
        now = datetime.now()
        cleaned_count = 0
        
        for direction in ['bullish', 'bearish']:
            for group_num in ['1', '2', '3']:
                group_name = f"group{group_num}_{direction}"
                original_count = len(self.pending_signals[group_key][group_name])
                
                # 🎯 استخدام الإعداد من .env للتحكم بعمر الإشارات
                self.pending_signals[group_key][group_name] = [
                    signal for signal in self.pending_signals[group_key][group_name]
                    if (now - signal['timestamp']).total_seconds() < self.signal_max_age.total_seconds()
                ]
                
                cleaned_count += (original_count - len(self.pending_signals[group_key][group_name]))
        
        if cleaned_count > 0:
            logger.debug(f"🧹 تم تنظيف {cleaned_count} إشارة قديمة لـ {symbol} (العمر: {self.signal_max_age.total_seconds()/60} دقيقة)")

    def _determine_group_and_direction(self, classification: str, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """🎯 تحديد المجموعة والاتجاه بدقة مع GROUP3 المنفصل - تحسين الرسائل"""
        
        # 🗺️ خريطة التصنيفات للمجموعات
        classification_map = {
            'entry_bullish': ('group1_bullish', 'buy'),
            'entry_bearish': ('group1_bearish', 'sell'),
            'entry_bullish1': ('group2_bullish', 'buy'),
            'entry_bearish1': ('group2_bearish', 'sell'),
            'group3': self._determine_group3_direction_strict(signal_data)
        }
        
        result = classification_map.get(classification)
        
        if not result:
            logger.error(f"❌ تعيين غير معروف للتصنيف: {classification}")
            return None, None
        
        # 📝 معالجة خاصة لـ GROUP3
        if classification == 'group3':
            group_type, direction = result
            if not group_type:
                # 🛠️ تحسين الرسالة: لا داعي لطباعة القوائم الكاملة للإشارات غير GROUP3
                signal_type = signal_data['signal_type']
                # فقط طباعة رسالة مبسطة للإشارات غير GROUP3
                if not any(keyword in signal_type.lower() for keyword in ['moneyflow', 'catcher', 'hyperwave']):
                    logger.error(f"❌ إشارة GROUP3 غير معروفة: {signal_type}")
                return None, None
        else:
            group_type, direction = result
        
        logger.debug(f"🎯 التصنيف: {classification} → المجموعة: {group_type} | الاتجاه: {direction}")
        return group_type, direction

    def _determine_group3_direction_strict(self, signal_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """🎯 تحديد اتجاه GROUP3 بالتطابق التام 100% مع القوائم المنفصلة"""
        signal_type = signal_data['signal_type'].lower().strip()
        
        # 🛠️ الإصلاح: معالجة خاصة لإشارات GROUP3 مع البوادئ
        group3_signal_clean = signal_type
        if signal_type.startswith('bullish_'):
            group3_signal_clean = signal_type.replace('bullish_', '')
        elif signal_type.startswith('bearish_'):
            group3_signal_clean = signal_type.replace('bearish_', '')
        
        # 📋 الحصول على إشارات GROUP3 الصاعدة والهابطة المعرفة في .env
        group3_bullish_signals = [s.lower().strip() for s in self.config.get('ENTRY_SIGNALS_GROUP3_BULLISH', [])]
        group3_bearish_signals = [s.lower().strip() for s in self.config.get('ENTRY_SIGNALS_GROUP3_BEARISH', [])]
        
        # ✅ التطابق التام 100% فقط مع القوائم المنفصلة
        if group3_signal_clean in group3_bullish_signals:
            logger.debug(f"✅ تم التعرف على إشارة GROUP3 صاعدة (تطابق تام): {signal_data['signal_type']}")
            return 'group3_bullish', 'buy'
        elif group3_signal_clean in group3_bearish_signals:
            logger.debug(f"✅ تم التعرف على إشارة GROUP3 هابطة (تطابق تام): {signal_data['signal_type']}")
            return 'group3_bearish', 'sell'
        else:
            return None, None

    def _check_trend_alignment(self, symbol: str, direction: str) -> bool:
        """🔒 التحقق من محاذاة الإشارة مع الاتجاه الحالي"""
        current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
        
        if current_trend == 'UNKNOWN':
            logger.debug(f"⏸️  تجاهل الإشارة - اتجاه غير معروف: {symbol}")
            return False
        
        is_aligned = (
            (current_trend == 'bullish' and direction == 'buy') or
            (current_trend == 'bearish' and direction == 'sell')
        )
        
        if not is_aligned:
            logger.debug(f"🚫 الإشارة مخالفة للاتجاه: {direction.upper()} vs {current_trend.upper()}")
        
        return is_aligned

    def _is_duplicate_signal(self, symbol: str, signal_data: Dict, group_type: str) -> bool:
        """🚫 منع الإشارات المكررة باستخدام hash فريد"""
        group_key = symbol.upper().strip()
        
        # إنشاء hash فريد للإشارة
        signal_text = f"{signal_data['signal_type']}_{group_type}_{symbol}_{datetime.now().strftime('%Y%m%d%H')}"
        signal_hash = hashlib.md5(signal_text.encode()).hexdigest()
        
        # التحقق من التكرار في جميع المجموعات
        for gt in ['group1_bullish', 'group1_bearish', 'group2_bullish', 
                  'group2_bearish', 'group3_bullish', 'group3_bearish']:
            if group_key in self.pending_signals:
                for signal in self.pending_signals[group_key][gt]:
                    if signal.get('hash') == signal_hash:
                        logger.debug(f"🔁 إشارة مكررة - تم تجاهلها: {signal_data['signal_type']}")
                        return True
        
        return False

    def _add_signal_to_group(self, symbol: str, signal_data: Dict, group_type: str, direction: str, classification: str):
        """➕ إضافة الإشارة للمجموعة مع التحكم بالسعة"""
        group_key = symbol.upper().strip()
        
        # إنشاء المجموعة إذا لم تكن موجودة
        if group_key not in self.pending_signals:
            self.pending_signals[group_key] = {
                "group1_bullish": [], "group1_bearish": [],
                "group2_bullish": [], "group2_bearish": [], 
                "group3_bullish": [], "group3_bearish": [],
                "created_at": datetime.now(), "updated_at": datetime.now()
            }
        
        # 🎯 إنشاء معلومات الإشارة
        signal_info = {
            'hash': hashlib.md5(f"{signal_data['signal_type']}_{classification}_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}".encode()).hexdigest(),
            'signal_type': signal_data['signal_type'],
            'classification': classification,
            'timestamp': datetime.now(),
            'direction': direction,
            'symbol': symbol
        }
        
        # 📦 التحكم بالسعة القصوى (50 إشارة كحد أقصى)
        max_signals = 50
        if len(self.pending_signals[group_key][group_type]) >= max_signals:
            removed_signal = self.pending_signals[group_key][group_type].pop(0)
            logger.debug(f"🗑️  تم إزالة إشارة قديمة: {removed_signal['signal_type']}")
        
        # إضافة الإشارة الجديدة
        self.pending_signals[group_key][group_type].append(signal_info)
        self.pending_signals[group_key]["updated_at"] = datetime.now()
        
        logger.debug(f"📥 إشارة مضافة: {signal_data['signal_type']} → {group_type}")

    def _evaluate_entry_conditions(self, symbol: str, direction: str) -> List[Dict]:
        """📊 تقييم شروط الدخول للصفقات"""
        try:
            group_key = symbol.upper().strip()
            
            if group_key not in self.pending_signals:
                return []
            
            # 📈 حساب عدد الإشارات لكل مجموعة
            signal_counts = self._count_signals_by_direction(group_key, direction)
            
            logger.debug(f"📊 إحصائيات {symbol} [{direction.upper()}]: G1={signal_counts['g1']}, G2={signal_counts['g2']}, G3={signal_counts['g3']}")
            
            # ✅ الشرط الأساسي الإلزامي: يجب توفر الحد الأدنى من GROUP1
            if signal_counts['g1'] < self.config["REQUIRED_CONFIRMATIONS_GROUP1"]:
                logger.debug(f"❌ شروط المجموعة الأولى غير محققة: {signal_counts['g1']}/{self.config['REQUIRED_CONFIRMATIONS_GROUP1']}")
                return []  # 🚨 إرجاع فوري - لا مزيد من المعالجة
            
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
            else:
                logger.debug(f"⏹️  لم يتم فتح أي صفقة لـ {symbol}")
            
            return trade_results
            
        except Exception as e:
            error_msg = f"💥 خطأ في تقييم شروط الدخول: {symbol} | {str(e)}"
            logger.error(error_msg)
            return []

    def _count_signals_by_direction(self, group_key: str, direction: str) -> Dict[str, int]:
        """📈 حساب عدد الإشارات حسب الاتجاه"""
        groups = self.pending_signals[group_key]
        
        if direction == "buy":
            return {
                'g1': len(groups["group1_bullish"]),
                'g2': len(groups["group2_bullish"]),
                'g3': len(groups["group3_bullish"])
            }
        else:
            return {
                'g1': len(groups["group1_bearish"]),
                'g2': len(groups["group2_bearish"]),
                'g3': len(groups["group3_bearish"])
            }

    def _get_active_modes(self) -> List[str]:
        """🎯 الحصول على الأنماط المفعلة فقط"""
        active_modes = ['TRADING_MODE']  # النمط الأساسي دائماً مفعل
        
        if self.config.get('TRADING_MODE1_ENABLED', False):
            active_modes.append('TRADING_MODE1')
        if self.config.get('TRADING_MODE2_ENABLED', False):
            active_modes.append('TRADING_MODE2')
        
        logger.debug(f"🎯 الأنماط المفعلة: {active_modes}")
        return active_modes

    def _evaluate_single_mode(self, mode_key: str, symbol: str, direction: str, signal_counts: Dict) -> Optional[Dict]:
        """🎯 تقييم نمط تداول فردي"""
        try:
            # 📊 التحقق من حدود الصفقات أولاً
            if not self._can_open_trade(symbol, mode_key):
                return None
            
            # 🎯 الحصول على إعدادات النمط
            trading_mode = self.config[mode_key]
            logger.debug(f"🔍 فحص النمط {mode_key}: {trading_mode}")
            
            # ✅ التحقق من شروط الدخول حسب الاستراتيجية
            conditions_met, required_groups = self._check_strategy_conditions(trading_mode, signal_counts)
            
            if conditions_met:
                logger.debug(f"🎯 شروط الدخول متحققة لـ {symbol} بالنمط {mode_key}")
                
                # 💼 فتح الصفقة
                if self._open_trade(symbol, direction, trading_mode, mode_key):
                    # 📋 جمع الإشارات المستخدمة
                    trade_info = self._collect_trade_signals(symbol, direction, required_groups)
                    trade_info.update({
                        'symbol': symbol,
                        'direction': direction,
                        'strategy_type': trading_mode,
                        'mode_key': mode_key
                    })
                    return trade_info
            
            return None
            
        except Exception as e:
            error_msg = f"💥 خطأ في تقييم النمط {mode_key}: {str(e)}"
            logger.error(error_msg)
            return None

    def _can_open_trade(self, symbol: str, mode_key: str) -> bool:
        """📊 التحقق من إمكانية فتح صفقة جديدة"""
        # التحقق من الحدود العامة
        current_count = self.trade_manager.get_active_trades_count(symbol)
        if current_count >= self.config['MAX_TRADES_PER_SYMBOL']:
            logger.debug(f"⏹️  وصل الرمز {symbol} للحد الأقصى: {current_count}")
            return False
        
        # التحقق من الحدود الإجمالية
        total_trades = self.trade_manager.get_active_trades_count()
        if total_trades >= self.config['MAX_OPEN_TRADES']:
            logger.debug(f"⏹️  وصل النظام للحد الأقصى الإجمالي: {total_trades}")
            return False
        
        # التحقق من حدود النمط
        mode_limits = {
            'TRADING_MODE': self.config.get('MAX_TRADES_MODE_MAIN', self.config['MAX_TRADES_PER_SYMBOL']),
            'TRADING_MODE1': self.config.get('MAX_TRADES_MODE1', self.config['MAX_TRADES_PER_SYMBOL'] // 2),
            'TRADING_MODE2': self.config.get('MAX_TRADES_MODE2', self.config['MAX_TRADES_PER_SYMBOL'] // 2)
        }
        
        current_mode_trades = self._count_trades_by_mode(symbol, mode_key)
        mode_limit = mode_limits.get(mode_key, 2)
        
        if current_mode_trades >= mode_limit:
            logger.debug(f"⏹️  النمط {mode_key} وصل الحد: {current_mode_trades}/{mode_limit}")
            return False
        
        return True

    def _check_strategy_conditions(self, trading_mode: str, signal_counts: Dict) -> Tuple[bool, List[str]]:
        """✅ التحقق من شروط الاستراتيجية"""
        required_groups = ['GROUP1']  # GROUP1 مطلوب دائماً
        
        if trading_mode == 'GROUP1':
            return True, required_groups
            
        elif trading_mode == 'GROUP1_GROUP2':
            group2_ok = self.config.get('GROUP2_ENABLED', False) and \
                       signal_counts['g2'] >= self.config["REQUIRED_CONFIRMATIONS_GROUP2"]
            required_groups.append('GROUP2')
            return group2_ok, required_groups
            
        elif trading_mode == 'GROUP1_GROUP3':
            group3_ok = self.config.get('GROUP3_ENABLED', False) and \
                       signal_counts['g3'] >= self.config["REQUIRED_CONFIRMATIONS_GROUP3"]
            required_groups.append('GROUP3')
            return group3_ok, required_groups
            
        elif trading_mode == 'GROUP1_GROUP2_GROUP3':
            group2_ok = self.config.get('GROUP2_ENABLED', False) and \
                       signal_counts['g2'] >= self.config["REQUIRED_CONFIRMATIONS_GROUP2"]
            group3_ok = self.config.get('GROUP3_ENABLED', False) and \
                       signal_counts['g3'] >= self.config["REQUIRED_CONFIRMATIONS_GROUP3"]
            required_groups.extend(['GROUP2', 'GROUP3'])
            return group2_ok and group3_ok, required_groups
            
        else:
            logger.warning(f"⚠️ استراتيجية غير معروفة: {trading_mode}")
            return False, required_groups

    def _collect_trade_signals(self, symbol: str, direction: str, required_groups: List[str]) -> Dict:
        """📋 جمع الإشارات المستخدمة في الصفقة"""
        group_key = symbol.upper().strip()
        groups = self.pending_signals[group_key]
        
        trade_info = {}
        
        if 'GROUP1' in required_groups:
            trade_info['group1_signals'] = self._get_signals_by_group(groups, direction, 'group1')
        
        if 'GROUP2' in required_groups:
            trade_info['group2_signals'] = self._get_signals_by_group(groups, direction, 'group2')
        
        if 'GROUP3' in required_groups:
            trade_info['group3_signals'] = self._get_signals_by_group(groups, direction, 'group3')
        
        return trade_info

    def _get_signals_by_group(self, groups: Dict, direction: str, group_type: str) -> List[str]:
        """📝 الحصول على أسماء الإشارات حسب المجموعة"""
        group_map = {
            'group1': 'group1_bullish' if direction == 'buy' else 'group1_bearish',
            'group2': 'group2_bullish' if direction == 'buy' else 'group2_bearish', 
            'group3': 'group3_bullish' if direction == 'buy' else 'group3_bearish'
        }
        
        group_name = group_map[group_type]
        return [signal['signal_type'] for signal in groups[group_name]]

    def _open_trade(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> bool:
        """💼 فتح صفقة جديدة"""
        try:
            logger.debug(f"🚀 فتح صفقة: {symbol} | النمط: {mode_key} | الاستراتيجية: {strategy_type}")
            return self.trade_manager.open_trade(symbol, direction, strategy_type, mode_key)
        except Exception as e:
            logger.error(f"❌ فشل فتح الصفقة: {e}")
            return False

    def _count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """📊 حساب الصفقات حسب النمط"""
        count = 0
        for trade_id, trade in self.trade_manager.active_trades.items():
            if trade.get('symbol') == symbol and trade.get('mode_key') == mode_key:
                count += 1
        return count

    def _reset_used_signals(self, symbol: str, direction: str, trade_results: List[Dict]):
        """🧹 إعادة تعيين الإشارات المستخدمة"""
        try:
            group_key = symbol.upper().strip()
            
            if not trade_results:
                return
            
            # 🎯 جمع جميع الإشارات المستخدمة
            used_signals = set()
            for trade in trade_results:
                for group in ['group1_signals', 'group2_signals', 'group3_signals']:
                    signals = trade.get(group, [])
                    used_signals.update(signals)
            
            logger.debug(f"🎯 الإشارات المستخدمة التي سيتم حذفها: {used_signals}")
            
            if not used_signals:
                return
            
            # 🗑️ حذف الإشارات المستخدمة
            removed_total = 0
            for group_type in ['group1_bullish', 'group1_bearish', 'group2_bullish', 
                              'group2_bearish', 'group3_bullish', 'group3_bearish']:
                original_count = len(self.pending_signals[group_key][group_type])
                
                self.pending_signals[group_key][group_type] = [
                    signal for signal in self.pending_signals[group_key][group_type]
                    if signal['signal_type'] not in used_signals
                ]
                
                removed_count = original_count - len(self.pending_signals[group_key][group_type])
                removed_total += removed_count
            
            logger.debug(f"✅ تم حذف {removed_total} إشارة مستخدمة")
            
        except Exception as e:
            logger.error(f"⚠️ خطأ في إعادة تعيين الإشارات: {e}")

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
                'total_signals': sum([
                    len(groups['group1_bullish']), len(groups['group1_bearish']),
                    len(groups['group2_bullish']), len(groups['group2_bearish']),
                    len(groups['group3_bullish']), len(groups['group3_bearish'])
                ]),
                'updated_at': groups['updated_at']
            }
        except Exception as e:
            logger.error(f"⚠️ خطأ في إحصائيات المجموعات: {e}")
            return None

    def cleanup_all_groups(self) -> bool:
        """🧹 تنظيف جميع المجموعات"""
        try:
            count_before = len(self.pending_signals)
            self.pending_signals.clear()
            logger.debug(f"✅ تم تنظيف جميع المجموعات: {count_before} → 0")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف المجموعات: {e}")
            return False