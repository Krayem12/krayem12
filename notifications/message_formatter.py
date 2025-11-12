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

        # 🆕 الجديد: تصفية الإشارات مع إزالة التكرار وعرض الإشارات الفريدة فقط
        signals_display = MessageFormatter._filter_and_deduplicate_signals(
            strategy_type, safe_group1, safe_group2, safe_group3
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
    def _filter_and_deduplicate_signals(strategy_type, group1_signals, group2_signals, group3_signals):
        """🎯 دالة جديدة: تصفية الإشارات مع إزالة التكرار وعرض الإشارات الفريدة فقط"""
        
        # نسخ القوائم لتجنب التعديل على الأصل
        filtered_group1 = list(group1_signals) if group1_signals else []
        filtered_group2 = list(group2_signals) if group2_signals else []
        filtered_group3 = list(group3_signals) if group3_signals else []
        
        # 🎯 تطبيق التصفية الصارمة حسب الاستراتيجية
        if strategy_type == 'GROUP1':
            filtered_group2 = []
            filtered_group3 = []
        elif strategy_type == 'GROUP1_GROUP2':
            filtered_group3 = []
        elif strategy_type == 'GROUP1_GROUP3':
            filtered_group2 = []
        # GROUP1_GROUP2_GROUP3 تظهر جميع الإشارات
        
        # 🆕 الجديد: إزالة التكرار وعرض الإشارات الفريدة فقط مع الحفاظ على العدد الأصلي
        display = ""
        
        # معالجة المجموعة الأولى - إزالة التكرار
        if filtered_group1:
            # حساب التكرارات
            group1_counter = Counter(filtered_group1)
            total_group1 = len(filtered_group1)
            unique_group1 = len(group1_counter)
            
            numbered_group1 = [f"┃   {i+1}. {signal}" for i, signal in enumerate(group1_counter.keys())]
            display += f"┃ 🔴 إشارات المجموعة الأولى ({total_group1} إشارة, {unique_group1} فريدة):\n" + "\n".join(numbered_group1)
        
        # معالجة المجموعة الثانية - إزالة التكرار
        if filtered_group2:
            if display:  # إضافة سطر فاصل إذا كان هناك إشارات سابقة
                display += "\n"
            
            group2_counter = Counter(filtered_group2)
            total_group2 = len(filtered_group2)
            unique_group2 = len(group2_counter)
            
            numbered_group2 = [f"┃   {i+1}. {signal}" for i, signal in enumerate(group2_counter.keys())]
            display += f"┃ 🔵 إشارات المجموعة الثانية ({total_group2} إشارة, {unique_group2} فريدة):\n" + "\n".join(numbered_group2)
        
        # معالجة المجموعة الثالثة - إزالة التكرار
        if filtered_group3:
            if display:  # إضافة سطر فاصل إذا كان هناك إشارات سابقة
                display += "\n"
            
            group3_counter = Counter(filtered_group3)
            total_group3 = len(filtered_group3)
            unique_group3 = len(group3_counter)
            
            numbered_group3 = [f"┃   {i+1}. {signal}" for i, signal in enumerate(group3_counter.keys())]
            display += f"┃ 🟢 إشارات المجموعة الثالثة ({total_group3} إشارة, {unique_group3} فريدة):\n" + "\n".join(numbered_group3)
        
        # إذا لم توجد أي إشارات بعد التصفية
        if not display:
            display = "┃   ⚠️ لا توجد إشارات مسجلة"
        
        return display

    @staticmethod
    def _filter_signals_by_strategy_strict(strategy_type, group1_signals, group2_signals, group3_signals):
        """🎯 دالة مساعدة: تصفية صارمة للإشارات حسب الاستراتيجية (للتوافق)"""
        # استدعاء الدالة الجديدة للحفاظ على التوافق
        return MessageFormatter._filter_and_deduplicate_signals(strategy_type, group1_signals, group2_signals, group3_signals)

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
                                          active_for_symbol, total_active, config, mode_key="TRADING_MODE"):
        """🎯 إصدار معدل - معالجة آمنة لبيانات group3_signals"""
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

        # 🛠️ الإصلاح: معالجة آمنة لبيانات group3_signals
        safe_group1 = group1_signals if group1_signals is not None else []
        safe_group2 = group2_signals if group2_signals is not None else []
        safe_group3 = group3_signals if group3_signals is not None else []

        # 🎯 تصفية الإشارات الصارمة حسب الاستراتيجية الفعلية
        signals_display = MessageFormatter._filter_and_deduplicate_signals(
            strategy_type, safe_group1, safe_group2, safe_group3
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