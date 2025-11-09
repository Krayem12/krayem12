# core/group_manager.py
from datetime import datetime, timedelta
import hashlib
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class GroupManager:
    """إدارة نظام التجميع (Group1 / Group2 / Group3) مع نظام MULTI-MODE - الإصدار المُصحح جذرياً"""

    def __init__(self, config, trade_manager):
        self.config = config
        self.trade_manager = trade_manager
        self.pending_signals = {}
        self.error_log = []
        self._last_cleanup_time = None
        self.mode_performance = {}

    def _get_group_key(self, symbol: str) -> str:
        """إنشاء مفتاح مجموعة للرمز"""
        return symbol.upper().strip()

    def _create_group_if_missing(self, group_key: str):
        """إنشاء مجموعة جديدة إذا لم تكن موجودة"""
        if group_key not in self.pending_signals:
            self.pending_signals[group_key] = {
                "group1_bullish": [], "group1_bearish": [], 
                "group2_bullish": [], "group2_bearish": [],
                "group3_bullish": [], "group3_bearish": [],
                "created_at": datetime.now(), "updated_at": datetime.now()
            }

    def route_signal(self, symbol: str, signal_data: Dict, classification: str) -> List[Dict]:
        """🎯 استلام الإشارة وتوجيهها مع تحقق إضافي من التصنيف"""
        try:
            # 🎯 تحقق إضافي: التأكد أن التصنيف صحيح
            if classification not in ['entry_bullish', 'entry_bearish', 'entry_bullish1', 'entry_bearish1', 'group3']:
                print(f"🚫 تصنيف غير صالح للإشارة: {classification}")
                return []

            # تجاهل إشارات الاتجاه نهائياً
            if classification in ["trend", "trend_confirm"]:
                print(f"🔷 إشارة اتجاه ({classification}) - تم تجاهلها في نظام المجموعات")
                return []

            group_key = self._get_group_key(symbol)
            self._create_group_if_missing(group_key)
            
            # تنظيف الإشارات القديمة
            self._clean_old_signals(group_key)

            # تحديد المجموعة المستهدفة والاتجاه
            direction = None
            group_type = None
            
            if classification == "entry_bullish":
                group_type = "group1_bullish"
                direction = "buy"
            elif classification == "entry_bearish":
                group_type = "group1_bearish" 
                direction = "sell"
            elif classification == "entry_bullish1":
                group_type = "group2_bullish"
                direction = "buy"
            elif classification == "entry_bearish1":
                group_type = "group2_bearish"
                direction = "sell"
            elif classification == "group3":
                direction = self._determine_group3_direction(signal_data['signal_type'])
                if direction == "unknown":
                    print(f"⚠️ اتجاه GROUP3 غير محدد: {signal_data['signal_type']}")
                    return []
                group_type = "group3_bullish" if direction == "buy" else "group3_bearish"
            else:
                print(f"⚠️ تصنيف غير معروف: {classification}")
                return []

            # التحقق من محاذاة الاتجاه
            current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
            if current_trend == 'UNKNOWN':
                print(f"⏸️  تجاهل الإشارة لأن الاتجاه غير معروف: {symbol}")
                return []
                
            if not self._is_signal_aligned_with_trend(direction, current_trend):
                print(f"🚫 تجاهل الإشارة المخالفة للاتجاه: {direction.upper()} بينما الاتجاه {current_trend.upper()}")
                return []

            # منع التكرار
            signal_text = f"{signal_data['signal_type']}_{classification}_{symbol}_{datetime.now().strftime('%Y%m%d%H')}"
            sig_hash = hashlib.md5(signal_text.encode()).hexdigest()
            
            existing_hashes = [s['hash'] for s in self.pending_signals[group_key][group_type]]
            if sig_hash in existing_hashes:
                print(f"🔁 إشارة مكررة - تم تجاهلها: {signal_data['signal_type']}")
                return []

            # تخزين الإشارة
            signal_info = {
                'hash': sig_hash,
                'signal_type': signal_data['signal_type'],
                'classification': classification,
                'timestamp': datetime.now(),
                'direction': direction,
                'symbol': symbol
            }
            
            self._add_signal_safely(group_key, group_type, signal_info)
            self.pending_signals[group_key]["updated_at"] = datetime.now()

            print(f"📥 إشارة مضافَة إلى {group_type}: {signal_data['signal_type']} | الاتجاه: {direction.upper()}")

            # تقييم شروط الدخول
            trade_results = self._evaluate_entry_conditions(symbol, direction)
            return trade_results

        except Exception as e:
            error_msg = f"💥 خطأ في route_signal: {symbol} | {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return []

    def _clean_old_signals(self, group_key: str, max_age_minutes: int = 30):
        """تنظيف الإشارات القديمة"""
        if group_key not in self.pending_signals:
            return
            
        now = datetime.now()
        if self._last_cleanup_time and (now - self._last_cleanup_time).total_seconds() < 300:
            return
        
        groups = self.pending_signals[group_key]
        cleaned_count = 0
        
        for group_type in ['group1_bullish', 'group1_bearish', 'group2_bullish', 
                          'group2_bearish', 'group3_bullish', 'group3_bearish']:
            original_count = len(groups[group_type])
            groups[group_type] = [
                signal for signal in groups[group_type]
                if (now - signal['timestamp']).total_seconds() < max_age_minutes * 60
            ]
            cleaned_count += (original_count - len(groups[group_type]))
        
        if cleaned_count > 0:
            print(f"🧹 تم تنظيف {cleaned_count} إشارة قديمة لـ {group_key}")
        
        self._last_cleanup_time = now

    def _add_signal_safely(self, group_key: str, group_type: str, signal_info: Dict, max_signals_per_group: int = 50):
        """إضافة إشارة مع التحقق من الحد الأقصى"""
        if len(self.pending_signals[group_key][group_type]) >= max_signals_per_group:
            removed = self.pending_signals[group_key][group_type].pop(0)
            print(f"🗑️  تم إزالة إشارة قديمة: {removed['signal_type']}")
        
        self.pending_signals[group_key][group_type].append(signal_info)

    def _determine_group3_direction(self, signal_type: str) -> str:
        """تحديد اتجاه GROUP3"""
        signal_lower = signal_type.lower().strip()
        
        if not signal_lower:
            return "unknown"
        
        group3_signals = self.config.get('ENTRY_SIGNALS_GROUP3', [])
        for signal in group3_signals:
            signal_lower_clean = signal.lower().strip()
            if signal_lower_clean and signal_lower_clean in signal_lower:
                if any(word in signal_lower for word in ['bullish', 'above', 'co_50', 'up', 'long', 'rising', 'over', 'buy']):
                    return "buy"
                elif any(word in signal_lower for word in ['bearish', 'below', 'cu_50', 'down', 'short', 'falling', 'under', 'sell']):
                    return "sell"
        
        return "unknown"

    def _is_signal_aligned_with_trend(self, signal_direction: str, current_trend: str) -> bool:
        """التحقق من محاذاة الإشارة مع الاتجاه الحالي"""
        if current_trend == 'UNKNOWN':
            return False
        return (current_trend == 'bullish' and signal_direction == 'buy') or \
               (current_trend == 'bearish' and signal_direction == 'sell')

    def _evaluate_entry_conditions(self, symbol: str, direction: str) -> List[Dict]:
        """🎯 الإصلاح الجذري: تقييم شروط الدخول مع التحقق من الأنماط المفعلة فقط"""
        try:
            group_key = self._get_group_key(symbol)
            if group_key not in self.pending_signals:
                return []

            groups = self.pending_signals[group_key]

            req_g1 = self.config["REQUIRED_CONFIRMATIONS_GROUP1"]
            req_g2 = self.config["REQUIRED_CONFIRMATIONS_GROUP2"] 
            req_g3 = self.config["REQUIRED_CONFIRMATIONS_GROUP3"]

            # حساب الإشارات بناءً على الاتجاه
            if direction == "buy":
                g1_count = len(groups["group1_bullish"])
                g2_count = len(groups["group2_bullish"])
                g3_count = len(groups["group3_bullish"])
            else:
                g1_count = len(groups["group1_bearish"])
                g2_count = len(groups["group2_bearish"])
                g3_count = len(groups["group3_bearish"])

            print(f"📊 إحصائيات المجموعات لـ {symbol} [{direction.upper()}]: G1={g1_count}/{req_g1}, G2={g2_count}/{req_g2}, G3={g3_count}/{req_g3}")

            # 🎯 الإصلاح الجذري: التحقق من شروط المجموعة الأولى أولاً (إلزامي)
            if g1_count < req_g1:
                print(f"❌ شروط المجموعة الأولى غير محققة لـ {symbol}")
                return []

            # 🎯 الإصلاح الجذري: تحديد الأنماط المفعلة فقط حسب الإعدادات
            active_modes = self._get_active_modes()
            print(f"🎯 الأنماط المفعلة حسب الإعدادات: {active_modes}")

            # 🎯 الإصلاح الجذري: تقييم الأنماط المفعلة فقط
            trade_results = []
            opened_any_trade = False
            
            for mode_key in active_modes:
                mode_result = self._evaluate_single_mode(mode_key, symbol, direction, g1_count, g2_count, g3_count)
                if mode_result:
                    trade_results.append(mode_result)
                    opened_any_trade = True
                    print(f"✅ تم فتح صفقة بالنمط {mode_key}")

            # إعادة تعيين الإشارات المستخدمة
            if opened_any_trade:
                self._reset_used_signals(symbol, direction, trade_results)
                print(f"🎯 تم فتح {len(trade_results)} صفقة لـ {symbol}")
            else:
                print(f"⏹️  لم يتم فتح أي صفقة لـ {symbol}")

            return trade_results

        except Exception as e:
            error_msg = f"💥 خطأ في _evaluate_entry_conditions: {symbol} | {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return []

    def _get_active_modes(self) -> List[str]:
        """🎯 الإصلاح الجذري: الحصول على الأنماط المفعلة فقط حسب الإعدادات"""
        active_modes = ['TRADING_MODE']  # النمط الأساسي دائماً مفعل
        
        if self.config.get('TRADING_MODE1_ENABLED', False):
            active_modes.append('TRADING_MODE1')
        if self.config.get('TRADING_MODE2_ENABLED', False):
            active_modes.append('TRADING_MODE2')
        
        return active_modes

    def _reset_used_signals(self, symbol: str, direction: str, trade_results: List[Dict]):
        """إعادة تعيين الإشارات المستخدمة"""
        try:
            group_key = self._get_group_key(symbol)
            
            if not trade_results:
                return
            
            used_signals = set()
            for trade in trade_results:
                used_signals.update(trade.get('group1_signals', []))
                used_signals.update(trade.get('group2_signals', []))
                used_signals.update(trade.get('group3_signals', []))
            
            for group_type in ['group1_bullish', 'group1_bearish', 'group2_bullish', 
                              'group2_bearish', 'group3_bullish', 'group3_bearish']:
                original_count = len(self.pending_signals[group_key][group_type])
                self.pending_signals[group_key][group_type] = [
                    signal for signal in self.pending_signals[group_key][group_type]
                    if signal['signal_type'] not in used_signals
                ]
                removed_count = original_count - len(self.pending_signals[group_key][group_type])
                if removed_count > 0:
                    print(f"🔄 تم إزالة {removed_count} إشارة مستخدمة من {group_type}")
            
            self.pending_signals[group_key]["updated_at"] = datetime.now()
            
        except Exception as e:
            error_msg = f"💥 خطأ في _reset_used_signals: {symbol} | {str(e)}"
            print(error_msg)
            logger.error(error_msg)

    def _update_mode_performance(self, trade_results: List[Dict]):
        """تحديث إحصائيات أداء الأنماط"""
        for trade in trade_results:
            mode_key = trade.get('mode_key', 'TRADING_MODE')
            if mode_key not in self.mode_performance:
                self.mode_performance[mode_key] = {
                    'trades_opened': 0,
                    'last_trade_time': None,
                    'performance_score': 0
                }
            
            self.mode_performance[mode_key]['trades_opened'] += 1
            self.mode_performance[mode_key]['last_trade_time'] = datetime.now()

    def _evaluate_single_mode(self, mode_key: str, symbol: str, direction: str, 
                             g1_count: int, g2_count: int, g3_count: int) -> Optional[Dict]:
        """🎯 تقييم نمط تداول فردي مع منع الخلط بين المجموعات"""
        try:
            # التحقق من الحدود أولاً
            current_count = self.trade_manager.get_active_trades_count(symbol)
            if current_count >= self.config['MAX_TRADES_PER_SYMBOL']:
                print(f"⏹️  النمط {mode_key} متوقف - وصل الرمز {symbol} للحد الأقصى")
                return None
            
            # التحقق من توازن الصفقات بين الأنماط
            if not self._should_open_trade_for_mode(mode_key, symbol):
                return None
                
            trading_mode = self.config[mode_key]
            print(f"🎯 فحص النمط {mode_key}: {trading_mode}")
            
            # 🎯 التحقق الدقيق من الشروط حسب الاستراتيجية
            condition_met = False
            required_groups = ['GROUP1']  # GROUP1 مطلوب دائماً
            
            if trading_mode == 'GROUP1':
                condition_met = True
                print(f"✅ {mode_key}: وضع GROUP1 - مطلوب G1 فقط")
                
            elif trading_mode == 'GROUP1_GROUP2':
                group2_enabled = self.config.get('GROUP2_ENABLED', False)
                condition_met = group2_enabled and g2_count >= self.config["REQUIRED_CONFIRMATIONS_GROUP2"]
                required_groups = ['GROUP1', 'GROUP2']
                print(f"🔍 {mode_key}: وضع GROUP1_GROUP2 - G2={g2_count}/{self.config['REQUIRED_CONFIRMATIONS_GROUP2']}, مفعل={group2_enabled}")
                
            elif trading_mode == 'GROUP1_GROUP3':
                group3_enabled = self.config.get('GROUP3_ENABLED', False)
                condition_met = group3_enabled and g3_count >= self.config["REQUIRED_CONFIRMATIONS_GROUP3"]
                required_groups = ['GROUP1', 'GROUP3']
                print(f"🔍 {mode_key}: وضع GROUP1_GROUP3 - G3={g3_count}/{self.config['REQUIRED_CONFIRMATIONS_GROUP3']}, مفعل={group3_enabled}")
                
            elif trading_mode == 'GROUP1_GROUP2_GROUP3':
                group2_enabled = self.config.get('GROUP2_ENABLED', False)
                group3_enabled = self.config.get('GROUP3_ENABLED', False)
                g2_condition = group2_enabled and g2_count >= self.config["REQUIRED_CONFIRMATIONS_GROUP2"]
                g3_condition = group3_enabled and g3_count >= self.config["REQUIRED_CONFIRMATIONS_GROUP3"]
                condition_met = g2_condition and g3_condition
                required_groups = ['GROUP1', 'GROUP2', 'GROUP3']
                print(f"🔍 {mode_key}: وضع GROUP1_GROUP2_GROUP3 - G2={g2_condition}, G3={g3_condition}")
                
            else:
                print(f"⚠️ {mode_key}: وضع تداول غير معروف: {trading_mode}")
                condition_met = False

            if condition_met:
                print(f"🎯 شروط الدخول متحققة لـ {symbol} باستراتيجية {trading_mode} | النمط: {mode_key}")
                success = self._open_trade(symbol, direction, trading_mode, mode_key)
                if success:
                    # 🎯 منع الخلط: الحصول على الإشارات حسب المجموعات المطلوبة فقط
                    group_key = self._get_group_key(symbol)
                    groups = self.pending_signals[group_key]
                    
                    trade_info = {
                        'symbol': symbol,
                        'direction': direction,
                        'group1_signals': self._get_signals_by_direction(groups, direction, 'group1') if 'GROUP1' in required_groups else [],
                        'group2_signals': self._get_signals_by_direction(groups, direction, 'group2') if 'GROUP2' in required_groups else [],
                        'group3_signals': self._get_signals_by_direction(groups, direction, 'group3') if 'GROUP3' in required_groups else [],
                        'strategy_type': trading_mode,
                        'mode_key': mode_key
                    }
                    return trade_info
                else:
                    print(f"❌ فشل فتح الصفقة للنمط {mode_key}")
            else:
                print(f"⏹️  شروط النمط {mode_key} غير محققة لـ {symbol}")
    
        except Exception as e:
            error_msg = f"💥 خطأ في _evaluate_single_mode: {mode_key} | {symbol} | {str(e)}"
            print(error_msg)
            logger.error(error_msg)
    
        return None

    def _should_open_trade_for_mode(self, mode_key: str, symbol: str) -> bool:
        """التحقق من توازن الصفقات بين الأنماط"""
        current_mode_trades = self._count_trades_by_mode(symbol, mode_key)
        
        mode_limits = {
            'TRADING_MODE': self.config.get('MAX_TRADES_MODE_MAIN', self.config['MAX_TRADES_PER_SYMBOL']),
            'TRADING_MODE1': self.config.get('MAX_TRADES_MODE1', self.config['MAX_TRADES_PER_SYMBOL'] // 2),
            'TRADING_MODE2': self.config.get('MAX_TRADES_MODE2', self.config['MAX_TRADES_PER_SYMBOL'] // 2)
        }
        
        mode_limit = mode_limits.get(mode_key, 2)
        can_open = current_mode_trades < mode_limit
        
        if not can_open:
            print(f"⏹️  النمط {mode_key} وصل الحد: {current_mode_trades}/{mode_limit}")
        
        return can_open

    def _count_trades_by_mode(self, symbol: str, mode_key: str) -> int:
        """حساب عدد الصفقات الحالية لنمط معين"""
        count = 0
        for trade_id, trade in self.trade_manager.active_trades.items():
            if trade.get('symbol') == symbol and trade.get('mode_key') == mode_key:
                count += 1
        return count

    def _get_signals_by_direction(self, groups: Dict, direction: str, group_type: str) -> List[str]:
        """الحصول على الإشارات بناءً على الاتجاه ونوع المجموعة"""
        try:
            if direction == "buy":
                if group_type == 'group1':
                    return [s['signal_type'] for s in groups["group1_bullish"]]
                elif group_type == 'group2':
                    return [s['signal_type'] for s in groups["group2_bullish"]]
                elif group_type == 'group3':
                    return [s['signal_type'] for s in groups["group3_bullish"]]
            else:
                if group_type == 'group1':
                    return [s['signal_type'] for s in groups["group1_bearish"]]
                elif group_type == 'group2':
                    return [s['signal_type'] for s in groups["group2_bearish"]]
                elif group_type == 'group3':
                    return [s['signal_type'] for s in groups["group3_bearish"]]
            return []
        except Exception as e:
            print(f"⚠️ خطأ في _get_signals_by_direction: {e}")
            return []

    def _open_trade(self, symbol: str, direction: str, strategy_type: str, mode_key: str) -> bool:
        """فتح صفقة"""
        try:
            print(f"🚀 محاولة فتح صفقة: {symbol} | النمط: {mode_key} | الاستراتيجية: {strategy_type}")
            
            current_count = self.trade_manager.get_active_trades_count(symbol)
            if current_count >= self.config['MAX_TRADES_PER_SYMBOL']:
                print(f"❌ وصل الرمز {symbol} للحد الأقصى: {current_count}/{self.config['MAX_TRADES_PER_SYMBOL']}")
                return False
                
            total_trades = self.trade_manager.get_active_trades_count()
            if total_trades >= self.config['MAX_OPEN_TRADES']:
                print(f"❌ وصل النظام للحد الأقصى الإجمالي: {total_trades}/{self.config['MAX_OPEN_TRADES']}")
                return False
                
            return self.trade_manager.open_trade(symbol, direction, strategy_type, mode_key)
        
        except Exception as e:
            error_msg = f"💥 خطأ في _open_trade: {symbol} | {mode_key} | {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return False

    def get_group_stats(self, symbol: str) -> Optional[Dict]:
        """الحصول على إحصائيات المجموعات"""
        try:
            group_key = self._get_group_key(symbol)
            if group_key not in self.pending_signals:
                return None
                
            groups = self.pending_signals[group_key]
            stats = {
                'symbol': symbol,
                'group1_bullish': len(groups['group1_bullish']),
                'group1_bearish': len(groups['group1_bearish']),
                'group2_bullish': len(groups['group2_bullish']),
                'group2_bearish': len(groups['group2_bearish']),
                'group3_bullish': len(groups['group3_bullish']),
                'group3_bearish': len(groups['group3_bearish']),
                'created_at': groups['created_at'],
                'updated_at': groups['updated_at'],
                'total_signals': sum([
                    len(groups['group1_bullish']), len(groups['group1_bearish']),
                    len(groups['group2_bullish']), len(groups['group2_bearish']),
                    len(groups['group3_bullish']), len(groups['group3_bearish'])
                ])
            }
            return stats
        except Exception as e:
            print(f"⚠️ خطأ في get_group_stats: {e}")
            return None

    def cleanup_all_groups(self) -> bool:
        """تنظيف جميع المجموعات"""
        try:
            count_before = len(self.pending_signals)
            self.pending_signals.clear()
            print(f"🧹 تم تنظيف جميع المجموعات: {count_before} -> 0")
            return True
        except Exception as e:
            error_msg = f"💥 خطأ في cleanup_all_groups: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return False

    def get_system_status(self) -> Dict:
        """الحصول على حالة النظام"""
        try:
            total_groups = len(self.pending_signals)
            total_signals = 0
            for group_key, groups in self.pending_signals.items():
                total_signals += sum(len(groups[gt]) for gt in [
                    'group1_bullish', 'group1_bearish', 'group2_bullish', 
                    'group2_bearish', 'group3_bullish', 'group3_bearish'
                ])
            
            return {
                'total_groups': total_groups,
                'total_signals': total_signals,
                'error_count': len(self.error_log),
                'mode_performance': self.mode_performance,
                'last_cleanup': self._last_cleanup_time
            }
        except Exception as e:
            print(f"⚠️ خطأ في get_system_status: {e}")
            return {}