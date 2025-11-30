#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter

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

class MessageFormatter:
    """🎯 فئة متخصصة في تنسيق رسائل النظام - مع دعم عرض إشارات الاتجاه والتوقيت السعودي"""

    @staticmethod
    def format_detailed_entry_message(symbol, signal_type, direction, current_trend, strategy_type, 
                                    group1_signals, group2_signals, group3_signals, 
                                    group4_signals, group5_signals,
                                    active_for_symbol, total_active, config, mode_key="TRADING_MODE"):
        """🎯 تنسيق رسالة دخول مفصلة مع عرض جميع الإشارات بالتوقيت السعودي"""
        timestamp = saudi_time.format_time()

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
        safe_group4 = group4_signals or []
        safe_group5 = group5_signals or []

        # 🆕 الإصلاح: عرض جميع الإشارات المستخدمة (حتى المكررة)
        signals_display = MessageFormatter._display_all_signals_used(
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
            f"🕐 {timestamp} 🇸🇦"
        )

    @staticmethod
    def _display_all_signals_used(strategy_type, group1_signals, group2_signals, group3_signals, group4_signals, group5_signals):
        """🎯 دالة معدلة: عرض جميع الإشارات المستخدمة (حتى المكررة)"""
        
        # تحديد المجموعات المطلوبة بناءً على الاستراتيجية
        required_groups = strategy_type.split('_') if strategy_type else []
        
        # 🎯 عرض جميع الإشارات دون إزالة التكرار
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
                total_signals = len(signals)
                
                # 🎯 الإصلاح: عرض جميع الإشارات حتى المكررة
                numbered_signals = [f"┃   {i+1}. {signal}" for i, signal in enumerate(signals)]
                display += f"┃ {group_info['color']} إشارات المجموعة {group_info['name']} ({total_signals} إشارة):\n" + "\n".join(numbered_signals)
        
        # إذا لم توجد أي إشارات بعد التصفية
        if not display:
            display = "┃   ⚠️ لا توجد إشارات مسجلة"
        
        return display

    @staticmethod
    def format_trend_message(signal_data, new_trend, old_trend, trend_signals=None):
        """📊 تنسيق رسالة تغيير الاتجاه الأساسية مع عرض جميع الإشارات بالتوقيت السعودي"""
        symbol = signal_data['symbol']
        signal = signal_data['signal_type']
        timestamp = saudi_time.format_time()

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

        # 🎯 الإضافة الجديدة: عرض جميع الإشارات المستخدمة في تغيير الاتجاه
        signals_display = ""
        if trend_signals and len(trend_signals) > 0:
            signals_display = "\n┃ 📋 الإشارات المستخدمة:\n"
            for i, trend_signal in enumerate(trend_signals, 1):
                signal_direction = "🟢 صاعد" if trend_signal['direction'] == 'bullish' else "🔴 هابط"
                signals_display += f"┃   {i}. {trend_signal['signal_type']} ({signal_direction})\n"

        return f"""☰☰☰ 📊 تغيير الاتجاه ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة الحالية: {signal}
┃ 🔄 الحالة: {status_text}{signals_display}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp} 🇸🇦"""

    @staticmethod
    def format_exit_message(symbol, signal_type, closed_trades, remaining_trades, total_active, config):
        """🎯 تنسيق رسالة الخروج مع معلومات الصفقات المغلقة بالتوقيت السعودي"""
        timestamp = saudi_time.format_time()

        return (
            "════ 🚪 إشـــــــارة خــــــروج ════\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 📝 السبب: إشارة خروج: {signal_type}\n"
            f"┃ 🔴 الصفقات المغلقة: {closed_trades}\n"
            f"┃ 📊 صفقات {symbol} المتبقية: {remaining_trades}/{config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp} 🇸🇦"
        )