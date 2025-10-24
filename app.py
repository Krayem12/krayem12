#!/usr/bin/env python3
"""
نظام معالجة إشارات التداول - نسخة مدمجة بالسيرفر المحلي والخارجي
يدعم المنفذ 10000 ويشمل جميع الميزات بنمط الرسائل الجديد
"""

import os
import sys
import json
import logging
import uuid
import re
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from decouple import config

# إضافة مسار المشروع إلى نظام المسارات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# تحميل متغيرات البيئة
load_dotenv()

# 🔧 إعدادات التطبيق
class Config:
    """فئة إعدادات التطبيق المدمجة"""
    
    def __init__(self):
        # الإعدادات الأساسية
        self.APP_NAME = config('APP_NAME', default='TradingSignalProcessor')
        self.APP_VERSION = config('APP_VERSION', default='4.0.0')
        self.DEBUG = config('DEBUG', default=True, cast=bool)
        self.LOG_LEVEL = config('LOG_LEVEL', default='INFO')
        self.LOG_FILE = config('LOG_FILE', default='app.log')
        
        # إعدادات Telegram
        self.TELEGRAM_ENABLED = config('TELEGRAM_ENABLED', default=True, cast=bool)
        self.TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='your_bot_token_here')
        self.TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID', default='your_chat_id_here')
        
        # إعدادات الخادم الخارجي
        self.EXTERNAL_SERVER_ENABLED = config('EXTERNAL_SERVER_ENABLED', default=False, cast=bool)
        self.EXTERNAL_SERVER_URL = config('EXTERNAL_SERVER_URL', default='https://api.example.com/webhook/trading')
        self.EXTERNAL_SERVER_TOKEN = config('EXTERNAL_SERVER_TOKEN', default='your_external_server_token_here')
        
        # إعدادات التأكيد وإدارة الصفقات
        self.REQUIRED_CONFIRMATIONS = config('REQUIRED_CONFIRMATIONS', default=2, cast=int)
        self.CONFIRMATION_TIMEOUT = config('CONFIRMATION_TIMEOUT', default=1200, cast=int)
        self.CONFIRMATION_WINDOW = config('CONFIRMATION_WINDOW', default=1200, cast=int)
        self.MAX_OPEN_TRADES = config('MAX_OPEN_TRADES', default=5, cast=int)
        self.RESPECT_TREND_FOR_REGULAR_TRADES = config('RESPECT_TREND_FOR_REGULAR_TRADES', default=True, cast=bool)
        self.RESET_TRADES_ON_TREND_CHANGE = config('RESET_TRADES_ON_TREND_CHANGE', default=False, cast=bool)
        
        # قوائم الإشارات - جميعها تقرأ من ملف .env
        self.TREND_SIGNALS = self._parse_signal_list(config('TREND_SIGNALS', default='bullish_catcher,bearish_catcher'))
        self.TREND_CONFIRM_SIGNALS = self._parse_signal_list(config('TREND_CONFIRM_SIGNALS', default='bullish_tracer,bearish_tracer,bullish_catcher_and_tracer,bearish_catcher_and_tracer'))
        self.ENTRY_SIGNALS_BULLISH = self._parse_signal_list(config('ENTRY_SIGNALS_BULLISH', default='bullish_sbos_buy,bullish_schoch_buy,bullish_grab_buy,discount_exit_call,bullish_confirmation+,bullish_catcher_cross_over_tracer,bullish_moneyflow_co_50,bullish_hyperwave_co_50,bullish_switch_tracer,Strong bullish confluence,Bullish New Imbalance,Bullish Turn +,Bullish overflow,Bullish reversal,Weak bullish confluence'))
        self.ENTRY_SIGNALS_BEARISH = self._parse_signal_list(config('ENTRY_SIGNALS_BEARISH', default='bearish_moneyflow_cu_50,bearish_hyperwave_cu_50,bearish_switch_tracer,Within Bearish Imbalance,Bearish New Imbalance,Hyper Wave oscillator downward signal'))
        self.EXIT_SIGNALS = self._parse_signal_list(config('EXIT_SIGNALS', default='exit_buy,exit_sell,Bullish Imbalance Exited,Bearish Imbalance Exited,Bearish Imbalance Mitigated,Bearish Imbalance Exited Block'))
        self.GENERAL_SIGNALS = self._parse_signal_list(config('GENERAL_SIGNALS', default='Within Bullish Imbalance'))
        self.ALL_SIGNALS = self._get_all_signals()
    
    def _parse_signal_list(self, signal_str: str) -> list:
        """معالجة قائمة الإشارات وتحويلها إلى list"""
        if not signal_str or signal_str.strip() == '':
            return []
        signals = [s.strip() for s in signal_str.split(',') if s.strip()]
        return signals
    
    def _get_all_signals(self) -> list:
        """جمع جميع الإشارات في قائمة واحدة"""
        all_signals = []
        all_signals.extend(self.TREND_SIGNALS)
        all_signals.extend(self.TREND_CONFIRM_SIGNALS)
        all_signals.extend(self.ENTRY_SIGNALS_BULLISH)
        all_signals.extend(self.ENTRY_SIGNALS_BEARISH)
        all_signals.extend(self.EXIT_SIGNALS)
        all_signals.extend(self.GENERAL_SIGNALS)
        return all_signals

