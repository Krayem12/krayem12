#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AbuRayan_Bot_V8.4_Exact_Match.py
نظام معالجة إشارات التداول - مطابقة تامة مع إشارات .env
- المطابقة التامة مع الإشارات في .env (نسخ ولصق)
- منع فتح الصفقات ضد الاتجاه بشكل صارم
- منع إرسال رسائل الاتجاه المكررة إلا عند تغيير الاتجاه
"""

import os
import json
import logging
import uuid
import re
import requests
import sys
import socket
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from decouple import config

# =============================
# تحميل متغيرات البيئة
# =============================
load_dotenv()


class TradingSystem:
    """النظام الرئيسي المدمج لإشارات التداول مع اتجاه منفصل لكل رمز"""

    def __init__(self):
        self.setup_config()
        self.setup_managers()
        self.setup_flask()
        self.display_loaded_signals()
        self.check_settings()

        print(f"🚀 نظام معالجة الإشارات جاهز - المنفذ {self.port}")
        print(f"✅ التأكيد المطلوب: {self.config['REQUIRED_CONFIRMATIONS']} إشارات مختلفة من نفس المجموعة")
        print(f"📊 الحد الأقصى للصفقات: {self.config['MAX_OPEN_TRADES']}")
        print(f"🎯 نظام اتجاه منفصل لكل رمز: مفعّل")
        print(f"🔒 منع الصفقات ضد الاتجاه: {'مفعّل' if self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] else 'معطل'}")
        print(f"🔕 منع رسائل الاتجاه المكررة: مفعّل")
        print(f"🎯 نظام المطابقة التامة مع .env: مفعّل")

    # =============================
    # الإعدادات والتهيئة
    # =============================
    def setup_config(self):
        """إعداد التكوين الكامل من .env"""
        self.config = {
            # 🔧 أساسي
            'APP_NAME': config('APP_NAME', default='TradingSignalProcessor'),
            'APP_VERSION': config('APP_VERSION', default='8.4.0'),
            'DEBUG': config('DEBUG', default=False, cast=bool),
            'LOG_LEVEL': config('LOG_LEVEL', default='INFO'),
            'LOG_FILE': config('LOG_FILE', default='app.log'),

            # 📱 Telegram
            'TELEGRAM_ENABLED': config('TELEGRAM_ENABLED', default=True, cast=bool),
            'TELEGRAM_BOT_TOKEN': config('TELEGRAM_BOT_TOKEN', default='your_bot_token_here'),
            'TELEGRAM_CHAT_ID': config('TELEGRAM_CHAT_ID', default='your_chat_id_here'),

            # 🌐 الخادم الخارجي (قروب احتياطي)
            'EXTERNAL_SERVER_ENABLED': config('EXTERNAL_SERVER_ENABLED', default=True, cast=bool),
            'EXTERNAL_SERVER_URL': config('EXTERNAL_SERVER_URL', default='https://api.example.com/webhook/trading'),
            'EXTERNAL_SERVER_TOKEN': config('EXTERNAL_SERVER_TOKEN', default=''),

            # ⚙️ التأكيد وإدارة الصفقات
            'REQUIRED_CONFIRMATIONS': config('REQUIRED_CONFIRMATIONS', default=3, cast=int),
            'CONFIRMATION_TIMEOUT': config('CONFIRMATION_TIMEOUT', default=1200, cast=int),
            'CONFIRMATION_WINDOW': config('CONFIRMATION_WINDOW', default=1200, cast=int),
            'MAX_OPEN_TRADES': config('MAX_OPEN_TRADES', default=10, cast=int),
            'RESPECT_TREND_FOR_REGULAR_TRADES': config('RESPECT_TREND_FOR_REGULAR_TRADES', default=True, cast=bool),
            'RESET_TRADES_ON_TREND_CHANGE': config('RESET_TRADES_ON_TREND_CHANGE', default=False, cast=bool),

            # 🔔 تحكم الإرسال
            'SEND_TREND_MESSAGES': config('SEND_TREND_MESSAGES', default=True, cast=bool),
            'SEND_ENTRY_MESSAGES': config('SEND_ENTRY_MESSAGES', default=True, cast=bool),
            'SEND_EXIT_MESSAGES': config('SEND_EXIT_MESSAGES', default=True, cast=bool),
            'SEND_CONFIRMATION_MESSAGES': config('SEND_CONFIRMATION_MESSAGES', default=True, cast=bool),
            'SEND_GENERAL_MESSAGES': config('SEND_GENERAL_MESSAGES', default=False, cast=bool),
            'SEND_BULLISH_SIGNALS': config('SEND_BULLISH_SIGNALS', default=True, cast=bool),
            'SEND_BEARISH_SIGNALS': config('SEND_BEARISH_SIGNALS', default=True, cast=bool),
        }

        self.port = config('PORT', default=10000, cast=int)

        # تحميل قوائم الإشارات
        self.signals = {
            'trend': self._load_signal_list('TREND_SIGNALS'),
            'trend_confirm': self._load_signal_list('TREND_CONFIRM_SIGNALS'),
            'entry_bullish': self._load_signal_list('ENTRY_SIGNALS_BULLISH'),
            'entry_bearish': self._load_signal_list('ENTRY_SIGNALS_BEARISH'),
            'exit': self._load_signal_list('EXIT_SIGNALS'),
            'general': self._load_signal_list('GENERAL_SIGNALS')
        }

        # فهرس سريع للمطابقة التامة
        self.exact_index = {}
        for category, arr in self.signals.items():
            for s in arr:
                self.exact_index[s] = category  # حفظ الإشارة كما هي

    def _load_signal_list(self, key):
        """تحميل الإشارات مع معالجة خاصة لـ catcher"""
        try:
            signal_str = config(key, default='')
            if not signal_str:
                return []
            
            # معالجة خاصة للإشارات التي تحتوي على catcher
            if 'catcher' in signal_str.lower():
                signals = [s.strip() for s in signal_str.split(',') if s.strip()]
                print(f"✅ [تحميل] إشارات catcher في {key}: {signals}")
                return signals
            
            # المعالجة الأصلية للإشارات الأخرى
            signals, current, inside = [], "", False
            for ch in signal_str:
                if ch == '(':
                    inside = True
                    current += ch
                elif ch == ')':
                    inside = False
                    current += ch
                elif ch == ',' and not inside:
                    if current.strip():
                        signals.append(current.strip())
                    current = ""
                else:
                    current += ch
            if current.strip():
                signals.append(current.strip())
            return signals
        except Exception as e:
            print(f"❌ خطأ في تحميل {key}: {e}")
            return []

    def display_loaded_signals(self):
        """عرض تفصيلي للإشارات المحملة"""
        print("\n🔖 الإشارات المحملة من .env (مطابقة تامة):")
        for category, signals in self.signals.items():
            print(f"   📁 {category}:")
            for i, signal in enumerate(signals, 1):
                print(f"      {i}. '{signal}'")
        
        print("\n🔖 الفهرس التام:")
        for signal, category in self.exact_index.items():
            print(f"   📍 '{signal}' -> {category}")

    def setup_managers(self):
        self.pending_signals = {}          # تأكيد الدخول
        self.active_trades = {}            # الصفقات المفتوحة
        self.symbol_trends = {}            # اتجاه لكل رمز
        self.last_trend_notifications = {} # آخر اتجاه تم الإشعار عنه
        self.last_trend_notified_at = {}   # آخر وقت تم الإشعار فيه

    def setup_flask(self):
        self.app = Flask(__name__)
        self.setup_routes()
        self.setup_logging()

    def setup_logging(self):
        self.logger = logging.getLogger('trading_system')
        self.logger.setLevel(getattr(logging, self.config['LOG_LEVEL'], logging.INFO))
        # ازالة أي handlers قديمة
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)

        fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file_path = os.path.join(os.getcwd(), self.config['LOG_FILE'])
        try:
            fh = logging.FileHandler(log_file_path, encoding='utf-8')
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)
            print(f"📁 ملف السجل مفعل: {log_file_path}")
        except Exception as e:
            print(f"⚠️ تعذر إنشاء ملف السجل: {e}")

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        self.logger.addHandler(sh)

    # =============================
    # تشخيص الشبكة والإعدادات
    # =============================
    def diagnose_external_server(self):
        print("\n🔍 تشخيص مفصل للخادم الخارجي:")
        print(f"   📍 الرابط: {self.config['EXTERNAL_SERVER_URL']}")
        # DNS
        try:
            domain = self.config['EXTERNAL_SERVER_URL'].split('//')[1].split('/')[0]
            ip = socket.gethostbyname(domain)
            print(f"   🌐 DNS يعمل: {domain} → {ip}")
        except Exception as e:
            print(f"   ❌ مشكلة DNS: {e}")

        # محاولة GET على الجذر
        try:
            test_base = self.config['EXTERNAL_SERVER_URL'].split('/sendMessage')[0]
            r = requests.get(test_base, timeout=5, verify=False)
            print(f"   📡 اتصال أساسي: {r.status_code}")
        except Exception as e:
            print(f"   ❌ فشل الاتصال الأساسي: {e}")

        print("   🗺️ فحص المسار: /sendMessage")

    def check_settings(self):
        print("\n🔍 فحص إعدادات Telegram:")
        print(f"   TELEGRAM_ENABLED: {self.config['TELEGRAM_ENABLED']}")
        tb = self.config['TELEGRAM_BOT_TOKEN']
        print(f"   TELEGRAM_BOT_TOKEN: {'****'+tb[-4:] if tb and tb!='your_bot_token_here' else 'غير مضبوط'}")
        print(f"   TELEGRAM_CHAT_ID: {self.config['TELEGRAM_CHAT_ID'] if self.config['TELEGRAM_CHAT_ID']!='your_chat_id_here' else 'غير مضبوط'}")
        print(f"   SEND_TREND_MESSAGES: {self.config['SEND_TREND_MESSAGES']}")
        print(f"   SEND_ENTRY_MESSAGES: {self.config['SEND_ENTRY_MESSAGES']}")
        print(f"   SEND_EXIT_MESSAGES: {self.config['SEND_EXIT_MESSAGES']}")

        if self.config['TELEGRAM_ENABLED'] and tb and tb != 'your_bot_token_here':
            print("   📡 اختبار Telegram...")
            ok = self.test_telegram_connection()
            print(f"   حالة الاتصال: {'✅ نجح' if ok else '❌ فشل'}")
        else:
            print("   ⚠️ إعدادات Telegram غير مكتملة")

        print("\n🔍 فحص إعدادات الخادم الخارجي:")
        print(f"   EXTERNAL_SERVER_ENABLED: {self.config['EXTERNAL_SERVER_ENABLED']}")
        print(f"   EXTERNAL_SERVER_URL: {self.config['EXTERNAL_SERVER_URL']}")
        print(f"   EXTERNAL_SERVER_TOKEN: {'مضبوط' if self.config['EXTERNAL_SERVER_TOKEN'] else 'غير مضبوط'}")

        if self.config['EXTERNAL_SERVER_ENABLED'] and \
           self.config['EXTERNAL_SERVER_URL'] and \
           self.config['EXTERNAL_SERVER_URL'] != 'https://api.example.com/webhook/trading':
            self.diagnose_external_server()
            ok = self.test_external_server_connection()
            print(f"   حالة الاتصال: {'✅ نجح' if ok else '❌ فشل'}")
        else:
            print("   ⚠️ إعدادات الخادم الخارجي غير مكتملة")

    def test_telegram_connection(self):
        try:
            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/getMe"
            r = requests.get(url, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print(f"   ❌ خطأ Telegram: {e}")
            return False

    def test_external_server_connection(self):
        """طلب POST نص خام للتأكد أن السيرفر يقبل text/plain"""
        try:
            print("   🌐 اختبار POST text/plain إلى الخادم الخارجي...")
            probe_text = "ping"
            r = requests.post(
                self.config['EXTERNAL_SERVER_URL'],
                data=probe_text.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=8,
                verify=False
            )
            print(f"   📊 الاستجابة: {r.status_code}")
            return r.status_code in (200, 201, 204)
        except Exception as e:
            print(f"   ❌ فشل الاختبار: {e}")
            return False

    # =============================
    # مسارات الويب
    # =============================
    def setup_routes(self):
        @self.app.route('/')
        def home():
            return jsonify({
                "status": "active",
                "service": self.config['APP_NAME'],
                "version": self.config['APP_VERSION'],
                "port": self.port
            })

        @self.app.route('/health')
        def health():
            return jsonify({"status": "healthy", "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

        @self.app.route('/status')
        def status():
            return jsonify(self.get_system_status())

        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            return self.handle_webhook(request)

    # =============================
    # حالة النظام
    # =============================
    def get_system_status(self):
        return {
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "open_trades": len([t for t in self.active_trades.values() if t['status'] == 'OPEN']),
            "pending_groups": len(self.pending_signals),
            "trends": self.symbol_trends,
            "last_notifications": self.last_trend_notifications
        }

    # =============================
    # معالجة الإشارات
    # =============================
    def handle_webhook(self, request):
        try:
            raw_signal = self.extract_signal_data(request)
            if not raw_signal:
                return jsonify({"status": "error", "message": "إشارة فارغة"}), 400

            self.logger.info(f"إشارة مستلمة: {raw_signal}")
            success = self.process_signal(raw_signal)

            if success:
                return jsonify({"status": "success", "message": "ok"})
            else:
                return jsonify({"status": "error", "message": "لم تُفتح صفقة/لم تُرسل رسالة"}), 400

        except Exception as e:
            self.logger.error(f"خطأ في Webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def extract_signal_data(self, request):
        """إخراج نص الإشارة من JSON أو نص خام"""
        ct = request.headers.get('Content-Type', '')
        if 'application/json' in ct:
            data = request.get_json(silent=True)
            if data:
                return self.convert_json_to_signal(data)
        raw = request.get_data(as_text=True)
        print(f"📥 [RAW] إشارة خام مستلمة: {repr(raw)}")
        return raw.strip() if raw else ''

    def convert_json_to_signal(self, data):
        if isinstance(data, dict):
            ticker = data.get('ticker', data.get('symbol', 'UNKNOWN'))
            signal_type = data.get('signal', data.get('action', 'UNKNOWN'))
            open_price = str(data.get('open', '0'))
            close_price = str(data.get('close', '0'))
            return f"Ticker : {ticker} Signal : {signal_type} Open : {open_price} Close : {close_price}"
        return str(data)

    def process_signal(self, raw_signal):
        signal_data = self.parse_signal(raw_signal)
        if not signal_data:
            self.logger.warning(f"إشارة غير صالحة: {raw_signal}")
            return False

        category = self.classify_signal(signal_data)
        signal_data['category'] = category
        self.logger.info(f"إشارة مصنفة: {signal_data['signal_type']} -> {category}")

        # 🔥 معالجة إشارات الاتجاه أولاً لتحديث اتجاه الرمز
        if category == 'trend':
            return self.handle_trend_signal(signal_data)
        if category == 'trend_confirm':
            return self.handle_trend_confirmation(signal_data)
        
        # 🔥 ثم معالجة إشارات الدخول مع الاتجاه المحدث
        if category == 'unknown':
            return self.handle_unknown_signal(signal_data)
        if category == 'exit':
            return self.handle_exit_signal(signal_data)
        if category in ('entry_bullish', 'entry_bearish'):
            return self.handle_entry_signal(signal_data, category)
        return self.handle_general_signal(signal_data)

    def parse_signal(self, raw_signal):
        """تحليل محسّن لنص الإشارة مع الحفاظ على النص الأصلي تماماً"""
        try:
            text = raw_signal.strip()
            if not text:
                return None
                
            print(f"🔍 [تحليل] نص الإشارة الخام: '{text}'")
            
            # النمط الأساسي: Ticker : XYZ Signal : ABC Open : 123 Close : 456
            pattern = r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+?)\s+Open\s*:\s*(.+?)\s+Close\s*:\s*(.+)'
            m = re.match(pattern, text)
            if m:
                ticker, signal_type, open_price, close_price = m.groups()
                print(f"✅ [تحليل] تطابق النمط الأساسي: {ticker} -> '{signal_type}'")
            else:
                # إذا لم يتطابق مع النمط الأساسي، افترض أن النص كله هو signal_type
                # واستخدم رمز افتراضي أو استخرج الرمز من البداية
                if ' ' in text:
                    # افترض أن أول كلمة هي الرمز والباقي هو الإشارة
                    parts = text.split(' ', 1)
                    if len(parts) == 2:
                        ticker, signal_type = parts[0], parts[1]
                        print(f"🔄 [تحليل] تقسيم النص: {ticker} -> '{signal_type}'")
                    else:
                        ticker = "UNKNOWN"
                        signal_type = text
                else:
                    ticker = "UNKNOWN"
                    signal_type = text
                    print(f"⚠️ [تحليل] نص بسيط: '{signal_type}'")

            # تنظيف NaN
            s_lower = signal_type.lower()
            if 'nan' in s_lower:
                if 'bullish' in s_lower:
                    signal_type = 'bullish_trend'
                elif 'bearish' in s_lower:
                    signal_type = 'bearish_trend'
                else:
                    return None

            result = {
                'ticker': ticker.strip(),
                'signal_type': signal_type.strip(),  # كما هي بدون تعديل
                'original_signal': signal_type.strip(),  # حفظ الإشارة الأصلية
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'TradingView'
            }
            print(f"✅ [تحليل] نتيجة التحليل: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل الإشارة: {e}")
            print(f"❌ [تحليل] خطأ: {e}")
            return None

    # =============================
    # تصنيف الإشارات - المطابقة التامة
    # =============================
    def clean_signal_type(self, signal_type):
        """تنظيف يحافظ على التطابق التام مع .env"""
        # فقط إزالة المسافات الطرفية للحفاظ على المطابقة التامة
        return signal_type.strip()

    def classify_signal(self, signal_data):
        """تصنيف يعتمد على المطابقة التامة مع إشارات .env"""
        signal_type = self.clean_signal_type(signal_data['signal_type'])
        
        print(f"🔍 [تصنيف] البحث عن تطابق تام للإشارة: '{signal_type}'")
        
        # البحث المباشر في الفهرس التام
        if signal_type in self.exact_index:
            category = self.exact_index[signal_type]
            print(f"✅ [تصنيف] تطابق تام: '{signal_type}' -> '{category}'")
            return category
        
        print(f"❌ [تصنيف] لا يوجد تطابق تام: '{signal_type}' -> 'unknown'")
        return 'unknown'

    def handle_unknown_signal(self, signal_data):
        """معالجة الإشارات غير المعروفة (غير موجودة في .env)"""
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        
        print(f"🚫 [غير معروفة] تجاهل إشارة غير معرفة في .env: '{signal}' للرمز {symbol}")
        self.logger.warning(f"إشارة غير معروفة: '{signal}' للرمز {symbol}")
        
        # تجاهل الإشارة تماماً
        return False

    # =============================
    # معالجات حسب الفئة
    # =============================
    def handle_trend_signal(self, signal_data):
        """معالجة محسنة لإشارات الاتجاه مع منع الإرسال المكرر"""
        symbol = signal_data['ticker']
        original_signal = signal_data.get('original_signal', signal_data['signal_type'])
        s = original_signal.lower()
        
        print(f"🎯 [اتجاه] معالجة إشارة اتجاه: '{original_signal}' للرمز {symbol}")

        if 'bullish_catcher' in s or 'bullish_trend' in s:
            new_trend = 'BULLISH'
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        elif 'bearish_catcher' in s or 'bearish_trend' in s:
            new_trend = 'BEARISH'
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        else:
            print(f"❌ [اتجاه] إشارة اتجاه غير معروفة: '{original_signal}'")
            return False

        current_trend = self.symbol_trends.get(symbol)
        last_notified_trend = self.last_trend_notifications.get(symbol)
        
        # 🔥 تحديث اتجاه الرمز دائماً
        self.symbol_trends[symbol] = new_trend
        
        # 🔥 التحقق إذا كان الاتجاه قد تغير
        changed = current_trend != new_trend
        
        # 🔥 التحقق إذا كان هذا نفس الاتجاه الذي تم الإشعار عنه مسبقاً
        same_as_last_notification = last_notified_trend == new_trend
        
        print(f"🔍 [اتجاه] {symbol}: الحالي={current_trend}, الجديد={new_trend}, تغيير={changed}")
        print(f"🔍 [إشعار] آخر إشعار={last_notified_trend}, نفس الإشعار={same_as_last_notification}")

        # 🔥 إرسال الإشعار فقط إذا تغير الاتجاه أو لم يتم الإشعار مسبقاً
        should_notify = False
        
        if changed:
            should_notify = True
            print(f"🔄 [اتجاه] تغيير اتجاه {symbol}: {current_trend} -> {new_trend}")
        elif last_notified_trend is None:
            should_notify = True
            print(f"📢 [اتجاه] أول إشعار لاتجاه {symbol}: {new_trend}")
        else:
            print(f"🔕 [اتجاه] تجاهل إشعار مكرر لـ {symbol}: {new_trend}")

        if should_notify:
            msg = self.format_trend_message(signal_data, trend_icon, trend_text)
            
            # إرسال لتيليجرام إذا كان مفعلاً
            if self.should_send_message('trend', signal_data):
                telegram_sent = self.send_telegram(msg)
                if telegram_sent:
                    print(f"✅ [Telegram] تم إرسال إشعار اتجاه {symbol}: {new_trend}")
                else:
                    print(f"❌ [Telegram] فشل إرسال إشعار اتجاه {symbol}")
            else:
                print(f"🔕 [Telegram] إرسال رسائل الاتجاه معطل")
            
            # إرسال للخادم الخارجي
            external_sent = self.send_to_external_server_with_retry(msg, 'trend')
            if external_sent:
                print(f"✅ [الخادم] تم إرسال إشعار اتجاه {symbol}: {new_trend}")
            else:
                print(f"❌ [الخادم] فشل إرسال إشعار اتجاه {symbol}")
            
            # تحديث آخر إشعار
            self.last_trend_notifications[symbol] = new_trend
            self.last_trend_notified_at[symbol] = datetime.now()
            self.logger.info(f"إشعار اتجاه {symbol}: {new_trend} (تغيير: {changed})")
        else:
            print(f"🔕 [اتجاه] لا حاجة للإشعار - نفس الاتجاه {new_trend} للرمز {symbol}")

        # إغلاق صفقات الرمز فقط عند تغيير الاتجاه (اختياري)
        if self.config['RESET_TRADES_ON_TREND_CHANGE'] and changed:
            closed = 0
            for tid in list(self.active_trades.keys()):
                tr = self.active_trades[tid]
                if tr['ticker'] == symbol and tr['status'] == 'OPEN':
                    tr.update({
                        'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'CLOSED',
                        'exit_signal': 'trend_change'
                    })
                    closed += 1
            if closed:
                self.logger.info(f"إغلاق {closed} صفقة للرمز {symbol} بسبب تغيير الاتجاه")
        
        return True

    def handle_trend_confirmation(self, signal_data):
        """تأكيد اتجاه عند ورود tracer مطابق للاتجاه الحالي"""
        symbol = signal_data['ticker']
        s = signal_data['signal_type'].lower()
        current = self.symbol_trends.get(symbol)

        if not current:
            # لا يوجد اتجاه مثبت بعد
            return False

        same = (('bullish' in s and current == 'BULLISH') or
                ('bearish' in s and current == 'BEARISH'))

        if not same:
            return False

        trend_icon = "🟢📈" if current == 'BULLISH' else "🔴📉"
        trend_text = "شراء (اتجاه صاعد)" if current == 'BULLISH' else "بيع (اتجاه هابط)"
        msg = self.format_trend_confirmation_message(signal_data, trend_icon, trend_text)
        if self.should_send_message('confirmation', signal_data):
            self.send_telegram(msg)
        self.send_to_external_server_with_retry(msg, 'trend_confirmation')
        self.logger.info(f"تأكيد اتجاه {symbol}: {current}")
        return True

    def handle_entry_signal(self, signal_data, signal_category):
        """معالجة محسنة لإشارات الدخول مع تطبيق صارم لشرط الاتجاه"""
        original_signal = signal_data.get('original_signal', signal_data['signal_type'])
        
        # 🔥 منع معالجة إشارات catcher كإشارات دخول
        if 'catcher' in original_signal.lower():
            print(f"🚫 [دخول] تجاهل إشارة اتجاه كإشارة دخول: '{original_signal}'")
            return False
        
        symbol = signal_data['ticker']

        # لا أكثر من صفقة للرمز
        if self.find_active_trade(symbol):
            self.logger.warning(f"تجاهل فتح صفقة: توجد صفقة مفتوحة للرمز {symbol}")
            return False

        # حد الصفقات
        open_count = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        if open_count >= self.config['MAX_OPEN_TRADES']:
            self.logger.warning("الحد الأقصى للصفقات مكتفي")
            return False

        # 🔥 🔥 🔥 التصحيح: تطبيق شرط الاتجاه بشكل صارم
        symbol_trend = self.symbol_trends.get(symbol)
        print(f"🔍 [اتجاه] التحقق من مطابقة الاتجاه: {symbol} -> {symbol_trend}, الإشارة: {signal_category}")
        
        if self.config['RESPECT_TREND_FOR_REGULAR_TRADES']:
            if not symbol_trend:
                print(f"❌ [اتجاه] لا يمكن فتح صفقة: لا يوجد اتجاه محدد للرمز {symbol}")
                self.logger.warning(f"لا يمكن فتح صفقة: لا يوجد اتجاه محدد للرمز {symbol}")
                return False
            
            if (signal_category == 'entry_bullish' and symbol_trend != 'BULLISH') or \
               (signal_category == 'entry_bearish' and symbol_trend != 'BEARISH'):
                print(f"❌ [اتجاه] رفض الصفقة: إشارة {signal_category} ضد اتجاه {symbol_trend} للرمز {symbol}")
                self.logger.warning(f"الإشارة لا تتطابق مع اتجاه {symbol} ({symbol_trend})")
                return False
            else:
                print(f"✅ [اتجاه] الصفقة مطابقة للاتجاه: {signal_category} مع {symbol_trend}")

        # تجميع للتأكيد
        key = f"{symbol}_{signal_category}"
        self.clean_expired_signals()

        if key not in self.pending_signals:
            self.pending_signals[key] = {
                'unique_signals': set(),
                'signals_data': [],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'signal_category': signal_category
            }

        clean_type = self.clean_signal_type(signal_data['signal_type'])
        group = self.pending_signals[key]

        now = datetime.now()
        if (now - group['created_at']).total_seconds() > self.config['CONFIRMATION_WINDOW']:
            # إعادة ضبط النافذة
            self.pending_signals[key] = {
                'unique_signals': set(),
                'signals_data': [],
                'created_at': now,
                'updated_at': now,
                'signal_category': signal_category
            }
            group = self.pending_signals[key]

        if clean_type not in group['unique_signals']:
            group['unique_signals'].add(clean_type)
            group['signals_data'].append(signal_data)
            group['updated_at'] = now
            self.logger.info(f"إشارة فريدة: '{signal_data['signal_type']}' للمجموعة {signal_category}")
        else:
            self.logger.info(f"تجاهل إشارة مكررة: '{signal_data['signal_type']}'")
            return True

        if len(group['unique_signals']) >= self.config['REQUIRED_CONFIRMATIONS']:
            return self.open_confirmed_trade(key, signal_category)
        else:
            self.logger.info(f"في انتظار التأكيد: {len(group['unique_signals'])}/{self.config['REQUIRED_CONFIRMATIONS']}")
            return True

    def clean_expired_signals(self):
        now = datetime.now()
        to_delete = []
        for k, data in self.pending_signals.items():
            last = data.get('updated_at', data['created_at'])
            if (now - last).total_seconds() > self.config['CONFIRMATION_TIMEOUT']:
                to_delete.append(k)
        for k in to_delete:
            del self.pending_signals[k]
            self.logger.info(f"تنظيف مجموعة منتهية: {k}")

    def open_confirmed_trade(self, key, category):
        data = self.pending_signals.get(key)
        if not data or len(data['unique_signals']) < self.config['REQUIRED_CONFIRMATIONS']:
            return False

        main = data['signals_data'][0]
        trade_id = str(uuid.uuid4())[:8]
        direction = 'CALL' if category == 'entry_bullish' else 'PUT'

        trade_info = {
            'trade_id': trade_id,
            'ticker': main['ticker'],
            'direction': direction,
            'signal_type': main['signal_type'],
            'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'OPEN',
            'confirmation_count': len(data['unique_signals']),
            'confirmed_signals': list(data['unique_signals'])
        }
        self.active_trades[trade_id] = trade_info

        msg = self.format_entry_message(trade_info, data)
        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            self.send_telegram(msg)
        self.send_to_external_server_with_retry(msg, 'entry')

        del self.pending_signals[key]
        self.logger.info(f"فتح صفقة {direction} #{trade_id} بإشارات: {list(data['unique_signals'])}")
        return True

    def handle_exit_signal(self, signal_data):
        trade = self.find_active_trade(signal_data['ticker'])
        if not trade:
            self.logger.warning(f"لا توجد صفقة نشطة للرمز {signal_data['ticker']}")
            return False

        trade.update({
            'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'CLOSED',
            'exit_signal': signal_data['signal_type']
        })

        msg = self.format_exit_message(trade)
        if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
            self.send_telegram(msg)
        self.send_to_external_server_with_retry(msg, 'exit')

        self.logger.info(f"إغلاق صفقة #{trade['trade_id']}")
        return True

    def handle_general_signal(self, signal_data):
        msg = self.format_general_message(signal_data)
        if self.should_send_message('general', signal_data):
            self.send_telegram(msg)
        self.send_to_external_server_with_retry(msg, 'general')
        self.logger.info(f"إشارة عامة: '{signal_data['signal_type']}'")
        return True

    def find_active_trade(self, ticker):
        for tr in self.active_trades.values():
            if tr['ticker'] == ticker and tr['status'] == 'OPEN':
                return tr
        return None

    # =============================
    # التحكم في الإرسال
    # =============================
    def should_send_message(self, message_type, signal_data=None):
        """فلتر الإرسال لتيليجرام (ويُستخدم نفس القرار للخادم الخارجي لتطابق السلوك)"""
        type_controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }
        if not type_controls.get(message_type, False):
            print(f"🔕 إرسال رسائل {message_type} معطل")
            return False

        if signal_data:
            st = str(signal_data.get('signal_type', '')).lower()
            direction = signal_data.get('direction', '').upper()
            if ('bullish' in st or direction == 'CALL') and not self.config['SEND_BULLISH_SIGNALS']:
                print("🔕 إرسال الإشارات الصاعدة معطل")
                return False
            if ('bearish' in st or direction == 'PUT') and not self.config['SEND_BEARISH_SIGNALS']:
                print("🔕 إرسال الإشارات الهابطة معطل")
                return False

        return True

    # =============================
    # قوالب الرسائل (مطابقة)
    # =============================
    def format_trend_message(self, signal_data, trend_icon, trend_text):
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        ts = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        return f"""☰☰☰ 📊 الاتجاه العام ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal}
┃ 🔄 الحالة: الاتجاه العام محدث
┗━━━━━━━━━━━━━━━━━━━━
🕐 {ts}"""

    def format_trend_confirmation_message(self, signal_data, trend_icon, trend_text):
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        ts = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        return f"""✅ 📊 تأكيـــــد الاتجــــاه 📊 ✅
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه المؤكد: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal}
┃ ✅ الحالة: تأكيد مطابقة الاتجاه العام
┗━━━━━━━━━━━━━━━━━━━━
🕐 {ts}"""

    def format_entry_message(self, trade_info, pending_data):
        symbol = trade_info['ticker']
        direction = trade_info['direction']
        signal = trade_info['signal_type']
        confirmations = trade_info.get('confirmation_count', 1)
        helpers = trade_info.get('confirmed_signals', [])
        trend = self.symbol_trends.get(symbol, '')
        trend_icon = '🟢📈 BULLISH' if trend == 'BULLISH' else '🔴📉 BEARISH'
        align_text = '🟢 مطابق للاتجاه العام' if ((direction == 'CALL' and trend == 'BULLISH') or (direction == 'PUT' and trend == 'BEARISH')) else '🔴 غير مطابق'
        ts = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        helpers_list = ''
        if len(helpers) > 1:
            numbered = [f"┃   {i+1}. {h}" for i, h in enumerate(helpers[1:])]
            helpers_list = "\n" + "\n".join(numbered)

        return (
            "✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 🎯 نوع الصفقة: {'🟢 شراء' if direction=='CALL' else '🔴 بيع'}\n"
            f"┃ 📊 اتجاه الرمز: {trend_icon}\n"
            f"┃ 🎯 محاذاة الاتجاه: {align_text}\n"
            f"┃ 📋 الإشارة الرئيسية: {signal} (تم التأكيد بـ {confirmations} إشارات)\n"
            f"┃ 🔔 الإشارات المساعدة: {len(helpers)-1} إشارة{helpers_list}\n"
            f"┃ 📊 الصفقات المفتوحة: {len([t for t in self.active_trades.values() if t['status']=='OPEN'])} من {self.config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {ts}"
        )

    def format_exit_message(self, trade):
        symbol = trade['ticker']
        exit_signal = trade.get('exit_signal', 'غير محدد')
        direction = trade.get('direction', 'CALL')
        dir_text = '🟢 شراء' if direction == 'CALL' else '🔴 بيع (PUT)'
        ts = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        open_count = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        return (
            "════ 🚪 إشـــــــارة خــــــروج ════\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 📝 السبب: إشارة خروج: {exit_signal}\n"
            f"┃ 🎯 نوع الصفقة المغلقة: {dir_text}\n"
            f"┃ 📊 الصفقات المفتوحة: {open_count}/{self.config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {ts}"
        )

    def format_general_message(self, signal_data):
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        ts = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        return (
            "ℹ️ إشـــــــــــارة عامـــــــــــــة\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 📝 التفاصيل: {signal}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {ts}"
        )

    # =============================
    # الإرسال
    # =============================
    def send_telegram(self, message):
        """إرسال لتيليجرام بنفس القالب"""
        print("🔍 محاولة إرسال Telegram...")
        if not self.config['TELEGRAM_ENABLED']:
            print("❌ Telegram معطل")
            return False
        if not self.config['TELEGRAM_BOT_TOKEN'] or self.config['TELEGRAM_BOT_TOKEN'] == 'your_bot_token_here':
            print(f"📲 محاكاة Telegram (TOKEN غير مضبوط):\n{message}")
            return True
        if not self.config['TELEGRAM_CHAT_ID'] or self.config['TELEGRAM_CHAT_ID'] == 'your_chat_id_here':
            print("❌ TELEGRAM_CHAT_ID غير مضبوط")
            return False
        try:
            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            payload = {
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': message,
                'parse_mode': 'HTML'
            }
            print(f"🔗 POST {url}")
            r = requests.post(url, json=payload, timeout=10)
            ok = r.status_code == 200
            if ok:
                print("✅ تم إرسال Telegram")
                self.logger.info("تم إرسال Telegram")
            else:
                print(f"❌ فشل Telegram: {r.status_code} - {r.text[:200]}")
                self.logger.error(f"فشل Telegram: {r.status_code} - {r.text}")
            return ok
        except Exception as e:
            print(f"💥 خطأ Telegram: {e}")
            self.logger.error(f"خطأ Telegram: {e}")
            return False

    def send_to_external_server(self, message_text, message_type):
        """
        إرسال للقروب الاحتياطي كنص خام 1:1
        - Content-Type: text/plain; charset=utf-8
        - Body = الرسالة نفسها (بدون message= وبدون ترميز URL وبدون JSON)
        """
        if not self.config['EXTERNAL_SERVER_ENABLED']:
            return False
        url = self.config['EXTERNAL_SERVER_URL']
        if not url or url == 'https://api.example.com/webhook/trading':
            return False
        try:
            r = requests.post(
                url,
                data=message_text.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=10,
            )
            if r.status_code in (200, 201, 204):
                print("✅ تم إرسال الرسالة للخادم الاحتياطي (مطابقة 1:1)")
                self.logger.info("تم إرسال الرسالة للخادم الاحتياطي")
                return True
            else:
                print(f"❌ فشل الخادم الخارجي: {r.status_code} - {r.text[:200]}")
                return False
        except Exception as e:
            print(f"💥 خطأ الخادم الخارجي: {e}")
            return False

    def send_to_external_server_with_retry(self, message_text, message_type, max_retries=2):
        """إعادة المحاولة للخادم الخارجي، مع احترام فلاتر should_send_message"""
        if not self.should_send_message(
            'trend' if message_type == 'trend' else
            'entry' if message_type == 'entry' else
            'exit' if message_type == 'exit' else
            'confirmation' if message_type == 'trend_confirmation' else
            'general'
        ):
            print(f"🔕 إرسال {message_type} للخادم الاحتياطي معطل وفق الإعدادات")
            return False

        for attempt in range(max_retries + 1):
            if self.send_to_external_server(message_text, message_type):
                return True
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"🔄 إعادة المحاولة بعد {wait} ثوانٍ... ({attempt + 1}/{max_retries})")
                time.sleep(wait)
        return False


# =============================
# تشغيل النظام
# =============================
system = TradingSystem()
app = system.app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=system.port)
