#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام معالجة إشارات التداول - نسخة ملف واحد (V8) بعد التصحيح
- يحافظ على نفس نماذج رسائل Telegram والخادم الخارجي (بدون تغيير التنسيق)
- إصلاحات أساسية: استخدام فلاتر الإرسال، تحسين تصنيف الإشارات، نافذة التأكيد، منع تكرار فتح صفقات نفس الرمز، صلابة تحليل الإشارة
"""

import os
import json
import logging
import uuid
import re
import requests
import platform
import sys
import socket
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from decouple import config

# تحميل متغيرات البيئة
load_dotenv()

class TradingSystem:
    """النظام الرئيسي المدمج لإشارات التداول مع اتجاه منفصل لكل رمز"""

    def __init__(self):
        self.setup_config()
        self.setup_managers()
        self.setup_flask()
        self.display_loaded_signals()
        self.check_settings()  # ✅ فحص إعدادات Telegram والخادم الخارجي

        print(f"🚀 نظام معالجة الإشارات جاهز - المنفذ {self.port}")
        print(f"✅ التأكيد المطلوب: {self.config['REQUIRED_CONFIRMATIONS']} إشارات مختلفة من نفس المجموعة")
        print(f"📊 الحد الأقصى للصفقات: {self.config['MAX_OPEN_TRADES']}")
        print(f"🎯 نظام اتجاه منفصل لكل رمز: مفعّل")

    # =============================
    # الإعدادات والتهيئة
    # =============================
    def setup_config(self):
        """إعداد التكوين الكامل من .env"""
        self.config = {
            # 🔧 الإعدادات الأساسية
            'APP_NAME': config('APP_NAME', default='TradingSignalProcessor'),
            'APP_VERSION': config('APP_VERSION', default='4.0.0'),
            'DEBUG': config('DEBUG', default=False, cast=bool),
            'LOG_LEVEL': config('LOG_LEVEL', default='INFO'),
            'LOG_FILE': config('LOG_FILE', default='app.log'),

            # 📱 إعدادات Telegram
            'TELEGRAM_ENABLED': config('TELEGRAM_ENABLED', default=True, cast=bool),
            'TELEGRAM_BOT_TOKEN': config('TELEGRAM_BOT_TOKEN', default='your_bot_token_here'),
            'TELEGRAM_CHAT_ID': config('TELEGRAM_CHAT_ID', default='your_chat_id_here'),

            # 🌐 إعدادات الخادم الخارجي
            'EXTERNAL_SERVER_ENABLED': config('EXTERNAL_SERVER_ENABLED', default=False, cast=bool),
            'EXTERNAL_SERVER_URL': config('EXTERNAL_SERVER_URL', default='https://api.example.com/webhook/trading'),
            'EXTERNAL_SERVER_TOKEN': config('EXTERNAL_SERVER_TOKEN', default='your_external_server_token_here'),

            # ⚙️ إعدادات التأكيد وإدارة الصفقات
            'REQUIRED_CONFIRMATIONS': config('REQUIRED_CONFIRMATIONS', default=3, cast=int),
            'CONFIRMATION_TIMEOUT': config('CONFIRMATION_TIMEOUT', default=1200, cast=int),
            'CONFIRMATION_WINDOW': config('CONFIRMATION_WINDOW', default=1200, cast=int),  # نافذة زمنية بين أول وآخر إشارة لنفس المجموعة
            'MAX_OPEN_TRADES': config('MAX_OPEN_TRADES', default=10, cast=int),
            'RESPECT_TREND_FOR_REGULAR_TRADES': config('RESPECT_TREND_FOR_REGULAR_TRADES', default=True, cast=bool),
            'RESET_TRADES_ON_TREND_CHANGE': config('RESET_TRADES_ON_TREND_CHANGE', default=False, cast=bool),

            # 🔔 التحكم في إرسال رسائل Telegram
            'SEND_TREND_MESSAGES': config('SEND_TREND_MESSAGES', default=True, cast=bool),
            'SEND_ENTRY_MESSAGES': config('SEND_ENTRY_MESSAGES', default=True, cast=bool),
            'SEND_EXIT_MESSAGES': config('SEND_EXIT_MESSAGES', default=True, cast=bool),
            'SEND_CONFIRMATION_MESSAGES': config('SEND_CONFIRMATION_MESSAGES', default=True, cast=bool),
            'SEND_GENERAL_MESSAGES': config('SEND_GENERAL_MESSAGES', default=False, cast=bool),
            'SEND_BULLISH_SIGNALS': config('SEND_BULLISH_SIGNALS', default=True, cast=bool),
            'SEND_BEARISH_SIGNALS': config('SEND_BEARISH_SIGNALS', default=True, cast=bool),
        }

        self.port = config('PORT', default=10000, cast=int)

        # تحميل قوائم الإشارات الكاملة
        self.signals = {
            'trend': self._load_signal_list('TREND_SIGNALS'),
            'trend_confirm': self._load_signal_list('TREND_CONFIRM_SIGNALS'),
            'entry_bullish': self._load_signal_list('ENTRY_SIGNALS_BULLISH'),
            'entry_bearish': self._load_signal_list('ENTRY_SIGNALS_BEARISH'),
            'exit': self._load_signal_list('EXIT_SIGNALS'),
            'general': self._load_signal_list('GENERAL_SIGNALS')
        }

        # إنشاء قائمة بجميع الإشارات + فهرس سريع للتصنيف
        self.all_signals = []
        self.normalized_index = {}  # {normalized_signal: category}
        for category, category_signals in self.signals.items():
            for s in category_signals:
                self.all_signals.append(s)
                ns = self._normalize_signal_name(s)
                self.normalized_index[ns] = category

    def _load_signal_list(self, key):
        """تحميل قائمة الإشارات من .env مع معالجة القوائم الطويلة"""
        try:
            signal_str = config(key, default='')
            if not signal_str:
                return []

            signals = []
            current_signal = ""
            inside_parentheses = False

            for char in signal_str:
                if char == '(':
                    inside_parentheses = True
                    current_signal += char
                elif char == ')':
                    inside_parentheses = False
                    current_signal += char
                elif char == ',' and not inside_parentheses:
                    if current_signal.strip():
                        signals.append(current_signal.strip())
                    current_signal = ""
                else:
                    current_signal += char

            if current_signal.strip():
                signals.append(current_signal.strip())

            return signals

        except Exception as e:
            print(f"❌ خطأ في تحميل الإشارات من {key}: {e}")
            return []

    def setup_managers(self):
        """إعداد المديرين الداخليين"""
        self.pending_signals = {}
        self.active_trades = {}
        self.symbol_trends = {}  # {symbol: 'BULLISH'|'BEARISH'}
        self.last_trend_notifications = {}  # {symbol: last_trend_string}
        self.last_trend_notified_at = {}    # {symbol: datetime}

    def setup_flask(self):
        """إعداد تطبيق Flask والمسارات"""
        self.app = Flask(__name__)
        self.setup_routes()
        self.setup_logging()

    def setup_logging(self):
        """إعداد نظام التسجيل - معدل لدعم Windows"""
        self.logger = logging.getLogger('trading_system')
        self.logger.setLevel(getattr(logging, self.config['LOG_LEVEL']))

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        try:
            log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.config['LOG_FILE'])
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            print(f"📁 ملف السجل: {log_file_path}")
        except Exception as e:
            print(f"❌ خطأ في إنشاء ملف السجل: {e}")
            print("⚠️  سيتم استخدام التسجيل في الطرفية فقط")

        stream_handler = logging.StreamHandler(sys.stdout)

        if platform.system() == 'Windows':
            class NoEmojiFormatter(logging.Formatter):
                def format(self, record):
                    try:
                        text = str(record.msg)
                        emoji_pattern = re.compile("[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2702-\u27B0\u24C2-\U0001F251]+", flags=re.UNICODE)
                        record.msg = emoji_pattern.sub('', text)
                    except Exception:
                        pass
                    return super().format(record)
            stream_handler.setFormatter(NoEmojiFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        else:
            stream_handler.setFormatter(formatter)

        self.logger.addHandler(stream_handler)

    # =============================
    # تشخيص الشبكة والإعدادات
    # =============================
    def diagnose_external_server(self):
        """تشخيص مفصل لمشكلة الخادم الخارجي"""
        print("\n🔍 تشخيص مفصل للخادم الخارجي:")
        print(f"   📍 الرابط: {self.config['EXTERNAL_SERVER_URL']}")

        try:
            domain = self.config['EXTERNAL_SERVER_URL'].split('//')[1].split('/')[0]
            ip = socket.gethostbyname(domain)
            print(f"   🌐 DNS يعمل: {domain} → {ip}")
        except Exception as e:
            print(f"   ❌ مشكلة في DNS: {e}")
            return False

        try:
            test_url = self.config['EXTERNAL_SERVER_URL'].split('/sendMessage')[0]
            response = requests.get(test_url, timeout=5, verify=False)
            print(f"   📡 الاتصال الأساسي: ✅ ({response.status_code})")
        except Exception as e:
            print(f"   ❌ فشل الاتصال الأساسي: {e}")

        print(f"   🗺️  فحص المسار: /sendMessage")
        return True

    def check_settings(self):
        """فحص إعدادات Telegram والخادم الخارجي"""
        print("\n🔍 فحص إعدادات Telegram:")
        print(f"   TELEGRAM_ENABLED: {self.config['TELEGRAM_ENABLED']}")
        print(f"   TELEGRAM_BOT_TOKEN: {'****' + self.config['TELEGRAM_BOT_TOKEN'][-4:] if self.config['TELEGRAM_BOT_TOKEN'] and self.config['TELEGRAM_BOT_TOKEN'] != 'your_bot_token_here' else 'غير مضبوط'}")
        print(f"   TELEGRAM_CHAT_ID: {self.config['TELEGRAM_CHAT_ID'] if self.config['TELEGRAM_CHAT_ID'] and self.config['TELEGRAM_CHAT_ID'] != 'your_chat_id_here' else 'غير مضبوط'}")
        print(f"   SEND_TREND_MESSAGES: {self.config['SEND_TREND_MESSAGES']}")
        print(f"   SEND_ENTRY_MESSAGES: {self.config['SEND_ENTRY_MESSAGES']}")
        print(f"   SEND_EXIT_MESSAGES: {self.config['SEND_EXIT_MESSAGES']}")

        if self.config['TELEGRAM_ENABLED'] and self.config['TELEGRAM_BOT_TOKEN'] and self.config['TELEGRAM_BOT_TOKEN'] != 'your_bot_token_here':
            print("   📡 اختبار الاتصال بالـ Telegram...")
            test_result = self.test_telegram_connection()
            print(f"   حالة الاتصال: {'✅ نجح' if test_result else '❌ فشل'}")
        else:
            print("   ⚠️  إعدادات Telegram غير مكتملة")

        print("\n🔍 فحص إعدادات الخادم الخارجي:")
        print(f"   EXTERNAL_SERVER_ENABLED: {self.config['EXTERNAL_SERVER_ENABLED']}")
        print(f"   EXTERNAL_SERVER_URL: {self.config['EXTERNAL_SERVER_URL']}")
        print(f"   EXTERNAL_SERVER_TOKEN: {'مضبوط' if self.config['EXTERNAL_SERVER_TOKEN'] and self.config['EXTERNAL_SERVER_TOKEN'] != 'your_external_server_token_here' else 'غير مضبوط'}")

        if self.config['EXTERNAL_SERVER_ENABLED'] and self.config['EXTERNAL_SERVER_URL'] and self.config['EXTERNAL_SERVER_URL'] != 'https://api.example.com/webhook/trading':
            print("   🌐 اختبار الاتصال بالخادم الخارجي...")
            self.diagnose_external_server()
            test_result = self.test_external_server_connection()
            print(f"   حالة الاتصال: {'✅ نجح' if test_result else '❌ فشل'}")
            if not test_result:
                print("   💡 اقتراح: تحقق من:")
                print("      - أن الخادم يعمل وتقوم بالاستماع على المنفذ الصحيح")
                print("      - أن رابط /sendMessage صحيح")
                print("      - أن الخادم يقبل طلبات POST بدون توكن")
                print("      - أن لا توجد قيود على الـ CORS أو الـ Firewall")
        else:
            print("   ⚠️  إعدادات الخادم الخارجي غير مكتملة")

    def test_telegram_connection(self):
        """اختبار الاتصال بـ Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/getMe"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"   ❌ خطأ في اختبار الاتصال: {e}")
            return False

    def test_external_server_connection(self):
        """اختبار الاتصال بالخادم الخارجي بدون توكن - محسّن"""
        try:
            print("   🌐 اختبار الاتصال بالخادم الخارجي (محسّن)...")

            test_payloads = [
                {
                    'text': message_text
                }
            ]
            headers = {'Content-Type': 'application/json'}

            for i, payload in enumerate(test_payloads, 1):
                print(f"   🧪 المحاولة {i}/3: {json.dumps(payload, ensure_ascii=False)[:50]}...")
                try:
                    response = requests.post(
                        self.config['EXTERNAL_SERVER_URL'],
                        json=payload,
                        headers=headers,
                        timeout=8,
                        verify=False
                    )
                    print(f"   📊 الاستجابة: {response.status_code}")
                    if response.status_code in [200, 201]:
                        print(f"   ✅ نجحت المحاولة {i}!")
                        return True
                    else:
                        print(f"   ❌ فشلت المحاولة {i}: {response.status_code} - {response.text[:100]}")
                except requests.exceptions.SSLError as ssl_error:
                    print(f"   🔒 خطأ SSL في المحاولة {i}: {ssl_error}")
                except requests.exceptions.ConnectionError as conn_error:
                    print(f"   🔌 خطأ اتصال في المحاولة {i}: {conn_error}")
                except requests.exceptions.Timeout as timeout_error:
                    print(f"   ⏰ انتهت المهلة في المحاولة {i}: {timeout_error}")
                except Exception as e:
                    print(f"   ❌ خطأ غير متوقع في المحاولة {i}: {e}")

            print("   🔄 محاولة طلب GET...")
            try:
                get_response = requests.get(
                    self.config['EXTERNAL_SERVER_URL'].replace('/sendMessage', ''),
                    timeout=5
                )
                print(f"   📊 استجابة GET: {get_response.status_code}")
                if get_response.status_code == 200:
                    print("   ⚠️  الخادم يعمل ولكن المسار قد يكون خاطئاً")
            except Exception as get_error:
                print(f"   ❌ فشل طلب GET: {get_error}")

            return False

        except Exception as e:
            print(f"   💥 فشل اختبار الاتصال تماماً: {e}")
            return False

    # =============================
    # مسارات الويب
    # =============================
    def setup_routes(self):
        """إعداد مسارات API"""

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
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        @self.app.route('/status')
        def status():
            return jsonify(self.get_system_status())

        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            return self.handle_webhook(request)

        @self.app.route('/test', methods=['GET', 'POST'])
        def test():
            return self.handle_test(request)

        @self.app.route('/test-telegram', methods=['GET', 'POST'])
        def test_telegram():
            return self.handle_test_telegram(request)

    # =============================
    # معالجة الإشارات
    # =============================
    def handle_webhook(self, request):
        """معالجة طلبات Webhook"""
        try:
            raw_signal = self.extract_signal_data(request)
            if not raw_signal:
                return jsonify({"status": "error", "message": "إشارة فارغة"}), 400

            self.logger.info(f"إشارة مستلمة: {raw_signal}")
            success = self.process_signal(raw_signal)

            if success:
                return jsonify({
                    "status": "success",
                    "message": "تم معالجة الإشارة بنجاح",
                    "signal": raw_signal
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "فشل في معالجة الإشارة"
                }), 400

        except Exception as e:
            self.logger.error(f"خطأ في Webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def extract_signal_data(self, request):
        """استخراج بيانات الإشارة من الطلب"""
        content_type = request.headers.get('Content-Type', '')

        if 'application/json' in content_type:
            data = request.get_json(silent=True)
            if data:
                return self.convert_json_to_signal(data)

        # محاولة قراءة نص خام
        raw = request.get_data(as_text=True)
        return raw.strip() if raw else ''

    def convert_json_to_signal(self, data):
        """تحويل JSON إلى إشارة نصية"""
        if isinstance(data, dict):
            ticker = data.get('ticker', data.get('symbol', 'UNKNOWN'))
            signal_type = data.get('signal', data.get('action', 'UNKNOWN'))
            open_price = str(data.get('open', '0'))
            close_price = str(data.get('close', '0'))
            return f"Ticker : {ticker} Signal : {signal_type} Open : {open_price} Close : {close_price}"
        return str(data)

    def process_signal(self, raw_signal):
        """المعالجة الرئيسية للإشارة"""
        signal_data = self.parse_signal(raw_signal)
        if not signal_data:
            self.logger.warning(f"إشارة غير صالحة: {raw_signal}")
            return False

        signal_category = self.classify_signal(signal_data)
        signal_data['category'] = signal_category

        self.logger.info(f"إشارة مصنفة: {signal_data['signal_type']} -> {signal_category}")

        if signal_category == 'trend':
            return self.handle_trend_signal(signal_data)
        elif signal_category == 'exit':
            return self.handle_exit_signal(signal_data)
        elif signal_category == 'trend_confirm':
            return self.handle_trend_confirmation(signal_data)
        elif signal_category == 'general':
            return self.handle_general_signal(signal_data)
        elif signal_category in ('entry_bullish', 'entry_bearish'):
            return self.handle_entry_signal(signal_data, signal_category)
        else:
            # غير معروف → تعامل كإشارة عامة فقط للتسجيل
            return self.handle_general_signal(signal_data)

    def parse_signal(self, raw_signal):
        """تحليل الإشارة إلى مكوناتها (صلابة أعلى)"""
        try:
            text = raw_signal.strip()
            if not text:
                return None

            # الصيغة القياسية
            pattern = r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+?)\s+Open\s*:\s*(.+?)\s+Close\s*:\s*(.+)'
            match = re.match(pattern, text)
            if match:
                ticker, signal_type, open_price, close_price = match.groups()
            else:
                # صيغة: "SPX500 | bullish_sbos_buy"
                if '|' in text:
                    parts = [p.strip() for p in text.split('|')]
                    if len(parts) >= 2:
                        ticker, signal_type = parts[0], parts[1]
                    else:
                        return None
                    open_price, close_price = "0", "0"
                else:
                    # إذا كانت مجرد اسم إشارة
                    ticker, signal_type = "BTCUSDT", text
                    open_price, close_price = "0", "0"

            # تنظيف NaN
            if 'NaN' in signal_type:
                signal_type = self.clean_nan_signal(signal_type, text) or ''
                if not signal_type:
                    return None

            return {
                'ticker': ticker.strip(),
                'signal_type': signal_type.strip(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'TradingView'
            }

        except Exception as e:
            self.logger.error(f"خطأ في تحليل الإشارة: {e}")
            return None

    def clean_nan_signal(self, signal_type, raw_signal):
        """تنظيف إشارات NaN"""
        s = raw_signal.lower()
        if 'bullish' in s:
            return 'bullish_trend'
        if 'bearish' in s:
            return 'bearish_trend'
        return None

    # =============================
    # تصنيف الإشارات
    # =============================
    def _normalize_signal_name(self, name: str) -> str:
        return re.sub(r'\s+', ' ', name.replace('_', ' ').replace('-', ' ').strip().lower())

    def classify_signal(self, signal_data):
        """تصنيف الإشارة مع تحسين السرعة والصلابة"""
        signal_type = self.clean_signal_type(signal_data['signal_type'])
        signal_data['signal_type'] = signal_type  # تحديث بالنظيف

        # 1) تطابق مباشر عبر الفهرس السريع
        ns = self._normalize_signal_name(signal_type)
        if ns in self.normalized_index:
            return self.normalized_index[ns]

        # 2) بعض القواعد العامة كباك أب
        ls = ns
        if 'bearish' in ls:
            return 'entry_bearish'
        if 'bullish' in ls:
            return 'entry_bullish'
        if 'trend' in ls:
            return 'trend'
        if 'exit' in ls or 'close' in ls or 'tp' in ls or 'sl' in ls:
            return 'exit'

        return 'general'

    def clean_signal_type(self, signal_type):
        """تنظيف نوع الإشارة"""
        cleaned = re.sub(r'\[.*?\]|\(.*?\)|\d+\.?\d*', '', signal_type)
        cleaned = ' '.join(cleaned.split()).strip()
        return cleaned

    # =============================
    # معالجات حسب الفئة
    # =============================
    def handle_trend_signal(self, signal_data):
        """معالجة إشارات الاتجاه - اتجاه منفصل لكل رمز"""
        signal_type = signal_data['signal_type']
        symbol = signal_data['ticker']

        if 'bullish' in signal_type.lower():
            new_trend = 'BULLISH'
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        elif 'bearish' in signal_type.lower():
            new_trend = 'BEARISH'
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        else:
            return False

        current_trend = self.symbol_trends.get(symbol)
        trend_changed = current_trend != new_trend
        self.symbol_trends[symbol] = new_trend

        # منع الإزعاج: لا تكرر نفس الإشعار لنفس الاتجاه خلال 60 ثانية
        should_notify = False
        last_sent = self.last_trend_notified_at.get(symbol)
        if trend_changed:
            should_notify = True
        else:
            if not last_sent or (datetime.now() - last_sent).total_seconds() > 60:
                should_notify = True

        if should_notify:
            message = self.format_trend_message(signal_data, trend_icon, trend_text)
            if self.should_send_message('trend', signal_data):
                self.send_telegram(message)
            self.send_to_external_server_with_retry(message, 'trend')
            self.last_trend_notifications[symbol] = new_trend
            self.last_trend_notified_at[symbol] = datetime.now()
            self.logger.info(f"إشعار اتجاه للرمز {symbol}: {new_trend}")

        # إغلاق صفقات هذا الرمز فقط إذا تغير الاتجاه
        if self.config['RESET_TRADES_ON_TREND_CHANGE'] and trend_changed and self.active_trades:
            closed_count = 0
            for trade_id in list(self.active_trades.keys()):
                trade = self.active_trades[trade_id]
                if trade['ticker'] == symbol and trade['status'] == 'OPEN':
                    trade.update({
                        'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'CLOSED',
                        'exit_signal': 'trend_change'
                    })
                    closed_count += 1
            if closed_count > 0:
                self.logger.info(f"إغلاق {closed_count} صفقة للرمز {symbol} بسبب تغيير الاتجاه")

        return True

    def handle_entry_signal(self, signal_data, signal_category):
        """معالجة إشارات الدخول - مع احترام اتجاه الرمز ومنع التكرار"""
        symbol = signal_data['ticker']

        # منع فتح أكثر من صفقة مفتوحة لنفس الرمز
        if self.find_active_trade(symbol):
            self.logger.warning(f"تجاهل فتح صفقة جديدة: توجد صفقة مفتوحة للرمز {symbol}")
            return False

        # التحقق من الحد الأقصى للصفقات
        active_trades_count = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        if active_trades_count >= self.config['MAX_OPEN_TRADES']:
            self.logger.warning("الحد الأقصى للصفقات مكتفي")
            return False

        # التحقق من مطابقة الاتجاه للرمز المحدد
        symbol_trend = self.symbol_trends.get(symbol)
        if self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and symbol_trend:
            if (signal_category == 'entry_bullish' and symbol_trend != 'BULLISH') or \
               (signal_category == 'entry_bearish' and symbol_trend != 'BEARISH'):
                self.logger.warning(f"الإشارة لا تتطابق مع الاتجاه الحالي للرمز {symbol}")
                return False

        # نظام التأكيد - إشارات مختلفة من نفس المجموعة خلال نافذة زمنية
        ticker = signal_data['ticker']
        signal_key = f"{ticker}_{signal_category}"

        self.clean_expired_signals()

        if signal_key not in self.pending_signals:
            self.pending_signals[signal_key] = {
                'unique_signals': set(),
                'signals_data': [],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'signal_category': signal_category
            }

        signal_type_clean = self.clean_signal_type(signal_data['signal_type'])
        group = self.pending_signals[signal_key]

        # التحقق من نافذة التأكيد (بين أول وآخر إشارة)
        now = datetime.now()
        if (now - group['created_at']).total_seconds() > self.config['CONFIRMATION_WINDOW']:
            # إعادة ضبط المجموعة إذا خرجت عن النافذة
            self.pending_signals[signal_key] = {
                'unique_signals': set(),
                'signals_data': [],
                'created_at': now,
                'updated_at': now,
                'signal_category': signal_category
            }
            group = self.pending_signals[signal_key]

        if signal_type_clean not in group['unique_signals']:
            group['unique_signals'].add(signal_type_clean)
            group['signals_data'].append(signal_data)
            group['updated_at'] = now
            self.logger.info(f"إشارة فريدة: {signal_data['signal_type']} للمجموعة {signal_category}")
        else:
            self.logger.info(f"تجاهل إشارة مكررة: {signal_data['signal_type']}")
            return True

        unique_count = len(group['unique_signals'])
        if unique_count >= self.config['REQUIRED_CONFIRMATIONS']:
            return self.open_confirmed_trade(signal_key, signal_category)
        else:
            current_signals = list(group['unique_signals'])
            self.logger.info(f"في انتظار التأكيد: {unique_count}/{self.config['REQUIRED_CONFIRMATIONS']} - الإشارات: {current_signals}")
            return True

    def clean_expired_signals(self):
        """تنظيف الإشارات المنتهية الصلاحية اعتمادًا على آخر تحديث"""
        current_time = datetime.now()
        expired_keys = []
        for signal_key, data in self.pending_signals.items():
            last = data.get('updated_at', data['created_at'])
            if (current_time - last).total_seconds() > self.config['CONFIRMATION_TIMEOUT']:
                expired_keys.append(signal_key)
        for key in expired_keys:
            del self.pending_signals[key]
            self.logger.info(f"تنظيف إشارات منتهية: {key}")

    def open_confirmed_trade(self, signal_key, signal_category):
        """فتح صفقة مؤكدة"""
        pending_data = self.pending_signals[signal_key]
        if len(pending_data['unique_signals']) < self.config['REQUIRED_CONFIRMATIONS']:
            self.logger.error(f"عدد الإشارات غير كافٍ: {len(pending_data['unique_signals'])}")
            return False

        main_signal_data = pending_data['signals_data'][0]
        trade_id = str(uuid.uuid4())[:8]
        direction = 'CALL' if signal_category == 'entry_bullish' else 'PUT'

        trade_info = {
            'trade_id': trade_id,
            'ticker': main_signal_data['ticker'],
            'direction': direction,
            'signal_type': main_signal_data['signal_type'],
            'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'OPEN',
            'confirmation_count': len(pending_data['unique_signals']),
            'confirmed_signals': list(pending_data['unique_signals'])
        }

        self.active_trades[trade_id] = trade_info

        message = self.format_entry_message(trade_info, pending_data)

        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            self.send_telegram(message)
        self.send_to_external_server_with_retry(message, 'entry')

        del self.pending_signals[signal_key]

        self.logger.info(f"فتح صفقة {direction} (#{trade_id}) بـ {trade_info['confirmation_count']} إشارات مختلفة: {list(pending_data['unique_signals'])}")
        return True

    def handle_exit_signal(self, signal_data):
        """معالجة إشارات الخروج"""
        trade = self.find_active_trade(signal_data['ticker'])
        if not trade:
            self.logger.warning(f"لا توجد صفقة نشطة للرمز {signal_data['ticker']}")
            return False

        trade.update({
            'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'CLOSED',
            'exit_signal': signal_data['signal_type']
        })

        message = self.format_exit_message(trade)

        if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
            self.send_telegram(message)
        self.send_to_external_server_with_retry(message, 'exit')

        self.logger.info(f"إغلاق صفقة #{trade['trade_id']}")
        return True

    def handle_trend_confirmation(self, signal_data):
        """معالجة تأكيد الاتجاه"""
        message = self.format_confirmation_message(signal_data)
        if self.should_send_message('confirmation', signal_data):
            self.send_telegram(message)
        self.send_to_external_server_with_retry(message, 'trend_confirmation')
        self.logger.info(f"تأكيد اتجاه: {signal_data['signal_type']}")
        return True

    def handle_general_signal(self, signal_data):
        """معالجة الإشارات العامة"""
        message = self.format_general_message(signal_data)
        if self.should_send_message('general', signal_data):
            self.send_telegram(message)
        self.send_to_external_server_with_retry(message, 'general')
        self.logger.info(f"إشارة عامة: {signal_data['signal_type']}")
        return True

    def find_active_trade(self, ticker):
        """البحث عن صفقة نشطة حسب الرمز"""
        for trade in self.active_trades.values():
            if trade['ticker'] == ticker and trade['status'] == 'OPEN':
                return trade
        return None

    # =============================
    # التحكم في الإرسال
    # =============================
    def should_send_message(self, message_type, signal_data=None):
        """التحقق مما إذا كان يجب إرسال الرسالة"""
        if not self.config['TELEGRAM_ENABLED']:
            print(f"🔕 Telegram معطل عالمياً لرسالة: {message_type}")
            return False

        type_controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }
        if not type_controls.get(message_type, False):
            print(f"🔕 إرسال رسائل {message_type} معطل في الإعدادات")
            return False

        if signal_data:
            signal_type = str(signal_data.get('signal_type', '')).lower()
            direction = signal_data.get('direction', '')
            if ('bullish' in signal_type or direction == 'CALL') and not self.config['SEND_BULLISH_SIGNALS']:
                print(f"🔕 إرسال الإشارات الصاعدة معطل")
                return False
            if ('bearish' in signal_type or direction == 'PUT') and not self.config['SEND_BEARISH_SIGNALS']:
                print(f"🔕 إرسال الإشارات الهابطة معطل")
                return False

        print(f"✅ السماح بإرسال رسالة: {message_type}")
        return True

    # =============================
    # الإرسال (مع الحفاظ على نفس قوالب الرسائل)
    # =============================
    def send_telegram(self, message):
        """إرسال رسالة إلى Telegram - يحافظ على نفس الشكل"""
        print(f"🔍 محاولة إرسال رسالة إلى Telegram...")

        if not self.config['TELEGRAM_ENABLED']:
            print("❌ إرسال Telegram معطل في الإعدادات (TELEGRAM_ENABLED = False)")
            return False

        if not self.config['TELEGRAM_BOT_TOKEN'] or self.config['TELEGRAM_BOT_TOKEN'] == 'your_bot_token_here':
            print(f"📲 محاكاة إرسال Telegram (التوكن غير مضبوط):\n{message}")
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
            print(f"🔗 محاولة الإرسال إلى: {url}")
            print(f"📨 محتوى الرسالة: {message[:100]}...")
            response = requests.post(url, json=payload, timeout=10)
            success = response.status_code == 200
            if success:
                print("✅ تم إرسال الرسالة إلى Telegram بنجاح!")
                self.logger.info("تم إرسال الرسالة إلى Telegram")
            else:
                print(f"❌ فشل إرسال Telegram: {response.status_code}")
                print(f"📋 تفاصيل الخطأ: {response.text}")
                self.logger.error(f"فشل إرسال Telegram: {response.status_code} - {response.text}")
            return success
        except Exception as e:
            print(f"❌ خطأ في إرسال Telegram: {e}")
            self.logger.error(f"خطأ في إرسال Telegram: {e}")
            return False

    def send_to_external_server(self, message_text, message_type):
        """إرسال نفس نص رسالة Telegram إلى الخادم الخارجي *حرفيًا* كـ RAW UTF-8
        - بدون JSON
        - بدون form-data
        - بدون مفاتيح إضافية
        - نفس النص تمامًا كما هو
        """
        if not self.config['EXTERNAL_SERVER_ENABLED']:
            return False
        if not self.config['EXTERNAL_SERVER_URL'] or self.config['EXTERNAL_SERVER_URL'] == 'https://api.example.com/webhook/trading':
            return False
        try:
            # نرسل النص الخام مباشرةً في جسم الطلب
            headers = {'Content-Type': 'text/plain; charset=utf-8'}
            response = requests.post(
                self.config['EXTERNAL_SERVER_URL'],
                data=message_text.encode('utf-8'),
                headers=headers,
                timeout=10,
                verify=False
            )
            if response.status_code in [200, 201, 204]:
                print("✅ تم الإرسال كنص خام (text/plain) مطابق 1:1")
                self.logger.info("تم إرسال الرسالة كنص خام إلى الخادم الخارجي")
                return True
            else:
                print(f"❌ الخادم الخارجي أعاد كود: {response.status_code}")
                try:
                    print(f"📋 الاستجابة: {response.text[:200]}")
                except Exception:
                    pass
                return False
        except Exception as e:
            print(f"💥 فشل إرسال النص الخام إلى الخادم الخارجي: {e}")
            return False

    def send_to_external_server_with_retry(self, message_text, message_type, max_retries=2):(self, message_text, message_type, max_retries=2):
        """إرسال مع إعادة المحاولة التلقائية"""
        for attempt in range(max_retries + 1):
            success = self.send_to_external_server(message_text, message_type)
            if success:
                return True
            elif attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"🔄 إعادة المحاولة بعد {wait_time} ثواني... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
        return False

    # =============================
    # قوالب الرسائل (بدون تغيير على الشكل المطلوب)
    # =============================
    def format_trend_message(self, signal_data, trend_icon, trend_text):
        return f"""
☰☰☰ 📊 الاتجاه العام ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {signal_data['ticker']}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal_data['signal_type']}
┃ 🔄 الحالة: الاتجاه العام محدث
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

    def format_entry_message(self, trade_info, confirmation_data):
        ticker = trade_info['ticker']
        direction = trade_info['direction']
        symbol_trend = self.symbol_trends.get(ticker, 'غير محدد')
        trend_match = symbol_trend == ('BULLISH' if direction == 'CALL' else 'BEARISH')

        if direction == 'CALL':
            direction_icon, direction_text = "🟢", "شراء"
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        else:
            direction_icon, direction_text = "🔴", "بيع"
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"

        confirm_count = len(confirmation_data['unique_signals'])
        secondary_signals = []
        main_signal = trade_info['signal_type']
        for s in confirmation_data['unique_signals']:
            if s != main_signal:
                secondary_signals.append(s)
        secondary_count = len(secondary_signals)

        secondary_listing = ""
        for i, s in enumerate(secondary_signals[:3], 1):
            clean_signal = s.replace('+', '').replace('-', '')
            secondary_listing += f"┃   {i}. {clean_signal}\n"
        if secondary_count > 3:
            secondary_listing += f"┃   ... و{secondary_count - 3} إشارات أخرى\n"
        elif secondary_count == 0:
            secondary_listing = "┃    - لا توجد إشارات مساعدة\n"

        open_trades = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        max_open_trades = self.config['MAX_OPEN_TRADES']
        main_signal_clean = main_signal.replace('+', '').replace('-', '')
        alignment_status = "🟢 مطابق للاتجاه العام" if trend_match else "🟡 غير متطابق مع الاتجاه"

        message = f"""
✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {ticker}
┃ 🎯 نوع الصفقة: {direction_icon} {direction_text}
┃ 📊 اتجاه الرمز: {trend_icon} {symbol_trend if symbol_trend else 'غير محدد'}
┃ 🎯 محاذاة الاتجاه: {alignment_status}
┃ 📋 الإشارة الرئيسية: {main_signal_clean} (تم التأكيد بـ {confirm_count} إشارات)
┃ 🔔 الإشارات المساعدة: {secondary_count} إشارة
{secondary_listing}┃ 📊 الصفقات المفتوحة: {open_trades} من {max_open_trades}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
        """.strip()
        return message

    def format_exit_message(self, trade_info):
        if trade_info['direction'] == 'CALL':
            direction_icon, direction_text = "🟢", "شراء (CALL)"
        else:
            direction_icon, direction_text = "🔴", "بيع (PUT)"
        clean_exit_signal = trade_info['exit_signal'].replace('_', ' ')
        open_trades = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        return f"""
════ 🚪 إشـــــــارة خــــــروج ════
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {trade_info['ticker']}
┃ 📝 السبب: إشارة خروج: {clean_exit_signal}
┃ 🎯 نوع الصفقة المغلقة: {direction_icon} {direction_text}
┃ 📊 الصفقات المفتوحة: {open_trades}/{self.config['MAX_OPEN_TRADES']}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
        """.strip()

    def format_confirmation_message(self, signal_data):
        symbol_trend = self.symbol_trends.get(signal_data['ticker'], 'غير محدد')
        if symbol_trend == 'BULLISH' or 'bullish' in signal_data['signal_type'].lower():
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        elif symbol_trend == 'BEARISH' or 'bearish' in signal_data['signal_type'].lower():
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        else:
            trend_icon, trend_text = "⚪", "محايد"
        clean_signal = signal_data['signal_type'].replace('+', '').replace('-', '')
        return f"""