# ✉️ مُنسق الرسائل المدمج - النماذج الجديدة
class MessageFormatter:
    """مُنسق الرسائل المدمج بالنماذج الجديدة"""
    
    @staticmethod
    def format_trend_signal(signal_data: Dict) -> str:
        """تنسيق رسالة الاتجاه العام - النموذج الأصلي المحفوظ"""
        ticker = signal_data['ticker']
        signal_type = signal_data['signal_type']
        
        # تحديد الاتجاه بناءً على نوع الإشارة
        if 'bullish' in signal_type.lower():
            trend_icon = "🟢📈"
            trend_text = "شراء (اتجاه صاعد)"
        elif 'bearish' in signal_type.lower():
            trend_icon = "🔴📉"
            trend_text = "بيع (اتجاه هابط)"
        else:
            trend_icon = "⚪"
            trend_text = "محايد"
        
        message = f"""
☰☰☰ 📊 الاتجاه العام ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {ticker}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal_type}
┃ 🔄 الحالة: الاتجاه العام محدث
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return message.strip()
    
    @staticmethod
    def format_trade_entry(trade_info: Dict, confirmation_data: Dict = None) -> str:
        """تنسيق رسالة دخول الصفقة بالنموذج الجديد"""
        ticker = trade_info['ticker']
        direction = trade_info['direction']
        
        if direction == 'CALL':
            direction_icon, direction_text = "🟢", "شراء"
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        else:
            direction_icon, direction_text = "🔴", "بيع" 
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        
        # معالجة بيانات التأكيد
        if confirmation_data:
            confirm_count = confirmation_data.get('total_signals', 1)
            secondary_signals = confirmation_data.get('secondary_signals', [])
            secondary_count = len(secondary_signals)
            
            secondary_listing = ""
            for i, signal in enumerate(secondary_signals[:3], 1):
                signal_name = signal.get('signal_type', 'unknown')
                # تنظيف اسم الإشارة من الرموز الخاصة
                clean_signal_name = signal_name.replace('+', '').replace('-', '')
                secondary_listing += f"┃   {i}. {clean_signal_name}\n"
            
            if secondary_count > 3:
                secondary_listing += f"┃   ... و{secondary_count - 3} إشارات أخرى\n"
        else:
            confirm_count = 1
            secondary_count = 0
            secondary_listing = "┃    - لا توجد إشارات مساعدة\n"
        
        align_icon, align_text = "🟢", "مطابق للاتجاه العام"
        open_trades = trade_info.get('open_trades', 1)
        max_open_trades = trade_info.get('max_open_trades', 5)
        
        # تنظيف اسم الإشارة الرئيسية من الرموز الخاصة
        main_signal_clean = trade_info['signal_type'].replace('+', '').replace('-', '')
        
        message = f"""
✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {ticker}
┃ 🎯 نوع الصفقة: {direction_icon} {direction_text}
┃ 📊 الاتجاه الحالي: {trend_icon} {trend_text}
┃ 🎯 محاذاة الاتجاه: {align_icon} {align_text}
┃ 📋 الإشارة الرئيسية: {main_signal_clean} (تم التأكيد بـ {confirm_count} إشارات)
┃ 🔔 الإشارات المساعدة: {secondary_count} إشارة
{secondary_listing}┃ 📊 الصفقات المفتوحة: {open_trades} من {max_open_trades}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
        """
        
        return message.strip()
    
    @staticmethod
    def format_trend_confirmation(signal_data: Dict, current_trend: str) -> str:
        """تنسيق رسالة تأكيد الاتجاه بالنموذج الجديد"""
        ticker = signal_data['ticker']
        signal_type = signal_data['signal_type']
        
        # تحديد الاتجاه المؤكد
        if 'bullish' in signal_type.lower() or current_trend == 'BULLISH':
            trend_icon = "🟢📈"
            trend_text = "شراء (اتجاه صاعد)"
        elif 'bearish' in signal_type.lower() or current_trend == 'BEARISH':
            trend_icon = "🔴📉"
            trend_text = "بيع (اتجاه هابط)"
        else:
            trend_icon = "⚪"
            trend_text = "محايد"
        
        # تنظيف اسم الإشارة من الرموز الخاصة
        clean_signal_name = signal_type.replace('+', '').replace('-', '')
        
        message = f"""
✅ 📊 تأكيـــــد الاتجــــاه 📊 ✅
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {ticker}
┃ 📈 الاتجاه المؤكد: {trend_icon} {trend_text}
┃ 📋 الإشارة: {clean_signal_name}
┃ ✅ الحالة: تأكيد مطابقة الاتجاه العام
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
        """
        
        return message.strip()
    
    @staticmethod
    def format_trade_exit(trade_info: Dict) -> str:
        """تنسيق رسالة خروج الصفقة بالنموذج الجديد"""
        ticker = trade_info['ticker']
        direction = trade_info['direction']
        exit_signal = trade_info['exit_signal']
        
        if direction == 'CALL':
            direction_icon, direction_text = "🟢", "شراء (CALL)"
        else:
            direction_icon, direction_text = "🔴", "بيع (PUT)"
        
        open_trades = trade_info.get('open_trades', 0)
        max_open_trades = trade_info.get('max_open_trades', 5)
        
        # تنظيف اسم إشارة الخروج
        clean_exit_signal = exit_signal.replace('_', ' ')
        
        message = f"""
════ 🚪 إشـــــــارة خــــــروج ════
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {ticker}
┃ 📝 السبب: إشارة خروج: {clean_exit_signal}
┃ 🎯 نوع الصفقة المغلقة: {direction_icon} {direction_text}
┃ 📊 الصفقات المفتوحة: {open_trades}/{max_open_trades}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
        """
        
        return message.strip()
    
    @staticmethod
    def format_general_signal(signal_data: Dict) -> str:
        """تنسيق رسالة الإشارة العامة"""
        # تنظيف اسم الإشارة
        clean_signal = signal_data['signal_type'].replace('+', '').replace('-', '')
        
        return f"""
