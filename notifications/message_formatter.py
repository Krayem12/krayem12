# notifications/message_formatter.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter  # 🆕 إضافة لعرض الإشارات الفريدة

class MessageFormatter:
    """فئة متخصصة في تنسيق رسائل النظام - بدون تكرار في الإشارات"""

    @staticmethod
    def format_detailed_entry_message(symbol, signal_type, direction, current_trend, strategy_type, 
                                    group1_signals, group2_signals, group3_signals, 
                                    group4_signals, group5_signals,  # 🆕 إضافة Group4 و Group5
                                    active_for_symbol, total_active, config, mode_key="TRADING_MODE"):
        """🎯 تنسيق رسالة دخول مفصلة بدون تكرار في الإشارات"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        trend_icon = '🟢📈 BULLISH' if str(current_trend).lower() == 'bullish' else '🔴📉 BEARISH'

        align_text = '🟢 مطابق للاتجاه العام' if (
            (direction == 'buy' and str(current_trend).lower() == 'bullish') or
            (direction == 'sell' and str(current_trend).lower() == 'bearish')
        ) else '🔴 غير مطابق'

        # 🎯 تحديد نوع الصفقة
        trade_types = {
            'TRADING_MODE': '🟦 أساسي',
            'TRADING_MODE1': '🟨 نمط 1', 
            'TRADING_MODE2': '🟪 نمط 2'
        }
        trade_type = trade_types.get(mode_key, '🟦 أساسي')

        # 🛠️ الإصلاح: معالجة آمنة لبيانات الإشارات
        safe_group1 = group1_signals or []
        safe_group2 = group2_signals or []
        safe_group3 = group3_signals or []
        safe_group4 = group4_signals or []  # 🆕 إضافة Group4
        safe_group5 = group5_signals or []  # 🆕 إضافة Group5

        # 🆕 الجديد: تصفية الإشارات مع إزالة التكرار وعرض الإشارات الفريدة فقط
        signals_display = MessageFormatter._filter_and_deduplicate_signals_dynamic(
            strategy_type, safe_group1, safe_group2, safe_group3, safe_group4, safe_group5
        )

        return (
            "✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 🎯 نوع الصفقة: {trade_type}\n"
            f"┃ 🎯 نوع العملية: {'🟢 شراء' if direction=='buy' else '🔴 بيع'}\n"
            f"┃ 📊 اتجاه الرمز: {trend_icon}\n"
            f"┃ 🎯 محاذاة الاتجاه: {align_text}\n"
            f"┃ 🎯 الاستراتيجية: {strategy_type}\n"
            f"┃ 📋 الإشارة الرئيسية: {signal_type}\n"
            f"{signals_display}\n"
            f"┃ 📊 صفقات {symbol}: {active_for_symbol}/{config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    @staticmethod
    def _filter_and_deduplicate_signals_dynamic(strategy_type, group1_signals, group2_signals, group3_signals, group4_signals, group5_signals):
        """🎯 دالة ديناميكية: تصفية الإشارات بناءً على الاستراتيجية فقط"""
        
        # تحديد المجموعات المطلوبة بناءً على الاستراتيجية
        required_groups = strategy_type.split('_') if strategy_type else []
        
        # 🎯 تصفية المجموعات بناءً على الاستراتيجية فقط
        group_mapping = {
            'GROUP1': group1_signals,
            'GROUP2': group2_signals, 
            'GROUP3': group3_signals,
            'GROUP4': group4_signals,
            'GROUP5': group5_signals
        }
        
        # إعداد الألوان والأيقونات للمجموعات
        group_display_info = {
            'GROUP1': {'color': '🔴', 'name': 'الأولى'},
            'GROUP2': {'color': '🔵', 'name': 'الثانية'}, 
            'GROUP3': {'color': '🟢', 'name': 'الثالثة'},
            'GROUP4': {'color': '🟠', 'name': 'الرابعة'},
            'GROUP5': {'color': '🟣', 'name': 'الخامسة'}
        }
        
        display = ""
        
        # معالجة كل مجموعة مطلوبة
        for group in required_groups:
            signals = group_mapping.get(group, [])
            if signals:
                if display:  # إضافة سطر فاصل إذا كان هناك إشارات سابقة
                    display += "\n"
                
                group_info = group_display_info.get(group, {'color': '⚪', 'name': group})
                group_counter = Counter(signals)
                total_signals = len(signals)
                unique_signals = len(group_counter)
                
                numbered_signals = [f"┃   {i+1}. {signal}" for i, signal in enumerate(group_counter.keys())]
                display += f"┃ {group_info['color']} إشارات المجموعة {group_info['name']} ({total_signals} إشارة, {unique_signals} فريدة):\n" + "\n".join(numbered_signals)
        
        # إذا لم توجد أي إشارات بعد التصفية
        if not display:
            display = "┃   ⚠️ لا توجد إشارات مسجلة"
        
        return display

    @staticmethod
    def _filter_and_deduplicate_signals(strategy_type, group1_signals, group2_signals, group3_signals, group4_signals, group5_signals):
        """🎯 دالة جديدة: تصفية الإشارات مع إزالة التكرار وعرض الإشارات الفريدة فقط"""
        
        # استخدام النسخة الديناميكية للتوافق
        return MessageFormatter._filter_and_deduplicate_signals_dynamic(
            strategy_type, group1_signals, group2_signals, group3_signals, group4_signals, group5_signals
        )

    @staticmethod
    def _filter_signals_by_strategy_strict(strategy_type, group1_signals, group2_signals, group3_signals):
        """🎯 دالة مساعدة: تصفية صارمة للإشارات حسب الاستراتيجية (للتوافق)"""
        # استدعاء الدالة الجديدة للحفاظ على التوافق
        return MessageFormatter._filter_and_deduplicate_signals_dynamic(strategy_type, group1_signals, group2_signals, group3_signals, [], [])

    @staticmethod
    def format_trend_message(signal_data, new_trend, old_trend):
        """📊 تنسيق رسالة تغيير الاتجاه الأساسية - للإستخدام في webhook_handler"""
        symbol = signal_data['symbol']
        signal = signal_data['signal_type']
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        # تحديد الأيقونة والنص بناءً على الاتجاه الجديد
        if new_trend.lower() == 'bullish':
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        else:
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"

        # تحديد نص الحالة بناءً على التغيير الحقيقي
        if old_trend == 'UNKNOWN' or old_trend is None:
            status_text = f"تحديد اتجاه جديد"
        elif old_trend == new_trend:
            status_text = f"تأكيد الاتجاه ({old_trend} → {new_trend})"
        else:
            status_text = f"تغيير اتجاه ({old_trend} → {new_trend})"

        return f"""☰☰☰ 📊 تغيير الاتجاه ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal}