✅ 📊 تأكيـــــد الاتجــــاه 📊 ✅
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {signal_data['ticker']}
┃ 📈 الاتجاه المؤكد: {trend_icon} {trend_text}
┃ 📋 الإشارة: {clean_signal}
┃ ✅ الحالة: تأكيد مطابقة الاتجاه العام
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
        """.strip()

    def format_general_message(self, signal_data):
        clean_signal = signal_data['signal_type'].replace('+', '').replace('-', '')
        return f"""
☰☰☰ 🔔 إشارة جديدة ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {signal_data['ticker']}
┃ 📈 نوع الإشارة: {signal_data.get('category', 'عام')}
┃ 📋 الإشارة: {clean_signal}
┃ 📍 الحالة: مراقبة
┗━━━━━━━━━━━━━━━━━━━━
🕐 {signal_data['timestamp']}
        """.strip()

    # =============================
    # الحالة والاختبارات
    # =============================
    def get_system_status(self):
        active_trades = [t for t in self.active_trades.values() if t['status'] == 'OPEN']
        return {
            "status": "operational",
            "app_name": self.config['APP_NAME'],
            "app_version": self.config['APP_VERSION'],
            "active_trades": len(active_trades),
            "max_open_trades": self.config['MAX_OPEN_TRADES'],
            "pending_signals": len(self.pending_signals),
            "symbol_trends": self.symbol_trends,
            "trends_count": len(self.symbol_trends),
            "required_confirmations": self.config['REQUIRED_CONFIRMATIONS'],
            "telegram_enabled": self.config['TELEGRAM_ENABLED'],
            "external_server_enabled": self.config['EXTERNAL_SERVER_ENABLED'],
            "message_controls": {
                "SEND_TREND_MESSAGES": self.config['SEND_TREND_MESSAGES'],
                "SEND_ENTRY_MESSAGES": self.config['SEND_ENTRY_MESSAGES'],
                "SEND_EXIT_MESSAGES": self.config['SEND_EXIT_MESSAGES'],
                "SEND_CONFIRMATION_MESSAGES": self.config['SEND_CONFIRMATION_MESSAGES'],
                "SEND_GENERAL_MESSAGES": self.config['SEND_GENERAL_MESSAGES'],
                "SEND_BULLISH_SIGNALS": self.config['SEND_BULLISH_SIGNALS'],
                "SEND_BEARISH_SIGNALS": self.config['SEND_BEARISH_SIGNALS']
            },
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def display_loaded_signals(self):
        print("📋 الإشارات المحملة من ملف .env:")
        total_signals = 0
        for category, signals in self.signals.items():
            print(f"   {category}: {len(signals)} إشارة")
            total_signals += len(signals)
        print(f"   📈 الإجمالي: {total_signals} إشارة")

        print("\n⚙️  الإعدادات المحملة:")
        print(f"   🔔 إشعارات الاتجاه: {'مفعّل' if self.config['SEND_TREND_MESSAGES'] else 'معطل'}")
        print(f"   🔔 إشعارات الدخول: {'مفعّل' if self.config['SEND_ENTRY_MESSAGES'] else 'معطل'}")
        print(f"   🔔 إشعارات الخروج: {'مفعّل' if self.config['SEND_EXIT_MESSAGES'] else 'معطل'}")
        print(f"   🔔 إشعارات عامة: {'مفعّل' if self.config['SEND_GENERAL_MESSAGES'] else 'معطل'}")
        print(f"   📊 التأكيدات المطلوبة: {self.config['REQUIRED_CONFIRMATIONS']} إشارات مختلفة من نفس المجموعة")
        print(f"   📈 الحد الأقصى للصفقات: {self.config['MAX_OPEN_TRADES']}")
        print(f"   🎯 نظام اتجاه منفصل لكل رمز: مفعّل")
        print(f"   🌐 الخادم الخارجي: {'مفعّل' if self.config['EXTERNAL_SERVER_ENABLED'] else 'معطل'}")
        if self.config['EXTERNAL_SERVER_ENABLED']:
            print(f"   🔗 رابط الخادم: {self.config['EXTERNAL_SERVER_URL']}")

    def handle_test(self, request):
        if request.method == 'GET':
            return '''
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <title>اختبار نظام إشارات التداول</title>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                    textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; }
                    button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
                    .status { margin-top: 20px; padding: 15px; border-radius: 5px; }
                    .success { background: #d4edda; color: #155724; }
                    .error { background: #f8d7da; color: #721c24; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🧪 اختبار نظام إشارات التداول</h1>
                    <p><strong>🎯 النظام يدعم الآن اتجاه منفصل لكل رمز</strong></p>
                    <form method="POST">
                        <textarea name="signal" placeholder="Ticker : BTCUSDT Signal : bullish_catcher Open : 0 Close : 0" required>Ticker : SPX500 Signal : Bearish New Imbalance Open : 0 Close : 0</textarea>
                        <br>
                        <button type="submit">إرسال الإشارة</button>
                    </form>
                    <div>
                        <h3>📊 اتجاهات الرموز الحالية:</h3>
                        <pre id="trends"></pre>
                    </div>
                </div>
                <script>
                    function updateTrends() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                const trends = data.symbol_trends || {};
                                const trendsElement = document.getElementById('trends');
                                if (Object.keys(trends).length === 0) {
                                    trendsElement.innerHTML = 'لا توجد اتجاهات مسجلة';
                                } else {
                                    trendsElement.innerHTML = JSON.stringify(trends, null, 2);
                                }
                            });
                    }
                    setInterval(updateTrends, 5000);
                    updateTrends();
                </script>
            </body>
            </html>
            '''
        else:
            signal = request.form.get('signal', '')
            success = self.process_signal(signal)
            if success:
                return f'''
                <div class="status success">
                    <h3>✅ تمت المعالجة بنجاح!</h3>
                    <p><strong>الإشارة:</strong> {signal}</p>
                </div>
                <a href="/test">⟲ اختبار إشارة أخرى</a>
                '''
            else:
                return f'''
                <div class="status error">
                    <h3>❌ فشل في المعالجة</h3>
                    <p><strong>الإشارة:</strong> {signal}</p>
                </div>
                <a href="/test">⟲ محاولة مرة أخرى</a>
                '''

    def handle_test_telegram(self, request):
        if request.method == 'GET':
            return '''
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <title>اختبار Telegram مباشر</title>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
                    textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; }
                    button { padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; cursor: pointer; }
                    .test-btn { background: #28a745; }
                    .status { margin-top: 20px; padding: 15px; border-radius: 5px; }
                    .success { background: #d4edda; color: #155724; }
                    .error { background: #f8d7da; color: #721c24; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🧪 اختبار Telegram مباشر</h1>
                    <div>
                        <button class="test-btn" onclick="testConnection()">🔗 اختبار الاتصال</button>
                        <button class="test-btn" onclick="testTrendMessage()">📊 اختبار رسالة اتجاه</button>
                        <button class="test-btn" onclick="testEntryMessage()">🚀 اختبار رسالة دخول</button>
                    </div>
                    <div id="result"></div>
                </div>
                <script>
                    function testConnection() {
                        fetch('/test-telegram', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({test_type: 'connection'})
                        })
                        .then(r => r.json())
                        .then(data => showResult(data));
                    }
                    function testTrendMessage() {
                        fetch('/test-telegram', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({test_type: 'trend'})
                        })
                        .then(r => r.json())
                        .then(data => showResult(data));
                    }
                    function testEntryMessage() {
                        fetch('/test-telegram', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({test_type: 'entry'})
                        })
                        .then(r => r.json())
                        .then(data => showResult(data));
                    }
                    function showResult(data) {
                        const resultDiv = document.getElementById('result');
                        if (data.success) {
                            resultDiv.innerHTML = `<div class="status success"><h3>✅ ${data.message}</h3><pre>${data.details || ''}</pre></div>`;
                        } else {
                            resultDiv.innerHTML = `<div class="status error"><h3>❌ ${data.message}</h3><pre>${data.details || ''}</pre></div>`;
                        }
                    }
                </script>
            </body>
            </html>
            '''
        else:
            data = request.get_json()
            test_type = data.get('test_type', 'connection')

            if test_type == 'connection':
                success = self.test_telegram_connection()
                if success:
                    return jsonify({
                        "success": True,
                        "message": "الاتصال بـ Telegram ناجح",
                        "details": f"البوت: {self.config['TELEGRAM_BOT_TOKEN'][:10]}...\nالدردشة: {self.config['TELEGRAM_CHAT_ID']}"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": "فشل الاتصال بـ Telegram",
                        "details": "تحقق من التوكن ورقم الدردشة"
                    })

            elif test_type == 'trend':
                test_signal = {
                    'ticker': 'BTCUSDT',
                    'signal_type': 'bullish_catcher',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                message = self.format_trend_message(test_signal, "🟢📈", "شراء (اتجاه صاعد)")
                success = self.send_telegram(message)
                return jsonify({
                    "success": success,
                    "message": "تم إرسال رسالة الاتجاه التجريبية" if success else "فشل إرسال رسالة الاتجاه",
                    "details": message if success else "تحقق من إعدادات Telegram"
                })

            elif test_type == 'entry':
                test_trade = {
                    'trade_id': 'TEST123',
                    'ticker': 'BTCUSDT',
                    'direction': 'CALL',
                    'signal_type': 'bullish_sbos_buy',
                    'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'OPEN',
                    'confirmation_count': 3
                }
                test_confirmation = {
                    'unique_signals': {'bullish_sbos_buy', 'bullish_confirmation', 'bullish_moneyflow_co_50'},
                    'signals_data': [test_trade]
                }
                message = self.format_entry_message(test_trade, test_confirmation)
                success = self.send_telegram(message)
                return jsonify({
                    "success": success,
                    "message": "تم إرسال رسالة الدخول التجريبية" if success else "فشل إرسال رسالة الدخول",
                    "details": message if success else "تحقق من إعدادات Telegram"
                })

    # =============================
    # التشغيل
    # =============================
    def run(self):
        self.logger.info(f"بدء التشغيل على المنفذ {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=self.config['DEBUG'])

# إنشاء النظام وتعيين app لكائن Flask
system = TradingSystem()
app = system.app

if __name__ == '__main__':
    system.run()