☰☰☰ 🔔 إشارة جديدة ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {signal_data['ticker']}
┃ 📈 نوع الإشارة: {signal_data['signal_category']}
┃ 📋 الإشارة: {clean_signal}
┃ 📍 الحالة: {signal_data['open_status']} / {signal_data['close_status']}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {signal_data['timestamp']}
        """.strip()

# 📨 نظام الإشعارات المدمج
class NotificationManager:
    """مدير الإشعارات المدمج لـ Telegram والخادم الخارجي"""
    
    def __init__(self, config):
        self.config = config
        self.telegram_enabled = config.TELEGRAM_ENABLED
        self.external_enabled = config.EXTERNAL_SERVER_ENABLED
        
    def send_message(self, message: str, signal_data: Dict = None) -> bool:
        """إرسال رسالة عبر جميع القنوات الممكنة"""
        success = True
        
        # إرسال إلى Telegram
        if self.telegram_enabled:
            if not self._send_telegram(message):
                success = False
        
        # إرسال إلى الخادم الخارجي
        if self.external_enabled and signal_data:
            if not self._send_external(signal_data):
                success = False
                
        return success
    
    def _send_telegram(self, message: str) -> bool:
        """إرسال إلى Telegram"""
        try:
            if self.config.TELEGRAM_BOT_TOKEN == 'your_bot_token_here':
                print("⚠️  إعدادات Telegram غير مكتملة - تم محاكاة الإرسال")
                print(f"📲 محاكاة إرسال إلى Telegram:\n{message}")
                return True
            
            url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': self.config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            success = response.status_code == 200
            
            if success:
                print("✅ تم إرسال الرسالة إلى Telegram بنجاح")
            else:
                print(f"❌ فشل إرسال Telegram: {response.status_code}")
            
            return success
            
        except Exception as e:
            print(f"❌ خطأ في إرسال رسالة Telegram: {e}")
            return False
    
    def _send_external(self, signal_data: Dict) -> bool:
        """إرسال إلى الخادم الخارجي"""
        try:
            if self.config.EXTERNAL_SERVER_URL == 'https://api.example.com/webhook/trading':
                print("⚠️  إعدادات الخادم الخارجي غير مكتملة - تم محاكاة الإرسال")
                print(f"🌐 محاكاة إرسال إلى API: {json.dumps(signal_data, indent=2, ensure_ascii=False)}")
                return True
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config.EXTERNAL_SERVER_TOKEN}',
                'X-API-Key': self.config.EXTERNAL_SERVER_TOKEN
            }
            
            response = requests.post(
                self.config.EXTERNAL_SERVER_URL,
                json=signal_data,
                headers=headers,
                timeout=10
            )
            
            success = response.status_code in [200, 201]
            
            if success:
                print("✅ تم إرسال البيانات إلى الخادم الخارجي بنجاح")
            else:
                print(f"❌ فشل إرسال إلى الخادم الخارجي: {response.status_code}")
            
            return success
            
        except Exception as e:
            print(f"❌ خطأ في إرسال البيانات إلى الخادم الخارجي: {e}")
            return False

# 🔍 مدير التأكيد المدمج
class ConfirmationManager:
    """مدير تأكيد الإشارات المدمج - يتطلب إشارتين مختلفتين من نفس النوع"""
    
    def __init__(self, config):
        self.config = config
        self.pending_signals = {}
        self.confirmed_signals = {}
        self.current_trend = None
        self.trend_signals = []
        self.last_trend_notification = None  # لتتبع آخر إشعار اتجاه تم إرساله
        
    def add_signal(self, signal_data: Dict) -> Dict:
        """إضافة إشارة جديدة"""
        signal_type = signal_data['signal_type']
        ticker = signal_data['ticker']
        
        category = self._classify_signal(signal_data)
        
        if category == 'TREND_SIGNALS':
            return self._handle_trend_signal(signal_data)
        elif category in ['ENTRY_SIGNALS_BULLISH', 'ENTRY_SIGNALS_BEARISH']:
            return self._handle_entry_signal(signal_data, category)
        elif category == 'TREND_CONFIRM_SIGNALS':
            return self._handle_confirmation_signal(signal_data)
        elif category == 'GENERAL_SIGNALS':
            return {'status': 'general_signal', 'message': 'إشارة عامة - للمراقبة فقط'}
        else:
            return {'status': 'ignored', 'reason': 'unknown_signal_type'}
    
    def _classify_signal(self, signal_data: Dict) -> str:
        """تصنيف الإشارة"""
        signal_type = signal_data['signal_type']
        
        if signal_type in self.config.TREND_SIGNALS:
            return 'TREND_SIGNALS'
        elif signal_type in self.config.TREND_CONFIRM_SIGNALS:
            return 'TREND_CONFIRM_SIGNALS'
        elif signal_type in self.config.ENTRY_SIGNALS_BULLISH:
            return 'ENTRY_SIGNALS_BULLISH'
        elif signal_type in self.config.ENTRY_SIGNALS_BEARISH:
            return 'ENTRY_SIGNALS_BEARISH'
        elif signal_type in self.config.EXIT_SIGNALS:
            return 'EXIT_SIGNALS'
        elif signal_type in self.config.GENERAL_SIGNALS:
            return 'GENERAL_SIGNALS'
        else:
            # محاولة مطابقة جزئية
            for trend_signal in self.config.TREND_SIGNALS:
                if trend_signal.lower() in signal_type.lower():
                    return 'TREND_SIGNALS'
            
            for bull_signal in self.config.ENTRY_SIGNALS_BULLISH:
                if bull_signal.lower() in signal_type.lower():
                    return 'ENTRY_SIGNALS_BULLISH'
            
            for bear_signal in self.config.ENTRY_SIGNALS_BEARISH:
                if bear_signal.lower() in signal_type.lower():
                    return 'ENTRY_SIGNALS_BEARISH'
            
            for exit_signal in self.config.EXIT_SIGNALS:
                if exit_signal.lower() in signal_type.lower():
                    return 'EXIT_SIGNALS'
            
            return 'UNKNOWN'
    
    def _handle_trend_signal(self, signal_data: Dict) -> Dict:
        """معالجة إشارات الاتجاه"""
        signal_type = signal_data['signal_type']
        new_trend = None
        
        if 'bullish' in signal_type.lower():
            new_trend = 'BULLISH'
        elif 'bearish' in signal_type.lower():
            new_trend = 'BEARISH'
        
        # التحقق إذا كان الاتجاه قد تغير
        trend_changed = self.current_trend != new_trend
        self.current_trend = new_trend
        
        self.trend_signals.append({
            **signal_data,
            'timestamp': datetime.now()
        })
        
        self._clean_old_trend_signals()
        
        return {
            'status': 'trend_updated', 
            'current_trend': self.current_trend,
            'trend_changed': trend_changed
        }
    
    def _handle_entry_signal(self, signal_data: Dict, category: str) -> Dict:
        """معالجة إشارات الدخول - تتطلب إشارتين مختلفتين"""
        current_time = datetime.now()
        ticker = signal_data['ticker']
        signal_type = signal_data['signal_type']
        
        self._clean_expired_signals()
        
        # مفتاح فريد لكل زوج من الرمز والنوع
        signal_key = f"{ticker}_{category}"
        
        if signal_key not in self.pending_signals:
            self.pending_signals[signal_key] = {
                'ticker': ticker,
                'category': category,
                'unique_signals': set(),  # استخدام set لتخزين الإشارات الفريدة
                'signals_data': [],       # تخزين بيانات الإشارات
                'created_at': current_time,
                'updated_at': current_time
            }
        
        # إضافة الإشارة إذا كانت مختلفة
        if signal_type not in self.pending_signals[signal_key]['unique_signals']:
            self.pending_signals[signal_key]['unique_signals'].add(signal_type)
            self.pending_signals[signal_key]['signals_data'].append(signal_data)
            self.pending_signals[signal_key]['updated_at'] = current_time
            print(f"📥 إضافة إشارة فريدة: {signal_type} للمفتاح {signal_key}")
        else:
            print(f"⏭️  تجاهل إشارة مكررة: {signal_type} للمفتاح {signal_key}")
        
        return self._check_confirmation(signal_key)
    
    def _handle_confirmation_signal(self, signal_data: Dict) -> Dict:
        """معالجة إشارات التأكيد"""
        ticker = signal_data['ticker']
        confirmed_any = False
        
        for signal_key in list(self.pending_signals.keys()):
            if ticker in signal_key:
                # إضافة إشارات التأكيد كإشارات ثانوية
                signal_type = signal_data['signal_type']
                if signal_type not in self.pending_signals[signal_key]['unique_signals']:
                    self.pending_signals[signal_key]['unique_signals'].add(signal_type)
                    self.pending_signals[signal_key]['signals_data'].append(signal_data)
                    self.pending_signals[signal_key]['updated_at'] = datetime.now()
                    
                    result = self._check_confirmation(signal_key)
                    if result['status'] == 'confirmed':
                        confirmed_any = True
        
        return {'status': 'confirmation_added', 'confirmed': confirmed_any}
    
    def _check_confirmation(self, signal_key: str) -> Dict:
        """التحقق من اكتمال التأكيدات - يتطلب إشارتين مختلفتين على الأقل"""
        signal_data = self.pending_signals[signal_key]
        unique_signals_count = len(signal_data['unique_signals'])
        
        print(f"🔍 التحقق من التأكيد للمفتاح {signal_key}: {unique_signals_count} إشارة فريدة")
        
        if unique_signals_count >= self.config.REQUIRED_CONFIRMATIONS:
            # تأكيد الصفقة
            confirmed_data = {
                'main_signal': signal_data['signals_data'][0],  # أول إشارة
                'secondary_signals': signal_data['signals_data'][1:],  # باقي الإشارات
                'unique_signals': list(signal_data['unique_signals']),
                'total_signals': unique_signals_count
            }
            
            self.confirmed_signals[signal_key] = confirmed_data
            del self.pending_signals[signal_key]
            
            print(f"✅ تأكيد صفقة بـ {unique_signals_count} إشارات فريدة: {confirmed_data['unique_signals']}")
            
            return {
                'status': 'confirmed',
                'unique_signals': confirmed_data['unique_signals'],
                'total_signals': unique_signals_count,
                'main_signal': confirmed_data['main_signal'],
                'secondary_signals': confirmed_data['secondary_signals']
            }
        
        return {
            'status': 'pending', 
            'current_count': unique_signals_count, 
            'required': self.config.REQUIRED_CONFIRMATIONS,
            'unique_signals': list(signal_data['unique_signals'])
        }
    
    def _clean_expired_signals(self):
        """تنظيف الإشارات المنتهية"""
        current_time = datetime.now()
        expired_keys = []
        
        for signal_key, signal_data in self.pending_signals.items():
            time_diff = (current_time - signal_data['created_at']).total_seconds()
            if time_diff > self.config.CONFIRMATION_TIMEOUT:
                expired_keys.append(signal_key)
                print(f"🗑️  تنظيف إشارات منتهية: {signal_key}")
        
        for key in expired_keys:
            del self.pending_signals[key]
    
    def _clean_old_trend_signals(self):
        """تنظيف إشارات الاتجاه القديمة"""
        current_time = datetime.now()
        self.trend_signals = [
            signal for signal in self.trend_signals 
            if (current_time - signal['timestamp']).total_seconds() <= self.config.CONFIRMATION_WINDOW
        ]

# 💼 مدير الصفقات المدمج
class TradeManager:
    """مدير الصفقات المدمج"""
    
    def __init__(self, config, notification_manager, message_formatter):
        self.config = config
        self.notification_manager = notification_manager
        self.message_formatter = message_formatter
        self.confirmation_manager = ConfirmationManager(config)
        self.active_trades = {}
        self.last_trend_notification = None  # لتتبع آخر إشعار اتجاه تم إرساله
    
    def process_signal(self, signal_data: Dict) -> Dict:
        """معالجة الإشارة"""
        try:
            confirmation_result = self.confirmation_manager.add_signal(signal_data)
            
            if confirmation_result['status'] == 'confirmed':
                return self._open_confirmed_trade(signal_data, confirmation_result)
            elif confirmation_result['status'] == 'trend_updated':
                return self._handle_trend_change(confirmation_result, signal_data)
            elif confirmation_result['status'] == 'general_signal':
                return {'status': 'general', 'message': 'إشارة عامة - للمراقبة فقط'}
            else:
                unique_signals = confirmation_result.get('unique_signals', [])
                if unique_signals:
                    return {
                        'status': 'pending',
                        'message': f"في انتظار تأكيدات إضافية ({confirmation_result.get('current_count', 1)}/{confirmation_result.get('required', 2)}) - الإشارات: {', '.join(unique_signals)}",
                        'signal': signal_data
                    }
                else:
                    return {
                        'status': 'pending',
                        'message': f"في انتظار تأكيدات إضافية ({confirmation_result.get('current_count', 1)}/{confirmation_result.get('required', 2)})",
                        'signal': signal_data
                    }
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def process_confirmation_signal(self, signal_data: Dict) -> Dict:
        """معالجة إشارات التأكيد وإرسال رسالة تأكيد الاتجاه"""
        try:
            # إضافة الإشارة إلى مدير التأكيد
            confirmation_result = self.confirmation_manager.add_signal(signal_data)
            
            # إرسال رسالة تأكيد الاتجاه
            if confirmation_result['status'] == 'confirmation_added':
                current_trend = self.confirmation_manager.current_trend
                message = self.message_formatter.format_trend_confirmation(signal_data, current_trend)
                self.notification_manager.send_message(message, signal_data)
            
            return confirmation_result
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _open_confirmed_trade(self, signal_data: Dict, confirmation_result: Dict) -> Dict:
        """فتح صفقة مؤكدة"""
        try:
            if len(self.active_trades) >= self.config.MAX_OPEN_TRADES:
                return {
                    'status': 'rejected',
                    'message': f"تم الوصول للحد الأقصى للصفقات المفتوحة ({self.config.MAX_OPEN_TRADES})",
                    'signal': signal_data
                }
            
            direction = self._get_trade_direction(signal_data['signal_type'])
            if direction == 'UNKNOWN':
                return {'status': 'rejected', 'message': 'اتجاه غير معروف'}
            
            trade_id = str(uuid.uuid4())[:8]
            trade_info = {
                'trade_id': trade_id,
                'ticker': signal_data['ticker'],
                'direction': direction,
                'signal_type': signal_data['signal_type'],
                'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entry_price': 0.0,
                'status': 'OPEN',
                'source': 'TradingView',
                'open_trades': len(self.active_trades) + 1,
                'max_open_trades': self.config.MAX_OPEN_TRADES,
                'confirmation_data': confirmation_result,
                'unique_confirmation_signals': confirmation_result.get('unique_signals', [])
            }
            
            self.active_trades[trade_id] = trade_info
            
            # إرسال الإشعار
            message = self.message_formatter.format_trade_entry(trade_info, confirmation_result)
            self.notification_manager.send_message(message, trade_info)
            
            unique_signals = confirmation_result.get('unique_signals', [])
            print(f"📈 فتح صفقة {direction} للرمز {signal_data['ticker']} (#{trade_id}) بـ {len(unique_signals)} إشارات فريدة: {unique_signals}")
            
            return {
                'status': 'opened',
                'trade_id': trade_id,
                'trade_info': trade_info,
                'message': 'تم فتح الصفقة بنجاح'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _handle_trend_change(self, trend_result: Dict, signal_data: Dict) -> Dict:
        """معالجة تغيير الاتجاه مع التحكم في الإشعارات"""
        try:
            current_trend = trend_result['current_trend']
            trend_changed = trend_result.get('trend_changed', False)
            
            # إرسال إشعار الاتجاه فقط إذا تغير الاتجاه أو لم يكن هناك إشعار سابق
            if trend_changed or self.last_trend_notification != current_trend:
                message = self.message_formatter.format_trend_signal(signal_data)
                self.notification_manager.send_message(message, signal_data)
                self.last_trend_notification = current_trend
                print(f"📊 إرسال إشعار الاتجاه: {current_trend}")
            else:
                print(f"⏭️  تجاهل إرسال إشعار الاتجاه لنفس الاتجاه: {current_trend}")
            
            if self.config.RESET_TRADES_ON_TREND_CHANGE and self.active_trades and trend_changed:
                closed_trades = []
                for trade_id in list(self.active_trades.keys()):
                    closed_trade = self._close_trade_by_id(trade_id, 'trend_change')
                    if closed_trade:
                        closed_trades.append(closed_trade)
                
                return {
                    'status': 'trend_changed',
                    'message': f"تم تغيير الاتجاه إلى {current_trend} وإغلاق {len(closed_trades)} صفقة",
                    'closed_trades': closed_trades
                }
            else:
                return {
                    'status': 'trend_updated',
                    'message': f"تم تحديث الاتجاه إلى {current_trend}",
                    'current_trend': current_trend,
                    'notification_sent': trend_changed or self.last_trend_notification != current_trend
                }
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def close_trade(self, signal_data: Dict) -> Dict:
        """إغلاق الصفقة"""
        try:
            trade_to_close = self._find_active_trade(signal_data['ticker'])
            if not trade_to_close:
                return {'status': 'not_found', 'message': 'لا توجد صفقة نشطة'}
            
            trade_id = trade_to_close['trade_id']
            closed_trade = self._close_trade_by_id(trade_id, signal_data['signal_type'])
            
            if closed_trade:
                return {
                    'status': 'closed',
                    'trade_id': trade_id,
                    'message': 'تم إغلاق الصفقة بنجاح'
                }
            else:
                return {'status': 'error', 'message': 'فشل في إغلاق الصفقة'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _close_trade_by_id(self, trade_id: str, reason: str) -> Optional[Dict]:
        """إغلاق صفقة بواسطة المعرف"""
        try:
            trade_to_close = self.active_trades.get(trade_id)
            if not trade_to_close:
                return None
            
            trade_to_close.update({
                'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'exit_price': 0.0,
                'status': 'CLOSED',
                'exit_signal': reason
            })
            
            # إرسال إشعار الإغلاق
            message = self.message_formatter.format_trade_exit(trade_to_close)
            self.notification_manager.send_message(message, trade_to_close)
            
            self.active_trades.pop(trade_id, None)
            print(f"📉 إغلاق صفقة #{trade_id} بسبب: {reason}")
            
            return trade_to_close
            
        except Exception as e:
            print(f"❌ خطأ في إغلاق الصفقة: {e}")
            return None
    
    def _get_trade_direction(self, signal_type: str) -> str:
        """تحديد اتجاه الصفقة"""
        if signal_type in self.config.ENTRY_SIGNALS_BULLISH:
            return 'CALL'
        elif signal_type in self.config.ENTRY_SIGNALS_BEARISH:
            return 'PUT'
        else:
            # محاولة تحديد الاتجاه بناءً على اسم الإشارة
            if 'bullish' in signal_type.lower() or 'buy' in signal_type.lower():
                return 'CALL'
            elif 'bearish' in signal_type.lower() or 'sell' in signal_type.lower():
                return 'PUT'
            else:
                return 'UNKNOWN'
    
    def _find_active_trade(self, ticker: str) -> Optional[Dict]:
        """البحث عن صفقة نشطة"""
        for trade in self.active_trades.values():
            if trade['ticker'] == ticker and trade['status'] == 'OPEN':
                return trade
        return None
    
    def get_active_trades_count(self) -> int:
        """الحصول على عدد الصفقات النشطة"""
        return len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
    
    def get_confirmation_stats(self) -> Dict:
        """الحصول على إحصائيات التأكيد"""
        return {
            'pending_signals': len(self.confirmation_manager.pending_signals),
            'confirmed_signals': len(self.confirmation_manager.confirmed_signals),
            'active_trades': self.get_active_trades_count(),
            'max_trades': self.config.MAX_OPEN_TRADES,
            'current_trend': self.confirmation_manager.current_trend,
            'last_trend_notification': self.last_trend_notification
        }

# 🎯 معالج الإشارات المدمج
class SignalHandler:
    """معالج الإشارات المدمج"""
    
    def __init__(self):
        self.config = Config()
        self.message_formatter = MessageFormatter()
        self.notification_manager = NotificationManager(self.config)
        self.trade_manager = TradeManager(self.config, self.notification_manager, self.message_formatter)
        
        # عرض الإشارات المحملة من .env
        self._display_loaded_signals()
        
        print(f"🔧 نظام التأكيد مفعل - مطلوب {self.config.REQUIRED_CONFIRMATIONS} إشارات مختلفة للتأكيد")
        print(f"📊 الحد الأقصى للصفقات: {self.config.MAX_OPEN_TRADES}")
        print(f"📨 نماذج الرسائل المدعومة:")
        print(f"   ✦✦✦ دخول الصفقة")
        print(f"   ✅ 📊 تأكيد الاتجاه")  
        print(f"   ════ إشارة الخروج")
        print(f"   ☰☰☰ الاتجاه العام (مرة واحدة فقط)")
        print(f"   🔔 إشارة عامة")
    
    def _display_loaded_signals(self):
        """عرض الإشارات المحملة من .env"""
        print("📋 الإشارات المحملة من ملف .env:")
        print(f"   📊 إشارات الاتجاه: {len(self.config.TREND_SIGNALS)} إشارة")
        print(f"   ✅ إشارات تأكيد الاتجاه: {len(self.config.TREND_CONFIRM_SIGNALS)} إشارة")
        print(f"   🟢 إشارات الدخول الشرائية: {len(self.config.ENTRY_SIGNALS_BULLISH)} إشارة")
        print(f"   🔴 إشارات الدخول البيعية: {len(self.config.ENTRY_SIGNALS_BEARISH)} إشارة")
        print(f"   🚪 إشارات الخروج: {len(self.config.EXIT_SIGNALS)} إشارة")
        print(f"   🔔 إشارات عامة: {len(self.config.GENERAL_SIGNALS)} إشارة")
        print(f"   📈 إجمالي الإشارات: {len(self.config.ALL_SIGNALS)} إشارة")
        
        if len(self.config.ALL_SIGNALS) == 0:
            print("⚠️  تحذير: لم يتم تحميل أي إشارات من ملف .env!")
    
    def parse_signal(self, raw_signal: str) -> Optional[Dict]:
        """تحليل الإشارة - الصيغة الجديدة فقط"""
        try:
            # تنظيف الإشارة من الفراغات الزائدة
            cleaned_signal = ' '.join(raw_signal.split())
            
            # الصيغة الجديدة: "Ticker : ... Signal : ... Open : ... Close : ..."
            pattern = r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+?)\s+Open\s*:\s*(.+?)\s+Close\s*:\s*(.+)'
            match = re.match(pattern, cleaned_signal)
            
            if not match:
                # إذا كانت الإشارة بالصيغة القديمة، حاول تحويلها
                if '|' in cleaned_signal:
                    parts = [part.strip() for part in cleaned_signal.split('|')]
                    if len(parts) >= 2:
                        ticker = parts[0]
                        signal_type = parts[1]
                        open_price = parts[2] if len(parts) > 2 else "0"
                        close_price = parts[3] if len(parts) > 3 else "0"
                        print(f"⚠️  تم تحويل الإشارة من الصيغة القديمة: {signal_type}")
                    else:
                        raise ValueError(f"صيغة الإشارة غير صالحة. التنسيق المتوقع: Ticker : SYMBOL Signal : SIGNAL Open : PRICE Close : PRICE")
                else:
                    # إذا كانت مجرد اسم إشارة، استخدم قيم افتراضية
                    signal_type = cleaned_signal
                    ticker = "BTCUSDT"
                    open_price = "0"
                    close_price = "0"
                    print(f"⚠️  تم معالجة الإشارة المختصرة: {signal_type}")
            else:
                ticker, signal_type, open_price, close_price = match.groups()
            
            return {
                'ticker': ticker.strip(),
                'signal_type': signal_type.strip(),
                'open_status': "OPEN",
                'close_status': "CLOSE",
                'open_price': open_price.strip(),
                'close_price': close_price.strip(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'TradingView'
            }
        except Exception as e:
            print(f"❌ خطأ في تحليل الإشارة: {e}")
            return None
    
    def classify_signal(self, signal_data: Dict) -> Tuple[str, str]:
        """تصنيف الإشارة مع دعم المطابقة الجزئية"""
        signal_type = signal_data['signal_type']
        
        signal_categories = {
            'TREND_SIGNALS': self.config.TREND_SIGNALS,
            'TREND_CONFIRM_SIGNALS': self.config.TREND_CONFIRM_SIGNALS,
            'ENTRY_SIGNALS_BULLISH': self.config.ENTRY_SIGNALS_BULLISH,
            'ENTRY_SIGNALS_BEARISH': self.config.ENTRY_SIGNALS_BEARISH,
            'EXIT_SIGNALS': self.config.EXIT_SIGNALS,
            'GENERAL_SIGNALS': self.config.GENERAL_SIGNALS
        }
        
        # البحث عن مطابقة تامة أولاً
        for category, signals in signal_categories.items():
            if signal_type in signals:
                return category, self._get_category_description(category)
        
        # إذا لم توجد مطابقة تامة، ابحث عن مطابقة جزئية
        for category, signals in signal_categories.items():
            for signal in signals:
                if signal.lower() in signal_type.lower() or signal_type.lower() in signal.lower():
                    print(f"🎯 تمت مطابقة جزئية: {signal_type} -> {signal}")
                    return category, self._get_category_description(category)
        
        return 'UNKNOWN', 'إشارة غير معروفة'
    
    def _get_category_description(self, category: str) -> str:
        """الحصول على وصف الفئة"""
        descriptions = {
            'TREND_SIGNALS': 'الاتجاه العام للسوق',
            'TREND_CONFIRM_SIGNALS': 'تأكيد الاتجاه الحالي',
            'ENTRY_SIGNALS_BULLISH': 'دخول صفقة شراء (CALL)',
            'ENTRY_SIGNALS_BEARISH': 'دخول صفقة بيع (PUT)',
            'EXIT_SIGNALS': 'خروج من الصفقات',
            'GENERAL_SIGNALS': 'إشارة عامة (مراقبة فقط)'
        }
        return descriptions.get(category, 'غير معروف')
    
    def process_signal(self, raw_signal: str) -> bool:
        """معالجة الإشارة"""
        try:
            signal_data = self.parse_signal(raw_signal)
            if not signal_data:
                return False
            
            category, category_desc = self.classify_signal(signal_data)
            signal_data.update({
                'signal_category': category_desc,
                'signal_description': f'إشارة {signal_data["signal_type"]}'
            })
            
            print(f"🎯 الإشارة المصنفة: {signal_data['signal_type']} -> {category} ({category_desc})")
            
            # معالجة خاصة لإشارات الاتجاه
            if category == 'TREND_SIGNALS':
                # لا نرسل رسالة الاتجاه هنا - سيتم إرسالها في TradeManager إذا تغير الاتجاه
                result = self.trade_manager.process_signal(signal_data)
                print(f"📊 نتيجة معالجة الاتجاه: {result['status']} - {result.get('message', '')}")
                return True
            
            # معالجة إشارات تأكيد الاتجاه
            elif category == 'TREND_CONFIRM_SIGNALS':
                result = self.trade_manager.process_confirmation_signal(signal_data)
                print(f"📊 نتيجة تأكيد الاتجاه: {result['status']} - {result.get('message', '')}")
                return True
            
            # معالجة إشارات الخروج
            elif category == 'EXIT_SIGNALS':
                result = self.trade_manager.close_trade(signal_data)
                print(f"📊 نتيجة إغلاق الصفقة: {result['status']} - {result.get('message', '')}")
                return result['status'] != 'error'
            
            # معالجة الإشارات العامة
            elif category == 'GENERAL_SIGNALS':
                message = self.message_formatter.format_general_signal(signal_data)
                self.notification_manager.send_message(message, signal_data)
                print(f"📊 إشارة عامة: {signal_data['signal_type']}")
                return True
            
            # معالجة باقي أنواع الإشارات
            else:
                result = self.trade_manager.process_signal(signal_data)
                print(f"📊 نتيجة المعالجة: {result['status']} - {result.get('message', '')}")
                
                # إرسال إشعار عام للإشارات غير المرتبطة بالصفقات
                if result['status'] in ['pending', 'trend_updated', 'general']:
                    message = self.message_formatter.format_general_signal(signal_data)
                    self.notification_manager.send_message(message, signal_data)
                
                return result['status'] != 'error'
            
        except Exception as e:
            print(f"❌ خطأ في معالجة الإشارة: {e}")
            return False
    
    def get_system_status(self) -> dict:
        """الحصول على حالة النظام"""
        return {
            'active_trades': self.trade_manager.get_active_trades_count(),
            'confirmation_stats': self.trade_manager.get_confirmation_stats(),
            'signal_categories_loaded': {
                'TREND_SIGNALS': len(self.config.TREND_SIGNALS),
                'TREND_CONFIRM_SIGNALS': len(self.config.TREND_CONFIRM_SIGNALS),
                'ENTRY_SIGNALS_BULLISH': len(self.config.ENTRY_SIGNALS_BULLISH),
                'ENTRY_SIGNALS_BEARISH': len(self.config.ENTRY_SIGNALS_BEARISH),
                'EXIT_SIGNALS': len(self.config.EXIT_SIGNALS),
                'GENERAL_SIGNALS': len(self.config.GENERAL_SIGNALS),
                'TOTAL_SIGNALS': len(self.config.ALL_SIGNALS)
            },
            'telegram_enabled': self.config.TELEGRAM_ENABLED,
            'external_server_enabled': self.config.EXTERNAL_SERVER_ENABLED
        }

# 🌐 تطبيق Flask الرئيسي
app = Flask(__name__)

# إعداد المسجل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('signal_server')

# تهيئة معالج الإشارات
try:
    signal_handler = SignalHandler()
    logger.info("✅ تم تحميل نظام معالجة الإشارات بنجاح")
except Exception as e:
    logger.error(f"❌ فشل تحميل نظام الإشارات: {e}")
    signal_handler = None

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    return jsonify({
        "status": "active",
        "service": "Trading Signal Processor - Integrated",
        "version": "4.0.0",
        "environment": "integrated",
        "port": 10000,
        "endpoints": {
            "webhook": "/webhook (POST)",
            "health": "/health (GET)",
            "status": "/status (GET)",
            "test": "/test (GET/POST)"
        }
    })

@app.route('/health')
def health_check():
    """فحص صحة الخادم"""
    return jsonify({
        "status": "healthy",
        "environment": "integrated",
        "port": 10000,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/status')
def system_status():
    """حالة النظام"""
    if signal_handler:
        status = signal_handler.get_system_status()
        return jsonify({
            "status": "operational",
            "environment": "integrated",
            "port": 10000,
            "active_trades": status['active_trades'],
            "confirmation_stats": status['confirmation_stats'],
            "signal_categories": status['signal_categories_loaded'],
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Signal handler not loaded"
        }), 500

@app.route('/webhook', methods=['POST'])
def webhook_receiver():
    """استقبال إشارات Webhook"""
    try:
        if not signal_handler:
            return jsonify({
                "status": "error",
                "message": "Signal processor not available"
            }), 503

        content_type = request.headers.get('Content-Type', '')
        raw_signal = ""
        
        if 'application/json' in content_type:
            data = request.get_json()
            if data:
                logger.info(f"📊 بيانات JSON مستلمة: {json.dumps(data, ensure_ascii=False)}")
                raw_signal = _convert_json_to_signal(data)
            else:
                raw_signal = request.get_data(as_text=True)
            
        elif 'text/plain' in content_type:
            raw_signal = request.get_data(as_text=True)
            logger.info(f"📝 نص مستلم: {raw_signal}")
            
        else:
            try:
                data = request.get_json()
                if data:
                    raw_signal = _convert_json_to_signal(data)
                else:
                    raw_signal = request.get_data(as_text=True)
            except:
                raw_signal = request.get_data(as_text=True)

        if not raw_signal or raw_signal.strip() == '':
            return jsonify({
                "status": "error",
                "message": "Empty signal received"
            }), 400

        logger.info(f"🔍 معالجة الإشارة: {raw_signal}")
        success = signal_handler.process_signal(raw_signal)

        if success:
            logger.info("✅ تم معالجة الإشارة بنجاح")
            return jsonify({
                "status": "success",
                "message": "Signal processed successfully",
                "signal": raw_signal,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            logger.error("❌ فشل في معالجة الإشارة")
            return jsonify({
                "status": "error",
                "message": "Failed to process signal",
                "signal": raw_signal,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 400

    except Exception as e:
        logger.error(f"💥 خطأ في معالجة Webhook: {e}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

@app.route('/test', methods=['GET', 'POST'])
def test_webhook():
    """صفحة اختبار Webhook"""
    if request.method == 'GET':
        return _get_test_page()
    else:
        return _handle_test_post(request)

def _get_test_page():
    """عرض صفحة الاختبار"""
    return '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <title>نظام إشارات التداول - النسخة المدمجة</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            h1 { color: #333; text-align: center; }
            textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
            .result { margin: 20px 0; padding: 15px; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 اختبار نظام إشارات التداول - المنفذ 10000</h1>
            <p>أدخل إشارة بصيغة: <code>Ticker : SYMBOL Signal : SIGNAL Open : PRICE Close : PRICE</code></p>
            
            <form method="POST">
                <textarea name="signal" placeholder="Ticker : BTCUSDT Signal : bullish_catcher Open : 110000 Close : 110100" required>Ticker : BTCUSDT Signal : bullish_catcher Open : 110000 Close : 110100</textarea>
                <br>
                <button type="submit">إرسال الإشارة</button>
            </form>
            
            <div>
                <h3>📋 أمثلة للإشارات:</h3>
                <ul>
                    <li><strong>إشارة اتجاه:</strong> <code>Ticker : BTCUSDT Signal : bullish_catcher Open : 110000 Close : 110100</code></li>
                    <li><strong>إشارة دخول:</strong> <code>Ticker : BTCUSDT Signal : Strong bullish confluence Open : 110000 Close : 110100</code></li>
                    <li><strong>إشارة خروج:</strong> <code>Ticker : BTCUSDT Signal : exit_buy Open : 110000 Close : 110100</code></li>
                    <li><strong>إشارة عامة:</strong> <code>Ticker : BTCUSDT Signal : Within Bullish Imbalance Open : 110000 Close : 110100</code></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''

def _handle_test_post(request):
    """معالجة طلب الاختبار"""
    raw_signal = request.form.get('signal', '')
    if signal_handler:
        success = signal_handler.process_signal(raw_signal)
        if success:
            return f'''
            <div class="result success">
                <h3>✅ تمت المعالجة بنجاح!</h3>
                <p><strong>الإشارة:</strong> {raw_signal}</p>
                <p><strong>الوقت:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            <a href="/test">⟲ اختبار إشارة أخرى</a>
            '''
        else:
            return f'''
            <div class="result error">
                <h3>❌ فشل في المعالجة</h3>
                <p><strong>الإشارة:</strong> {raw_signal}</p>
                <p>تحقق من صيغة الإشارة وحاول مرة أخرى.</p>
            </div>
            <a href="/test">⟲ محاولة مرة أخرى</a>
            '''
    else:
        return '''
        <div class="result error">
            <h3>❌ نظام المعالجة غير متاح</h3>
        </div>
        '''

def _convert_json_to_signal(data):
    """تحويل JSON إلى إشارة نصية بالصيغة الجديدة"""
    try:
        if isinstance(data, dict):
            ticker = data.get('ticker', data.get('symbol', 'UNKNOWN'))
            signal_type = data.get('signal', data.get('action', 'UNKNOWN'))
            open_price = str(data.get('open', '0'))
            close_price = str(data.get('close', '0'))
            return f"Ticker : {ticker} Signal : {signal_type} Open : {open_price} Close : {close_price}"
        else:
            return str(data)
    except Exception as e:
        logger.error(f"خطأ في تحويل JSON: {e}")
        return str(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"🚀 بدء تشغيل النظام المدمج على المنفذ {port}")
    logger.info(f"📍 العنوان: http://localhost:{port}")
    logger.info(f"🔧 وضع التصحيح: {debug_mode}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
