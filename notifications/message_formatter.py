# notifications/message_formatter.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

class MessageFormatter:
    """فئة متخصصة في تنسيق رسائل النظام - UPDATED WITH CORRECT TREND DISPLAY"""
    
    @staticmethod
    def format_trend_message(signal_data, new_trend, old_trend):
        """Format trend message with CORRECT old and new trends"""
        symbol = signal_data['symbol']
        signal = signal_data['signal_type']
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        # 🆕 تحديد الأيقونة والنص بناءً على الاتجاه الجديد
        if new_trend.lower() == 'bullish':
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        else:
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"

        # 🆕 تحديد نص الحالة بناءً على التغيير الحقيقي
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

    # ... باقي الدوال تبقى كما هي بدون تغيير ...
    @staticmethod
    def format_detailed_entry_message(symbol, signal_type, direction, current_trend, strategy_type, 
                                    group1_signals, group2_signals, group3_signals, 
                                    active_for_symbol, total_active, config):
        """Format detailed entry message with ALL signals information"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        trend_icon = '🟢📈 BULLISH' if current_trend.lower() == 'bullish' else '🔴📉 BEARISH'

        align_text = '🟢 مطابق للاتجاه العام' if (
            (direction == 'buy' and current_trend.lower() == 'bullish') or
            (direction == 'sell' and current_trend.lower() == 'bearish')
        ) else '🔴 غير مطابق'

        # تحديد نص الاستراتيجية
        if strategy_type == 'GROUP1_ONLY':
            strategy_text = "المجموعة الأولى فقط"
        elif strategy_type == 'DUAL_GROUP':
            strategy_text = "تأكيد مزدوج (مجموعتين)"
        elif strategy_type == 'TRIPLE_GROUP':
            strategy_text = "تأكيد ثلاثي (3 مجموعات)"
        elif strategy_type == 'GROUP1_GROUP3':
            strategy_text = "تأكيد مزدوج (المجموعة الأولى + الثالثة)"
        elif strategy_type == 'GROUP2_GROUP3':
            strategy_text = "تأكيد مزدوج (المجموعة الثانية + الثالثة)"
        elif strategy_type == 'GROUP3_ONLY':
            strategy_text = "المجموعة الثالثة فقط"
        else:
            strategy_text = strategy_type

        # عرض إشارات المجموعة الأولى
        group1_list = ''
        if group1_signals:
            numbered_group1 = [f"┃   {i+1}. {signal}" for i, signal in enumerate(group1_signals)]
            group1_list = "\n" + "\n".join(numbered_group1)
        else:
            group1_list = "\n┃   - لا توجد إشارات"

        # عرض إشارات المجموعة الثانية
        group2_list = ''
        if group2_signals:
            numbered_group2 = [f"┃   {i+1}. {signal}" for i, signal in enumerate(group2_signals)]
            group2_list = "\n" + "\n".join(numbered_group2)
        else:
            group2_list = "\n┃   - لا توجد إشارات"

        # عرض إشارات المجموعة الثالثة
        group3_list = ''
        if group3_signals:
            numbered_group3 = [f"┃   {i+1}. {signal}" for i, signal in enumerate(group3_signals)]
            group3_list = "\n" + "\n".join(numbered_group3)
        else:
            group3_list = "\n┃   - لا توجد إشارات"

        # تحديد أي مجموعات سيتم عرضها بناءً على نوع الاستراتيجية
        signals_display = ""
        if strategy_type == 'GROUP1_ONLY':
            signals_display = f"┃ 🔔 إشارات المجموعة الأولى ({len(group1_signals)} إشارات):{group1_list}"
        elif strategy_type == 'DUAL_GROUP':
            signals_display = f"┃ 🔔 إشارات المجموعة الأولى ({len(group1_signals)} إشارات):{group1_list}\n"
            signals_display += f"┃ 🔔 إشارات المجموعة الثانية ({len(group2_signals)} إشارات):{group2_list}"
        elif strategy_type == 'GROUP1_GROUP3':
            signals_display = f"┃ 🔔 إشارات المجموعة الأولى ({len(group1_signals)} إشارات):{group1_list}\n"
            signals_display += f"┃ 🔷 إشارات المجموعة الثالثة ({len(group3_signals)} إشارات):{group3_list}"
        elif strategy_type == 'GROUP2_GROUP3':
            signals_display = f"┃ 🔔 إشارات المجموعة الثانية ({len(group2_signals)} إشارات):{group2_list}\n"
            signals_display += f"┃ 🔷 إشارات المجموعة الثالثة ({len(group3_signals)} إشارات):{group3_list}"
        elif strategy_type == 'GROUP3_ONLY':
            signals_display = f"┃ 🔷 إشارات المجموعة الثالثة ({len(group3_signals)} إشارات):{group3_list}"
        else:
            signals_display = f"┃ 🔔 الإشارات المؤكدة:{group1_list}"

        return (
            "✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 🎯 نوع الصفقة: {'🟢 شراء' if direction=='buy' else '🔴 بيع'}\n"
            f"┃ 📊 اتجاه الرمز: {trend_icon}\n"
            f"┃ 🎯 محاذاة الاتجاه: {align_text}\n"
            f"┃ 🎯 الاستراتيجية: {strategy_text}\n"
            f"┃ 📋 الإشارة الرئيسية: {signal_type}\n"
            f"{signals_display}\n"
            f"┃ 📊 صفقات {symbol}: {active_for_symbol}/{config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{config['MAX_OPEN_TRADES']}\n"
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