┃ 🔄 الحالة: {status_text}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp}"""

    @staticmethod
    def format_detailed_trend_message(symbol: str, new_trend: str, old_trend: str, 
                                    trigger_signal: str, removed_signals: List[Dict], 
                                    remaining_signals: List[Dict], removed_count: int) -> str:
        """🎯 تنسيق رسالة تفصيلية عن تغيير الاتجاه والتنظيف"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        # 🎯 تحديد الأيقونة والنص بناءً على الاتجاه الجديد
        if new_trend.lower() == 'bullish':
            trend_icon, trend_text, trend_color = "🟢", "صاعد (شراء)", "🟢"
        else:
            trend_icon, trend_text, trend_color = "🔴", "هابط (بيع)", "🔴"

        # 🎯 نص الحالة بناءً على التغيير
        if old_trend == 'UNKNOWN' or old_trend is None:
            status_text = f"تحديد اتجاه جديد"
        elif old_trend == new_trend:
            status_text = f"تأكيد الاتجاه ({old_trend} → {new_trend})"
        else:
            status_text = f"تغيير اتجاه ({old_trend} → {new_trend})"

        # 🎯 قسم الإشارات المحذوفة
        removed_section = ""
        if removed_count > 0 and removed_signals:
            removed_section = f"┃ 🗑️  الإشارات المحذوفة ({removed_count} إشارة):\n"
            for i, signal in enumerate(removed_signals[:10]):  # عرض أول 10 إشارات فقط
                age_text = f" ({signal.get('age_minutes', 0)} دقيقة)" if signal.get('age_minutes') else ""
                removed_section += f"┃    {i+1}. {signal['signal_type']} - {signal['group']}{age_text}\n"
            
            if removed_count > 10:
                removed_section += f"┃    ... و{removed_count - 10} إشارة أخرى\n"
        else:
            removed_section = "┃ 🗑️  لا توجد إشارات محذوفة\n"

        # 🎯 قسم الإشارات المتبقية
        remaining_section = ""
        if remaining_signals:
            # تجميع الإشارات حسب المجموعة
            signals_by_group = {}
            for signal in remaining_signals:
                group = signal['group']
                if group not in signals_by_group:
                    signals_by_group[group] = []
                signals_by_group[group].append(signal['signal_type'])
            
            remaining_section = f"┃ 📊 الإشارات المتبقية ({len(remaining_signals)} إشارة):\n"
            for group, signals in signals_by_group.items():
                signals_text = ", ".join(signals[:3])  # عرض أول 3 إشارات من كل مجموعة
                if len(signals) > 3:
                    signals_text += f" ... +{len(signals) - 3}"
                remaining_section += f"┃    • {group}: {signals_text}\n"
        else:
            remaining_section = "┃ 📊 لا توجد إشارات متبقية\n"

        # 🎯 قسم الإحصائيات
        stats_section = f"┃ 📈 الإحصائيات:\n"
        stats_section += f"┃    • الإشارات المحذوفة: {removed_count}\n"
        stats_section += f"┃    • الإشارات المتبقية: {len(remaining_signals)}\n"
        stats_section += f"┃    • الإشارة المسببة: {trigger_signal}\n"

        return (
            "☰☰☰ 📊 تقرير تغيير الاتجاه التفصيلي ☰☰☰\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ {trend_color} الاتجاه: {trend_icon} {trend_text}\n"
            f"┃ 🔄 الحالة: {status_text}\n"
            f"{removed_section}"
            f"{remaining_section}"
            f"{stats_section}"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    @staticmethod
    def format_exit_message(symbol, signal_type, active_for_symbol, total_active, config):
        """Format exit message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        return (
            "════ 🚪 إشـــــــارة خــــــروج ════\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 📝 السبب: إشارة خروج: {signal_type}\n"
            f"┃ 📊 صفقات {symbol} المتبقية: {active_for_symbol}/{config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    @staticmethod
    def format_simple_trend_message(symbol: str, new_trend: str, old_trend: str, trigger_signal: str) -> str:
        """📊 تنسيق رسالة اتجاه مبسطة - بديل احتياطي"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        
        if new_trend.lower() == 'bullish':
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        else:
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"

        status_text = "تحديد اتجاه جديد" if old_trend in [None, 'UNKNOWN'] else f"تغيير اتجاه ({old_trend} → {new_trend})"

        return f"""☰☰☰ 📊 تغيير الاتجاه ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {trigger_signal}
┃ 🔄 الحالة: {status_text}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp}"""

    @staticmethod
    def format_detailed_entry_message_fixed(symbol, signal_type, direction, current_trend, strategy_type, 
                                          group1_signals, group2_signals, group3_signals, 
                                          group4_signals, group5_signals,  # 🆕 إضافة Group4 و Group5
                                          active_for_symbol, total_active, config, mode_key="TRADING_MODE"):
        """🎯 إصدار معدل - معالجة آمنة لبيانات group4_signals و group5_signals"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        trend_icon = '🟢📈 BULLISH' if str(current_trend).lower() == 'bullish' else '🔴📉 BEARISH'

        align_text = '🟢 مطابق للاتجاه العام' if (
            (direction == 'buy' and str(current_trend).lower() == 'bullish') or
            (direction == 'sell' and str(current_trend).lower() == 'bearish')
        ) else '🔴 غير مطابق'

        # 🎯 تحديد نوع الصفقة
        trade_types = {
            'TRADING_MODE': '🟦 أساسي',
            'TRADING_MODE1': '🟨 نمط 1', 
            'TRADING_MODE2': '🟪 نمط 2'
        }
        trade_type = trade_types.get(mode_key, '🟦 أساسي')

        # 🛠️ الإصلاح: معالجة آمنة لبيانات group4_signals و group5_signals
        safe_group1 = group1_signals if group1_signals is not None else []
        safe_group2 = group2_signals if group2_signals is not None else []
        safe_group3 = group3_signals if group3_signals is not None else []
        safe_group4 = group4_signals if group4_signals is not None else []  # 🆕 إضافة Group4
        safe_group5 = group5_signals if group5_signals is not None else []  # 🆕 إضافة Group5

        # 🎯 تصفية الإشارات الصارمة حسب الاستراتيجية الفعلية
        signals_display = MessageFormatter._filter_and_deduplicate_signals_dynamic(
            strategy_type, safe_group1, safe_group2, safe_group3, safe_group4, safe_group5
        )

        return (
            "✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 🎯 نوع الصفقة: {trade_type}\n"
            f"┃ 🎯 نوع العملية: {'🟢 شراء' if direction=='buy' else '🔴 بيع'}\n"
            f"┃ 📊 اتجاه الرمز: {trend_icon}\n"
            f"┃ 🎯 محاذاة الاتجاه: {align_text}\n"
            f"┃ 🎯 الاستراتيجية: {strategy_type}\n"
            f"┃ 📋 الإشارة الرئيسية: {signal_type}\n"
            f"{signals_display}\n"
            f"┃ 📊 صفقات {symbol}: {active_for_symbol}/{config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )