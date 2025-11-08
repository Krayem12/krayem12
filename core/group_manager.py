# core/group_manager.py
from datetime import datetime
import hashlib

class GroupManager:
    """إدارة نظام التجميع (Group1 / Group2 / Group3) مع تجاهل الإشارات المخالفة للاتجاه"""

    def __init__(self, config, trade_manager):
        self.config = config
        self.trade_manager = trade_manager
        self.pending_signals = {}

    def _get_group_key(self, symbol):
        return symbol.upper()

    def _create_group_if_missing(self, group_key):
        if group_key not in self.pending_signals:
            self.pending_signals[group_key] = {
                "group1_bullish": [],   # فصل الإشارات الصاعدة
                "group1_bearish": [],   # فصل الإشارات الهابطة
                "group2_bullish": [],   # فصل الإشارات الصاعدة
                "group2_bearish": [],   # فصل الإشارات الهابطة  
                "group3_bullish": [],   # فصل الإشارات الصاعدة
                "group3_bearish": [],   # فصل الإشارات الهابطة
                "updated_at": datetime.now()
            }

    def route_signal(self, symbol, signal_data, classification):
        """
        استلام الإشارة وتوجيهها حسب نوعها واتجاهها.
        """
        # تجاهل إشارات الاتجاه نهائياً - لا تدخل في نظام المجموعات
        if classification in ["trend", "trend_confirm"]:
            print(f"🔷 إشارة اتجاه ({classification}) - تم تجاهلها في نظام المجموعات")
            return False

        group_key = self._get_group_key(symbol)
        self._create_group_if_missing(group_key)

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
            group_type = "group3_bullish" if "above" in signal_data['signal_type'].lower() or "bullish" in signal_data['signal_type'].lower() else "group3_bearish"
            direction = "buy" if "above" in signal_data['signal_type'].lower() or "bullish" in signal_data['signal_type'].lower() else "sell"
        else:
            print(f"⚠️ تصنيف غير معروف: {classification}")
            return False

        # 🎯 التحقق من محاذاة الاتجاه الحالي للسهم
        current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
        
        # إذا كان الاتجاه غير معروف، نتجاهل جميع الإشارات
        if current_trend == 'UNKNOWN':
            print(f"⏸️  تجاهل الإشارة لأن الاتجاه غير معروف: {symbol} -> {direction.upper()}")
            return False
            
        # 🎯 التحقق من محاذاة الإشارة مع الاتجاه الحالي
        if not self._is_signal_aligned_with_trend(direction, current_trend):
            print(f"🚫 تجاهل الإشارة المخالفة للاتجاه: {direction.upper()} بينما الاتجاه {current_trend.upper()}")
            return False

        # منع تكرار نفس الإشارة (باستخدام بصمة hash)
        signal_text = f"{signal_data['signal_type']}_{classification}"
        sig_hash = hashlib.md5(signal_text.encode()).hexdigest()
        
        # التحقق من التكرار بناءً على الهاش
        existing_hashes = [s['hash'] for s in self.pending_signals[group_key][group_type]]
        if sig_hash in existing_hashes:
            print(f"🔁 إشارة مكررة - تم تجاهلها: {signal_data['signal_type']}")
            return False

        # تخزين معلومات الإشارة بشكل مفصل
        signal_info = {
            'hash': sig_hash,
            'signal_type': signal_data['signal_type'],
            'classification': classification,
            'timestamp': datetime.now(),
            'direction': direction
        }
        self.pending_signals[group_key][group_type].append(signal_info)
        self.pending_signals[group_key]["updated_at"] = datetime.now()

        print(f"📥 إشارة مضافَة إلى {group_type}: {signal_data['signal_type']} | الاتجاه: {direction.upper()}")

        # تقييم شروط الدخول وإرجاع معلومات الصفقة إذا تم فتحها
        trade_result = self._evaluate_entry_conditions(symbol, direction)
        return trade_result

    def _is_signal_aligned_with_trend(self, signal_direction, current_trend):
        """التحقق من محاذاة الإشارة مع الاتجاه الحالي"""
        if current_trend == 'UNKNOWN':
            return False  # نتجاهل جميع الإشارات إذا كان الاتجاه غير معروف
            
        if current_trend == 'bullish' and signal_direction == 'buy':
            return True
        elif current_trend == 'bearish' and signal_direction == 'sell':
            return True
        else:
            return False

    def _evaluate_entry_conditions(self, symbol, direction):
        """تقييم شروط الدخول بناءً على الاستراتيجية المحددة في .env"""
        group_key = self._get_group_key(symbol)
        groups = self.pending_signals[group_key]

        # استخدام الأسماء الصحيحة من الإعدادات
        req_g1 = self.config.get("REQUIRED_CONFIRMATIONS_GROUP1", 2)
        req_g2 = self.config.get("REQUIRED_CONFIRMATIONS_GROUP2", 1)
        req_g3 = self.config.get("REQUIRED_CONFIRMATIONS_GROUP3", 1)

        # 🎯 حساب الإشارات بناءً على الاتجاه
        if direction == "buy":
            g1_count = len(groups["group1_bullish"])
            g2_count = len(groups["group2_bullish"])
            g3_count = len(groups["group3_bullish"])
        else:  # direction == "sell"
            g1_count = len(groups["group1_bearish"])
            g2_count = len(groups["group2_bearish"])
            g3_count = len(groups["group3_bearish"])

        print(f"📊 إحصائيات المجموعات لـ {symbol} [{direction.upper()}]: G1={g1_count}/{req_g1}, G2={g2_count}/{req_g2}, G3={g3_count}/{req_g3}")

        # 🎯 التحقق من شروط المجموعة الأولى (الأساسية)
        if g1_count < req_g1:
            print(f"❌ شروط المجموعة الأولى غير محققة لـ {symbol}")
            return False

        # 🎯 التحقق من استراتيجية التداول المحددة
        trading_mode = self.config.get('TRADING_MODE', 'GROUP1_GROUP2_GROUP3')
        condition_met = False

        if trading_mode == 'GROUP1':
            condition_met = True
        elif trading_mode == 'GROUP1_GROUP2':
            condition_met = g2_count >= req_g2 and self.config.get('GROUP2_ENABLED', False)
        elif trading_mode == 'GROUP1_GROUP3':
            condition_met = g3_count >= req_g3 and self.config.get('GROUP3_ENABLED', False)
        elif trading_mode == 'GROUP1_GROUP2_GROUP3':
            condition_met = (g2_count >= req_g2 and self.config.get('GROUP2_ENABLED', False)) and \
                          (g3_count >= req_g3 and self.config.get('GROUP3_ENABLED', False))

        if condition_met:
            print(f"🎯 شروط الدخول متحققة لـ {symbol} باستراتيجية {trading_mode} | الاتجاه: {direction.upper()}")
            success = self._open_trade(symbol, direction)
            if success:
                # إرجاع معلومات الصفقة والإشارات التي أدت إليها
                trade_info = {
                    'symbol': symbol,
                    'direction': direction,
                    'group1_signals': self._get_signals_by_direction(groups, direction, 'group1'),
                    'group2_signals': self._get_signals_by_direction(groups, direction, 'group2'),
                    'group3_signals': self._get_signals_by_direction(groups, direction, 'group3'),
                    'strategy_type': trading_mode
                }
                self._reset_groups(symbol)
                return trade_info
            else:
                return False

        return False

    def _get_signals_by_direction(self, groups, direction, group_type):
        """الحصول على الإشارات بناءً على الاتجاه ونوع المجموعة"""
        if direction == "buy":
            if group_type == 'group1':
                return [s['signal_type'] for s in groups["group1_bullish"]]
            elif group_type == 'group2':
                return [s['signal_type'] for s in groups["group2_bullish"]]
            elif group_type == 'group3':
                return [s['signal_type'] for s in groups["group3_bullish"]]
        else:  # direction == "sell"
            if group_type == 'group1':
                return [s['signal_type'] for s in groups["group1_bearish"]]
            elif group_type == 'group2':
                return [s['signal_type'] for s in groups["group2_bearish"]]
            elif group_type == 'group3':
                return [s['signal_type'] for s in groups["group3_bearish"]]
        return []

    def _open_trade(self, symbol, direction):
        print(f"🚀 محاولة فتح صفقة: {symbol} | الاتجاه: {direction.upper()}")
        return self.trade_manager.open_trade(symbol, direction)

    def _reset_groups(self, symbol):
        group_key = self._get_group_key(symbol)
        self.pending_signals[group_key] = {
            "group1_bullish": [],
            "group1_bearish": [], 
            "group2_bullish": [],
            "group2_bearish": [],
            "group3_bullish": [],
            "group3_bearish": [],
            "updated_at": datetime.now()
        }
        print(f"🔄 تم إعادة تعيين المجموعات لـ {symbol}")