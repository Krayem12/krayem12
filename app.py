#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AbuRayan_Bot_V8.9_Controlled_Trades.py
نظام معالجة إشارات التداول - تحكم كامل بعدد الصفقات مع استراتيجية المجموعتين
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
    """النظام الرئيسي المدمج لإشارات التداول مع تحكم كامل في الصفقات واستراتيجية المجموعتين"""

    def __init__(self):
        print("🚀 بدء تهيئة نظام التداول...")
        self.setup_config()
        self.setup_managers()
        self.setup_flask()
        self.display_loaded_signals()
        self.check_settings()

        print(f"🚀 نظام معالجة الإشارات جاهز - المنفذ {self.port}")
        print(f"✅ التأكيد المطلوب: {self.config['REQUIRED_CONFIRMATIONS']} إشارات مختلفة من نفس المجموعة")
        print(f"📊 الحد الأقصى للصفقات: {self.config['MAX_OPEN_TRADES']}")
        print(f"🎯 الحد الأقصى لكل رمز: {self.config['MAX_TRADES_PER_SYMBOL']}")
        print(f"🔒 إغلاق الصفقات عند تغيير الاتجاه: {'مفعّل' if self.config['RESET_TRADES_ON_TREND_CHANGE'] else 'معطل'}")
        
        # 🆕 عرض إعدادات الاستراتيجية المزدوجة
        if self.config['DUAL_CONFIRMATION_STRATEGY']:
            print(f"🎯 استراتيجية المجموعتين: مفعّلة")
            print(f"   • المجموعة الأولى: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']} إشارة")
            print(f"   • المجموعة الثانية: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']} إشارة")
            print(f"   • وقت التأكيد: {self.config['DUAL_CONFIRMATION_TIMEOUT']} ثانية")

    # =============================
    # الإعدادات والتهيئة - بتسلسل صحيح
    # =============================
    def setup_config(self):
        """إعداد التكوين الكامل من .env"""
        print("⚙️ جاري تحميل الإعدادات...")
        
        self.config = {
            # 🔧 أساسي
            'APP_NAME': config('APP_NAME', default='TradingSignalProcessor'),
            'APP_VERSION': config('APP_VERSION', default='8.9.0'),
            'DEBUG': config('DEBUG', default=False, cast=bool),
            'LOG_LEVEL': config('LOG_LEVEL', default='INFO'),
            'LOG_FILE': config('LOG_FILE', default='app.log'),

            # 📱 Telegram
            'TELEGRAM_ENABLED': config('TELEGRAM_ENABLED', default=True, cast=bool),
            'TELEGRAM_BOT_TOKEN': config('TELEGRAM_BOT_TOKEN', default='your_bot_token_here'),
            'TELEGRAM_CHAT_ID': config('TELEGRAM_CHAT_ID', default='your_chat_id_here'),

            # 🌐 الخادم الخارجي
            'EXTERNAL_SERVER_ENABLED': config('EXTERNAL_SERVER_ENABLED', default=True, cast=bool),
            'EXTERNAL_SERVER_URL': config('EXTERNAL_SERVER_URL', default='https://api.example.com/webhook/trading'),
            'EXTERNAL_SERVER_TOKEN': config('EXTERNAL_SERVER_TOKEN', default=''),

            # ⚙️ التأكيد وإدارة الصفقات
            'REQUIRED_CONFIRMATIONS': config('REQUIRED_CONFIRMATIONS', default=3, cast=int),
            'CONFIRMATION_TIMEOUT': config('CONFIRMATION_TIMEOUT', default=1200, cast=int),
            'MAX_OPEN_TRADES': config('MAX_OPEN_TRADES', default=10, cast=int),
            'MAX_TRADES_PER_SYMBOL': config('MAX_TRADES_PER_SYMBOL', default=1, cast=int),
            'RESPECT_TREND_FOR_REGULAR_TRADES': config('RESPECT_TREND_FOR_REGULAR_TRADES', default=True, cast=bool),
            'RESET_TRADES_ON_TREND_CHANGE': config('RESET_TRADES_ON_TREND_CHANGE', default=True, cast=bool),

            # 🆕 🔥 إعدادات الاستراتيجية المزدوجة - المجموعتين
            'DUAL_CONFIRMATION_STRATEGY': config('DUAL_CONFIRMATION_STRATEGY', default=False, cast=bool),
            'REQUIRED_CONFIRMATIONS_GROUP1': config('REQUIRED_CONFIRMATIONS_GROUP1', default=2, cast=int),
            'REQUIRED_CONFIRMATIONS_GROUP2': config('REQUIRED_CONFIRMATIONS_GROUP2', default=1, cast=int),
            'DUAL_CONFIRMATION_TIMEOUT': config('DUAL_CONFIRMATION_TIMEOUT', default=1800, cast=int),

            # 🔔 تحكم الإرسال
            'SEND_TREND_MESSAGES': config('SEND_TREND_MESSAGES', default=True, cast=bool),
            'SEND_ENTRY_MESSAGES': config('SEND_ENTRY_MESSAGES', default=True, cast=bool),
            'SEND_EXIT_MESSAGES': config('SEND_EXIT_MESSAGES', default=True, cast=bool),
            'SEND_CONFIRMATION_MESSAGES': config('SEND_CONFIRMATION_MESSAGES', default=True, cast=bool),
            'SEND_GENERAL_MESSAGES': config('SEND_GENERAL_MESSAGES', default=False, cast=bool),
            'SEND_BULLISH_SIGNALS': config('SEND_BULLISH_SIGNALS', default=True, cast=bool),
            'SEND_BEARISH_SIGNALS': config('SEND_BEARISH_SIGNALS', default=True, cast=bool),

            # 🔐 إعدادات الأمان
            'ALLOWED_IPS': config('ALLOWED_IPS', default=''),
        }

        self.port = config('PORT', default=10000, cast=int)
        print(f"📡 المنفذ المضبوط: {self.port}")

        # 🔄 الترتيب الصحيح: أولاً تحميل الإشارات، ثم الكلمات المفتاحية، ثم الفهرس
        print("📥 جاري تحميل قوائم الإشارات...")
        self.signals = {
            'trend': self._load_signal_list('TREND_SIGNALS'),
            'trend_confirm': self._load_signal_list('TREND_CONFIRM_SIGNALS'),
            'entry_bullish': self._load_signal_list('ENTRY_SIGNALS_BULLISH'),
            'entry_bearish': self._load_signal_list('ENTRY_SIGNALS_BEARISH'),
            'exit': self._load_signal_list('EXIT_SIGNALS'),
            'general': self._load_signal_list('GENERAL_SIGNALS')
        }

        # 🆕 تحميل الإشارات للمجموعة الثانية
        print("📥 جاري تحميل قوائم الإشارات للمجموعة الثانية...")
        self.signals['entry_bullish1'] = self._load_signal_list('ENTRY_SIGNALS_BULLISH1')
        self.signals['entry_bearish1'] = self._load_signal_list('ENTRY_SIGNALS_BEARISH1')

        print("🔧 جاري إعداد الكلمات المفتاحية...")
        self.setup_custom_keywords()

        print("🔍 جاري إنشاء الفهرس المرن...")
        self.setup_flexible_index()

    def _load_signal_list(self, key):
        """تحميل الإشارات مع معالجة خاصة"""
        try:
            signal_str = config(key, default='')
            if not signal_str:
                return []
            
            signals = [s.strip() for s in signal_str.split(',') if s.strip()]
            print(f"   ✅ {key}: {len(signals)} إشارة")
            return signals
            
        except Exception as e:
            print(f"   ❌ خطأ في تحميل {key}: {e}")
            return []

    def setup_custom_keywords(self):
        """إعداد الكلمات المفتاحية القابلة للتخصيص"""
        print("   🔑 جاري تحميل الكلمات المفتاحية المخصصة...")
        
        # 🔥 التعديل: فصل الكلمات المفتاحية للاتجاه عن تأكيد الاتجاه
        default_bullish = ['bullish', 'buy', 'up', 'long', 'oversold']
        default_bearish = ['bearish', 'sell', 'down', 'short', 'overbought'] 
        default_trend = ['catcher', 'ichoch', 'trend']  # 🔥 إزالة tracer من الاتجاه
        default_trend_confirm = ['tracer', 'confirmation']  # 🔥 إضافة كلمات تأكيد الاتجاه
        default_exit = ['exit', 'close', 'take_profit', 'stop_loss']
        
        self.custom_keywords = {
            'bullish': default_bullish,
            'bearish': default_bearish,
            'trend': default_trend,
            'trend_confirm': default_trend_confirm,  # 🔥 إضافة فئة جديدة
            'exit': default_exit
        }
        
        print(f"   ✅ الكلمات المفتاحية جاهزة: {len(self.custom_keywords)} فئة")
        print(f"   🔍 كلمات الاتجاه: {default_trend}")
        print(f"   🔍 كلمات تأكيد الاتجاه: {default_trend_confirm}")

    def setup_flexible_index(self):
        """إعداد فهرس مرن للإشارات مع كلمات مفتاحية"""
        print("   🔍 جاري بناء الفهرس المرن...")
        self.flexible_index = {}
        self.keyword_index = {}
        
        total_signals = 0
        for category, signals in self.signals.items():
            total_signals += len(signals)
            for signal in signals:
                # الفهرس التام (الأصلي)
                self.flexible_index[signal] = category
                
                # الفهرس المرن (بدون مسافات وحروف صغيرة)
                normalized = self.normalize_signal(signal)
                self.flexible_index[normalized] = category
                
                # فهرس الكلمات المفتاحية
                keywords = self.extract_keywords(signal)
                for keyword in keywords:
                    if keyword not in self.keyword_index:
                        self.keyword_index[keyword] = []
                    self.keyword_index[keyword].append((category, signal))
        
        print(f"   ✅ الفهرس المرن جاهز: {len(self.flexible_index)} إدخال من {total_signals} إشارة")
        print(f"   🔑 فهرس الكلمات المفتاحية: {len(self.keyword_index)} كلمة مفتاحية")

    def normalize_signal(self, signal):
        """تطبيع الإشارة للمقارنة المرنة"""
        normalized = signal.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized_no_spaces = normalized.replace(' ', '')
        return normalized_no_spaces

    def extract_keywords(self, signal):
        """استخراج الكلمات المفتاحية من الإشارة باستخدام القائمة المخصصة"""
        signal_lower = signal.lower()
        keywords = set()
        
        # استخدام الكلمات المفتاحية المخصصة
        for category, word_list in self.custom_keywords.items():
            for keyword in word_list:
                if keyword.lower() in signal_lower:
                    keywords.add(keyword.lower())
        
        # إضافة الإشارة المطبعة
        normalized = self.normalize_signal(signal)
        keywords.add(normalized)
        
        return list(keywords)

    def display_loaded_signals(self):
        """عرض تفصيلي للإشارات المحملة"""
        print("\n📊 الإشارات المحملة:")
        for category, signals in self.signals.items():
            print(f"   📁 {category}: {len(signals)} إشارة")
        
        # 🆕 عرض إعدادات الاستراتيجية المزدوجة
        if self.config['DUAL_CONFIRMATION_STRATEGY']:
            print("\n🎯 استراتيجية المجموعتين:")
            print(f"   • المجموعة الأولى (دخول): {self.config['REQUIRED_CONFIRMATIONS_GROUP1']} إشارة")
            print(f"   • المجموعة الثانية (تأكيد): {self.config['REQUIRED_CONFIRMATIONS_GROUP2']} إشارة")
            print(f"   • وقت الانتهاء: {self.config['DUAL_CONFIRMATION_TIMEOUT']} ثانية")

    def setup_managers(self):
        """إعداد المدراء والمتغيرات الأساسية"""
        print("👥 جاري تهيئة المدراء...")
        self.pending_signals = {}
        self.active_trades = {}
        self.symbol_trends = {}
        self.last_trend_notifications = {}
        self.last_trend_notified_at = {}
        self.signal_history = []

    def setup_flask(self):
        """إعداد تطبيق Flask"""
        print("🌐 جاري إعداد خادم الويب...")
        self.app = Flask(__name__)
        self.setup_routes()
        self.setup_logging()

    def setup_logging(self):
        """إعداد نظام التسجيل"""
        print("📝 جاري إعداد نظام التسجيل...")
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('trading_system')
        self.logger.setLevel(getattr(logging, self.config['LOG_LEVEL'], logging.INFO))
        
        # تنظيف المعالجات السابقة
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)

        fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 🔥 إصلاح مشكلة ملف السجل - استخدام المسار الحالي بدلاً من system32
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(current_dir, self.config['LOG_FILE'])
        
        try:
            # التأكد من وجود المجلد
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            
            fh = logging.FileHandler(log_file_path, encoding='utf-8')
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)
            print(f"   ✅ ملف السجل: {log_file_path}")
        except Exception as e:
            print(f"   ⚠️ تعذر إنشاء ملف السجل: {e}")
            print("   📝 سيتم استخدام التسجيل في الكونسول فقط")

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        self.logger.addHandler(sh)

    # =============================
    # الأمان والتحقق
    # =============================

    def safe_get_token(self, token_name):
        """استخراج التوكن بشكل آمن مع التحقق من الصحة"""
        token = self.config.get(token_name, '')
        
        if not token:
            self.logger.error(f"❌ التوكن {token_name} فارغ")
            return None
            
        forbidden_values = ['', 'your_bot_token_here', 'your_chat_id_here', 'undefined', 'none']
        if token.lower() in forbidden_values:
            self.logger.error(f"❌ التوكن {token_name} غير مضبوط بشكل صحيح")
            return None
            
        return token

    def validate_signal_source(self, request):
        """التحقق من مصدر الإشارة - مقبول لجميع IPs"""
        client_ip = self.get_client_ip(request)
        print(f"✅ قبول الإشارة من IP: {client_ip}")
        return True

    def get_client_ip(self, request):
        """استخراج IP العميل الحقيقي مع دعم reverse proxy"""
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
            return ip
        
        return request.remote_addr or 'UNKNOWN'

    def validate_signal_content(self, raw_signal):
        """التحقق من محتوى الإشارة لمنع الهجمات"""
        if not raw_signal or len(raw_signal.strip()) == 0:
            return False
            
        if len(raw_signal) > 10000:
            self.logger.warning(f"إشارة كبيرة جداً: {len(raw_signal)} حرف")
            return False
            
        injection_patterns = [
            r';.*DROP', r';.*DELETE', r';.*UPDATE',
            r'<script>', r'javascript:', r'onload=', r'onerror='
        ]
        
        signal_lower = raw_signal.lower()
        for pattern in injection_patterns:
            if re.search(pattern, signal_lower, re.IGNORECASE):
                self.logger.warning(f"محتوى خطير مكتشف في الإشارة: {pattern}")
                return False
                
        return True

    # =============================
    # تشخيص الشبكة والإعدادات
    # =============================
    def check_settings(self):
        """فحص شامل للإعدادات"""
        print("\n🔍 فحص الإعدادات:")
        
        print("📊 إدارة الصفقات:")
        print(f"   • الحد الأقصى للصفقات: {self.config['MAX_OPEN_TRADES']}")
        print(f"   • الحد الأقصى لكل رمز: {self.config['MAX_TRADES_PER_SYMBOL']}")
        
        # 🆕 عرض إعدادات الاستراتيجية المزدوجة
        if self.config['DUAL_CONFIRMATION_STRATEGY']:
            print("🎯 استراتيجية المجموعتين:")
            print(f"   • المجموعة الأولى: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']} إشارة")
            print(f"   • المجموعة الثانية: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']} إشارة")
            print(f"   • وقت التأكيد: {self.config['DUAL_CONFIRMATION_TIMEOUT']} ثانية")
        else:
            print(f"   • التأكيدات المطلوبة: {self.config['REQUIRED_CONFIRMATIONS']}")
        
        print(f"   • إغلاق الصفقات عند تغيير الاتجاه: {'مفعّل' if self.config['RESET_TRADES_ON_TREND_CHANGE'] else 'معطل'}")
        
        print("🔔 الإشعارات:")
        print(f"   • إشعارات الاتجاه: {'مفعّل' if self.config['SEND_TREND_MESSAGES'] else 'معطل'}")
        print(f"   • إشعارات الدخول: {'مفعّل' if self.config['SEND_ENTRY_MESSAGES'] else 'معطل'}")
        print(f"   • إشعارات الخروج: {'مفعّل' if self.config['SEND_EXIT_MESSAGES'] else 'معطل'}")
        print(f"   • تأكيدات الاتجاه: {'مفعّل' if self.config['SEND_CONFIRMATION_MESSAGES'] else 'معطل'}")

        # اختبار Telegram
        if self.config['TELEGRAM_ENABLED']:
            print("📱 اختبار Telegram...")
            if self.test_telegram_connection():
                print("   ✅ اتصال Telegram ناجح")
            else:
                print("   ❌ اتصال Telegram فاشل")

        # اختبار الخادم الخارجي
        if self.config['EXTERNAL_SERVER_ENABLED']:
            print("🌐 اختبار الخادم الخارجي...")
            if self.test_external_server_connection():
                print("   ✅ اتصال الخادم الخارجي ناجح")
            else:
                print("   ❌ اتصال الخادم الخارجي فاشل")

    def test_telegram_connection(self):
        """اختبار اتصال Telegram"""
        try:
            token = self.safe_get_token('TELEGRAM_BOT_TOKEN')
            if not token:
                return False
                
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ فشل اختبار Telegram: {e}")
            return False

    def test_external_server_connection(self):
        """اختبار اتصال الخادم الخارجي"""
        try:
            response = requests.post(
                self.config['EXTERNAL_SERVER_URL'],
                data="test".encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=8,
                verify=False
            )
            return response.status_code in (200, 201, 204)
        except Exception as e:
            print(f"❌ فشل اختبار الخادم الخارجي: {e}")
            return False

    # =============================
    # مسارات الويب
    # =============================
    def setup_routes(self):
        """إعداد مسارات Flask"""
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
        """الحصول على حالة النظام الحالية"""
        trades_per_symbol = {}
        for trade in self.active_trades.values():
            if trade['status'] == 'OPEN':
                symbol = trade['ticker']
                trades_per_symbol[symbol] = trades_per_symbol.get(symbol, 0) + 1

        return {
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "open_trades": len([t for t in self.active_trades.values() if t['status'] == 'OPEN']),
            "max_open_trades": self.config['MAX_OPEN_TRADES'],
            "max_trades_per_symbol": self.config['MAX_TRADES_PER_SYMBOL'],
            "trades_per_symbol": trades_per_symbol,
            "pending_groups": len(self.pending_signals),
            'trends': self.symbol_trends,
            "signal_history_count": len(self.signal_history),
            "dual_confirmation_strategy": self.config['DUAL_CONFIRMATION_STRATEGY']
        }

    # =============================
    # معالجة الإشارات
    # =============================
    def handle_webhook(self, request):
        """معالجة طلبات Webhook"""
        try:
            client_ip = self.get_client_ip(request)
            print(f"🌐 إشارة مستلمة من IP: {client_ip}")

            raw_signal = self.extract_signal_data(request)
            
            if not self.validate_signal_content(raw_signal):
                return jsonify({"status": "error", "message": "محتوى الإشارة غير صالح"}), 400
                
            if not raw_signal:
                return jsonify({"status": "error", "message": "إشارة فارغة"}), 400

            self.logger.info(f"إشارة مستلمة: {raw_signal}")
            
            # تسجيل الإشارة في التاريخ
            self.record_signal_history(raw_signal, client_ip)
            
            success = self.process_signal(raw_signal)

            if success:
                return jsonify({"status": "success", "message": "ok"})
            else:
                return jsonify({"status": "error", "message": "لم تُفتح صفقة/لم تُرسل رسالة"}), 400

        except Exception as e:
            self.logger.error(f"خطأ في Webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def record_signal_history(self, raw_signal, client_ip):
        """تسجيل الإشارة في سجل التاريخ"""
        signal_record = {
            'timestamp': datetime.now(),
            'signal': raw_signal[:100],
            'client_ip': client_ip,
            'processed': False
        }
        self.signal_history.append(signal_record)
        
        # الحفاظ على آخر 500 إشارة فقط
        if len(self.signal_history) > 500:
            self.signal_history = self.signal_history[-500:]

    def extract_signal_data(self, request):
        """إخراج نص الإشارة من JSON أو نص خام"""
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            data = request.get_json(silent=True)
            if data:
                return self.convert_json_to_signal(data)
        
        raw = request.get_data(as_text=True)
        return raw.strip() if raw else ''

    def convert_json_to_signal(self, data):
        """تحويل بيانات JSON إلى إشارة نصية"""
        if isinstance(data, dict):
            ticker = data.get('ticker', data.get('symbol', 'UNKNOWN'))
            signal_type = data.get('signal', data.get('action', 'UNKNOWN'))
            return f"Ticker : {ticker} Signal : {signal_type}"
        return str(data)

    def process_signal(self, raw_signal):
        """معالجة الإشارة الرئيسية"""
        signal_data = self.parse_signal(raw_signal)
        if not signal_data:
            self.logger.warning(f"إشارة غير صالحة: {raw_signal}")
            return False

        category = self.classify_signal_flexible(signal_data)
        signal_data['category'] = category

        # تحديث حالة الإشارة في السجل
        for record in self.signal_history[-5:]:
            if record['signal'].startswith(raw_signal[:50]):
                record['processed'] = True
                record['category'] = category
                break

        if category == 'trend':
            return self.handle_trend_signal(signal_data)
        elif category == 'trend_confirm':
            return self.handle_trend_confirmation(signal_data)
        elif category == 'unknown':
            return self.handle_unknown_signal(signal_data)
        elif category == 'exit':
            return self.handle_exit_signal(signal_data)
        elif category in ('entry_bullish', 'entry_bearish', 'entry_bullish1', 'entry_bearish1'):
            return self.handle_entry_signal(signal_data, category)
        else:
            return self.handle_general_signal(signal_data)

    def parse_signal(self, raw_signal):
        """تحليل محسّن لنص الإشارة"""
        try:
            text = raw_signal.strip()
            if not text:
                return None
            
            # النمط الأساسي: Ticker : SYMBOL Signal : SIGNAL_TYPE
            pattern = r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+)'
            match = re.match(pattern, text)
            if match:
                ticker, signal_type = match.groups()
                signal_type = re.sub(r'\s+', ' ', signal_type.strip())
                
                return {
                    'ticker': ticker.strip(),
                    'signal_type': signal_type,
                    'original_signal': signal_type,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'TradingView'
                }
            
            # النمط البديل: SYMBOL SIGNAL_TYPE
            pattern2 = r'([A-Za-z0-9]+)\s+(.+)'
            match2 = re.match(pattern2, text)
            if match2:
                ticker, signal_type = match2.groups()
                return {
                    'ticker': ticker.strip(),
                    'signal_type': signal_type.strip(),
                    'original_signal': signal_type.strip(),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'TradingView'
                }

            return {
                'ticker': "UNKNOWN",
                'signal_type': text,
                'original_signal': text,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'TradingView'
            }
                
        except Exception as e:
            self.logger.error(f"خطأ في تحليل الإشارة: {e}")
            return None

    # =============================
    # تصنيف الإشارات - التعديل الرئيسي هنا
    # =============================
    def classify_signal_flexible(self, signal_data):
        """تصنيف مرن للإشارات"""
        signal_type = signal_data['signal_type']
        signal_lower = signal_type.lower()
        
        print(f"🔍 [تصنيف] تحليل الإشارة: '{signal_type}'")
        
        # 🔥 التعديل: فحص تأكيد الاتجاه أولاً (لأنه أكثر تحديداً)
        if any(keyword in signal_lower for keyword in self.custom_keywords['trend_confirm']):
            print(f"🎯 [تصنيف] إشارة تأكيد اتجاه: '{signal_type}'")
            return 'trend_confirm'
        
        # ثم فحص الاتجاه الأساسي
        if any(keyword in signal_lower for keyword in self.custom_keywords['trend']):
            print(f"🎯 [تصنيف] إشارة اتجاه: '{signal_type}'")
            return 'trend'
        
        # 1. المطابقة التامة
        if signal_type in self.flexible_index:
            category = self.flexible_index[signal_type]
            print(f"✅ [مطابقة تامة] '{signal_type}' -> '{category}'")
            return category
        
        # 2. المطابقة المطبعة
        normalized = self.normalize_signal(signal_type)
        if normalized in self.flexible_index:
            category = self.flexible_index[normalized]
            print(f"✅ [مطابقة مطبعة] '{normalized}' -> '{category}'")
            return category
        
        # 3. البحث بالكلمات المفتاحية
        category = self.keyword_based_classification(signal_type)
        if category != 'unknown':
            print(f"✅ [مطابقة بالكلمات] '{signal_type}' -> '{category}'")
            return category
        
        print(f"❌ [غير معروفة] لا يوجد تطابق لـ '{signal_type}'")
        return 'unknown'

    def keyword_based_classification(self, signal_type):
        """تصنيف الإشارة بناء على الكلمات المفتاحية"""
        signal_lower = signal_type.lower()
        normalized = self.normalize_signal(signal_type)
        
        found_keywords = []
        for keyword, matches in self.keyword_index.items():
            if keyword in normalized or keyword in signal_lower:
                found_keywords.extend(matches)
        
        if not found_keywords:
            return 'unknown'
        
        category_scores = {}
        for category, original_signal in found_keywords:
            category_scores[category] = category_scores.get(category, 0) + 1
        
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            return best_category[0]
        
        return 'unknown'

    def handle_unknown_signal(self, signal_data):
        """معالجة الإشارات غير المعروفة"""
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        self.logger.warning(f"إشارة غير معروفة: '{signal}' للرمز {symbol}")
        return False

    # =============================
    # إدارة الصفقات
    # =============================
    def get_active_trades_for_symbol(self, symbol):
        """الحصول على جميع الصفقات النشطة لرمز معين"""
        active_trades = [trade for trade in self.active_trades.values() 
                if trade['ticker'].upper() == symbol.upper() and trade['status'] == 'OPEN']
        return active_trades

    def find_active_trade(self, ticker):
        """البحث عن أي صفقة نشطة للرمز"""
        active_trades = self.get_active_trades_for_symbol(ticker)
        return active_trades[0] if active_trades else None

    def can_open_new_trade(self, symbol):
        """التحقق من إمكانية فتح صفقة جديدة للرمز"""
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        symbol_ok = active_for_symbol < self.config['MAX_TRADES_PER_SYMBOL']
        total_ok = total_active < self.config['MAX_OPEN_TRADES']
        
        return symbol_ok and total_ok

    # =============================
    # 🔥 الوظيفة الجديدة: إغلاق جميع الصفقات للرمز
    # =============================
    def close_all_trades_for_symbol(self, symbol, reason="تغيير الاتجاه"):
        """إغلاق جميع الصفقات المفتوحة للرمز"""
        active_trades = self.get_active_trades_for_symbol(symbol)
        
        if not active_trades:
            print(f"📭 لا توجد صفقات مفتوحة للرمز {symbol}")
            return 0
        
        closed_count = 0
        print(f"🔻 جاري إغلاق {len(active_trades)} صفقة للرمز {symbol} بسبب {reason}...")
        
        for trade in active_trades:
            print(f"🔻 إغلاق الصفقة #{trade['trade_id']} - {trade['direction']} - {trade['ticker']}")
            trade.update({
                'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'CLOSED',
                'exit_signal': f"إغلاق تلقائي - {reason}",
                'auto_closed': True
            })
            
            # إرسال رسالة إغلاق
            msg = self.format_auto_close_message(trade, reason)
            if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
                telegram_sent = self.send_telegram(msg)
                if telegram_sent:
                    print(f"✅ [Telegram] تم إرسال إشعار إغلاق الصفقة #{trade['trade_id']}")
            
            external_sent = self.send_to_external_server_with_retry(msg, 'exit')
            if external_sent:
                print(f"✅ [الخادم] تم إرسال إشعار إغلاق الصفقة #{trade['trade_id']}")
            
            closed_count += 1
            self.logger.info(f"إغلاق تلقائي للصفقة #{trade['trade_id']} بسبب {reason}")
        
        print(f"✅ تم إغلاق {closed_count} صفقة للرمز {symbol}")
        return closed_count

    # =============================
    # معالجات حسب الفئة
    # =============================
    def handle_trend_signal(self, signal_data):
        """معالجة إشارات الاتجاه - ترسل فقط عند تغيير الاتجاه"""
        symbol = signal_data['ticker']
        original_signal = signal_data.get('original_signal', signal_data['signal_type'])
        signal_lower = original_signal.lower()
        
        # تحديد الاتجاه الجديد
        if any(keyword in signal_lower for keyword in self.custom_keywords['bullish']):
            new_trend = 'BULLISH'
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        elif any(keyword in signal_lower for keyword in self.custom_keywords['bearish']):
            new_trend = 'BEARISH'
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        else:
            return False

        current_trend = self.symbol_trends.get(symbol)
        
        # إرسال الإشعارات فقط عند تغيير الاتجاه
        if current_trend == new_trend:
            print(f"🔄 [اتجاه] تجاهل إشارة اتجاه مكررة: {symbol} لا يزال {current_trend}")
            return True
        
        print(f"🔧 [اتجاه] تغيير اتجاه {symbol} من {current_trend} إلى {new_trend}")
        
        # 🔥 إغلاق جميع الصفقات المفتوحة للرمز إذا كان الإعداد مفعلاً
        if self.config['RESET_TRADES_ON_TREND_CHANGE']:
            closed_trades = self.close_all_trades_for_symbol(symbol, f"تغيير الاتجاه من {current_trend} إلى {new_trend}")
            if closed_trades > 0:
                print(f"🔻 تم إغلاق {closed_trades} صفقة بسبب تغيير الاتجاه")
        
        # تحديث اتجاه الرمز
        self.symbol_trends[symbol] = new_trend

        # إرسال إشعار الاتجاه
        msg = self.format_trend_message(signal_data, trend_icon, trend_text, current_trend, new_trend)
        
        if self.should_send_message('trend', signal_data):
            self.send_telegram(msg)
            
        self.send_to_external_server_with_retry(msg, 'trend')
        
        self.last_trend_notifications[symbol] = new_trend
        self.last_trend_notified_at[symbol] = datetime.now()
        self.logger.info(f"تغيير اتجاه {symbol}: {current_trend} -> {new_trend}")

        return True

    def handle_trend_confirmation(self, signal_data):
        """معالجة إشارات تأكيد الاتجاه - ترسل فقط إذا كانت مطابقة للاتجاه الحالي"""
        symbol = signal_data['ticker']
        original_signal = signal_data.get('original_signal', signal_data['signal_type'])
        signal_lower = original_signal.lower()
        
        # تحديد اتجاه الإشارة
        if any(keyword in signal_lower for keyword in self.custom_keywords['bullish']):
            signal_trend = 'BULLISH'
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        elif any(keyword in signal_lower for keyword in self.custom_keywords['bearish']):
            signal_trend = 'BEARISH'
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        else:
            return False

        current_trend = self.symbol_trends.get(symbol)
        
        # 🔥 التحقق من مطابقة تأكيد الاتجاه مع الاتجاه الحالي
        if current_trend != signal_trend:
            print(f"❌ [تأكيد اتجاه] تجاهل إشارة تأكيد غير مطابقة: {symbol} ({signal_trend}) لا يتطابق مع الاتجاه الحالي ({current_trend})")
            return False
        
        print(f"✅ [تأكيد اتجاه] إشارة تأكيد مطابقة للاتجاه الحالي: {symbol} ({signal_trend})")

        # إرسال إشعار تأكيد الاتجاه
        msg = self.format_trend_confirmation_message(signal_data, trend_icon, trend_text)
        
        if self.should_send_message('confirmation', signal_data):
            telegram_sent = self.send_telegram(msg)
            if telegram_sent:
                print(f"✅ [Telegram] تم إرسال تأكيد اتجاه {symbol}: {signal_trend}")
            
        external_sent = self.send_to_external_server_with_retry(msg, 'confirmation')
        if external_sent:
            print(f"✅ [الخادم] تم إرسال تأكيد اتجاه {symbol}: {signal_trend}")
        
        self.logger.info(f"تأكيد اتجاه {symbol}: {signal_trend}")
        return True

    def handle_entry_signal(self, signal_data, signal_category):
        """معالجة إشارات الدخول مع دعم الاستراتيجية المزدوجة"""
        symbol = signal_data['ticker']

        # التحقق من إمكانية فتح صفقة جديدة
        if not self.can_open_new_trade(symbol):
            active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
            total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
            
            self.logger.warning(
                f"تجاهل فتح صفقة: حدود الصفقات مكتملة - "
                f"{symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']}, "
                f"الإجمالي: {total_active}/{self.config['MAX_OPEN_TRADES']}"
            )
            return False

        # تطبيق شرط الاتجاه
        symbol_trend = self.symbol_trends.get(symbol)
        if self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and symbol_trend:
            if (signal_category in ['entry_bullish', 'entry_bullish1'] and symbol_trend != 'BULLISH') or \
               (signal_category in ['entry_bearish', 'entry_bearish1'] and symbol_trend != 'BEARISH'):
                print(f"❌ [اتجاه] رفض الصفقة: إشارة {signal_category} ضد اتجاه {symbol_trend} للرمز {symbol}")
                self.logger.warning(f"الإشارة لا تتطابق مع اتجاه {symbol} ({symbol_trend})")
                return False
            else:
                print(f"✅ [اتجاه] الصفقة مطابقة للاتجاه: {signal_category} مع {symbol_trend}")

        # 🆕 استخدام الاستراتيجية المزدوجة إذا كانت مفعلة
        if self.config['DUAL_CONFIRMATION_STRATEGY']:
            return self.handle_dual_confirmation_strategy(signal_data, symbol, signal_category)
        else:
            # الاستراتيجية العادية (السابقة)
            return self.handle_single_confirmation_strategy(signal_data, symbol, signal_category)

    def handle_dual_confirmation_strategy(self, signal_data, symbol, signal_category):
        """معالجة الاستراتيجية المزدوجة - المجموعتين"""
        # 🆕 تحديد نوع المجموعة
        if signal_category in ['entry_bullish', 'entry_bearish']:
            group_type = 'group1'
        else:  # entry_bullish1, entry_bearish1
            group_type = 'group2'

        key = f"{symbol}_{signal_category}_{group_type}"
        self.clean_expired_signals()

        if key not in self.pending_signals:
            self.pending_signals[key] = {
                'unique_signals': set(),
                'signals_data': [],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'signal_category': signal_category,
                'group_type': group_type
            }

        clean_type = self.normalize_signal(signal_data['signal_type'])
        group = self.pending_signals[key]

        now = datetime.now()
        if (now - group['created_at']).total_seconds() > self.config['DUAL_CONFIRMATION_TIMEOUT']:
            self.pending_signals[key] = {
                'unique_signals': set(),
                'signals_data': [],
                'created_at': now,
                'updated_at': now,
                'signal_category': signal_category,
                'group_type': group_type
            }
            group = self.pending_signals[key]

        if clean_type not in group['unique_signals']:
            group['unique_signals'].add(clean_type)
            group['signals_data'].append(signal_data)
            group['updated_at'] = now
            self.logger.info(f"إشارة فريدة للمجموعة {group_type}: '{signal_data['signal_type']}'")
        else:
            self.logger.info(f"تجاهل إشارة مكررة للمجموعة {group_type}: '{signal_data['signal_type']}'")
            return True

        # التحقق من استيفاء شروط فتح الصفقة
        return self.check_dual_confirmation(symbol, signal_category)

    def check_dual_confirmation(self, symbol, signal_category):
        """التحقق من استيفاء شروط المجموعتين"""
        # تحديد الفئة الأساسية
        if 'bullish' in signal_category:
            base_category = 'entry_bullish'
        else:
            base_category = 'entry_bearish'

        group1_key = f"{symbol}_{base_category}_group1"
        group2_key = f"{symbol}_{base_category}1_group2"  # 🔥 استخدام الفئة الثانية المناسبة

        group1_ready = False
        group2_ready = False

        # التحقق من المجموعة الأولى
        if group1_key in self.pending_signals:
            group1 = self.pending_signals[group1_key]
            required_group1 = self.config['REQUIRED_CONFIRMATIONS_GROUP1']
            if len(group1['unique_signals']) >= required_group1:
                group1_ready = True
                print(f"✅ المجموعة الأولى جاهزة: {len(group1['unique_signals'])}/{required_group1}")

        # التحقق من المجموعة الثانية
        if group2_key in self.pending_signals:
            group2 = self.pending_signals[group2_key]
            required_group2 = self.config['REQUIRED_CONFIRMATIONS_GROUP2']
            if len(group2['unique_signals']) >= required_group2:
                group2_ready = True
                print(f"✅ المجموعة الثانية جاهزة: {len(group2['unique_signals'])}/{required_group2}")

        # إذا استوفت كلتا المجموعتين الشروط
        if group1_ready and group2_ready:
            print(f"🎯 جميع الشروط مستوفاة! فتح صفقة للرمز {symbol}")
            return self.open_dual_confirmed_trade(symbol, base_category, group1_key, group2_key)
        else:
            # عرض حالة التقدم
            group1_count = len(self.pending_signals[group1_key]['unique_signals']) if group1_key in self.pending_signals else 0
            group2_count = len(self.pending_signals[group2_key]['unique_signals']) if group2_key in self.pending_signals else 0
            
            print(f"📊 تقدم التأكيد المزدوج - {symbol}:")
            print(f"   📁 المجموعة الأولى: {group1_count}/{self.config['REQUIRED_CONFIRMATIONS_GROUP1']}")
            print(f"   📁 المجموعة الثانية: {group2_count}/{self.config['REQUIRED_CONFIRMATIONS_GROUP2']}")
            
            return True

    def open_dual_confirmed_trade(self, symbol, base_category, group1_key, group2_key):
        """فتح صفقة مؤكدة من المجموعتين"""
        group1_data = self.pending_signals[group1_key]
        group2_data = self.pending_signals[group2_key]

        trade_id = str(uuid.uuid4())[:8]
        direction = 'CALL' if base_category == 'entry_bullish' else 'PUT'

        trade_info = {
            'trade_id': trade_id,
            'ticker': symbol,
            'direction': direction,
            'signal_type': group1_data['signals_data'][0]['signal_type'],
            'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'OPEN',
            'confirmation_count_group1': len(group1_data['unique_signals']),
            'confirmation_count_group2': len(group2_data['unique_signals']),
            'confirmed_signals_group1': list(group1_data['unique_signals']),
            'confirmed_signals_group2': list(group2_data['unique_signals']),
            'strategy_type': 'DUAL_CONFIRMATION'
        }
        self.active_trades[trade_id] = trade_info

        # إرسال رسالة الدخول
        msg = self.format_dual_entry_message(trade_info, group1_data, group2_data)
        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            self.send_telegram(msg)
        self.send_to_external_server_with_retry(msg, 'entry')

        # تنظيف المجموعتين بعد فتح الصفقة
        del self.pending_signals[group1_key]
        del self.pending_signals[group2_key]

        # عرض إحصائية الصفقات
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        print(f"📊 إحصائية الصفقات: {symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']} | الإجمالي: {total_active}/{self.config['MAX_OPEN_TRADES']}")
        
        self.logger.info(f"فتح صفقة {direction} #{trade_id} باستراتيجية المزدوجة")
        return True

    def handle_single_confirmation_strategy(self, signal_data, symbol, signal_category):
        """معالجة الاستراتيجية العادية (السابقة)"""
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

        clean_type = self.normalize_signal(signal_data['signal_type'])
        group = self.pending_signals[key]

        now = datetime.now()
        if (now - group['created_at']).total_seconds() > self.config['CONFIRMATION_TIMEOUT']:
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
            self.logger.info(f"إشارة فريدة: '{signal_data['signal_type']}'")
        else:
            self.logger.info(f"تجاهل إشارة مكررة: '{signal_data['signal_type']}'")
            return True

        if len(group['unique_signals']) >= self.config['REQUIRED_CONFIRMATIONS']:
            return self.open_confirmed_trade(key, signal_category)
        else:
            self.logger.info(f"في انتظار التأكيد: {len(group['unique_signals'])}/{self.config['REQUIRED_CONFIRMATIONS']}")
            return True

    def open_confirmed_trade(self, key, category):
        """فتح صفقة مؤكدة"""
        data = self.pending_signals.get(key)
        if not data or len(data['unique_signals']) < self.config['REQUIRED_CONFIRMATIONS']:
            return False

        main_signal = data['signals_data'][0]
        trade_id = str(uuid.uuid4())[:8]
        direction = 'CALL' if category == 'entry_bullish' else 'PUT'

        trade_info = {
            'trade_id': trade_id,
            'ticker': main_signal['ticker'],
            'direction': direction,
            'signal_type': main_signal['signal_type'],
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
        
        # عرض إحصائية الصفقات بعد الفتح
        symbol = main_signal['ticker']
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        print(f"📊 إحصائية الصفقات: {symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']} | الإجمالي: {total_active}/{self.config['MAX_OPEN_TRADES']}")
        
        self.logger.info(f"فتح صفقة {direction} #{trade_id} بإشارات: {list(data['unique_signals'])}")
        return True

    def clean_expired_signals(self):
        """تنظيف الإشارات المنتهية الصلاحية"""
        now = datetime.now()
        expired_keys = []
        
        for key, data in self.pending_signals.items():
            # استخدام الوقت المناسب حسب نوع الاستراتيجية
            if self.config['DUAL_CONFIRMATION_STRATEGY']:
                timeout = self.config['DUAL_CONFIRMATION_TIMEOUT']
            else:
                timeout = self.config['CONFIRMATION_TIMEOUT']
                
            if (now - data.get('updated_at', data['created_at'])).total_seconds() > timeout:
                expired_keys.append(key)
        
        for key in expired_keys:
            group_type = self.pending_signals[key].get('group_type', 'unknown')
            signal_count = len(self.pending_signals[key]['unique_signals'])
            del self.pending_signals[key]
            self.logger.info(f"تنظيف مجموعة منتهية: {key} ({group_type}) - {signal_count} إشارة")

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

        msg = self.format_exit_message(trade)
        if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
            self.send_telegram(msg)
        self.send_to_external_server_with_retry(msg, 'exit')

        self.logger.info(f"إغلاق صفقة #{trade['trade_id']}")
        return True

    def handle_general_signal(self, signal_data):
        """معالجة الإشارات العامة"""
        msg = self.format_general_message(signal_data)
        if self.should_send_message('general', signal_data):
            self.send_telegram(msg)
        self.send_to_external_server_with_retry(msg, 'general')
        return True

    # =============================
    # التحكم في الإرسال
    # =============================
    def should_send_message(self, message_type, signal_data=None):
        """التحقق مما إذا يجب إرسال الرسالة"""
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
            signal_text = str(signal_data.get('signal_type', '')).lower()
            direction = signal_data.get('direction', '').upper()
            
            if ('bullish' in signal_text or direction == 'CALL') and not self.config['SEND_BULLISH_SIGNALS']:
                print("🔕 إرسال الإشارات الصاعدة معطل")
                return False
            if ('bearish' in signal_text or direction == 'PUT') and not self.config['SEND_BEARISH_SIGNALS']:
                print("🔕 إرسال الإشارات الهابطة معطل")
                return False

        return True

    # =============================
    # قوالب الرسائل - التصميم الأصلي المطلوب
    # =============================
    def format_trend_message(self, signal_data, trend_icon, trend_text, old_trend, new_trend):
        """تنسيق رسالة الاتجاه - التصميم الأصلي المطلوب"""
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        
        return f"""☰☰☰ 📊 تغيير الاتجاه ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal}
┃ 🔄 الحالة: تغيير اتجاه ({old_trend or 'لا يوجد'} → {new_trend})
┗━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp}"""

    def format_trend_confirmation_message(self, signal_data, trend_icon, trend_text):
        """تنسيق رسالة تأكيد الاتجاه - التصميم الأصلي المطلوب"""
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        
        return f"""☰☰☰ ✅ تأكيد الاتجاه ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal}
┃ 🔄 الحالة: تأكيد اتجاه
┃ 🎯 المحاذاة: 🟢 مطابق للاتجاه العام
┗━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp}"""

    def format_entry_message(self, trade_info, pending_data):
        """تنسيق رسالة الدخول - التصميم الأصلي المطلوب"""
        symbol = trade_info['ticker']
        direction = trade_info['direction']
        signal = trade_info['signal_type']
        confirmations = trade_info.get('confirmation_count', 1)
        helpers = trade_info.get('confirmed_signals', [])
        trend = self.symbol_trends.get(symbol, '')
        trend_icon = '🟢📈 BULLISH' if trend == 'BULLISH' else '🔴📉 BEARISH'
        
        # التحقق من محاذاة الاتجاه
        align_text = '🟢 مطابق للاتجاه العام' if (
            (direction == 'CALL' and trend == 'BULLISH') or 
            (direction == 'PUT' and trend == 'BEARISH')
        ) else '🔴 غير مطابق'
        
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        # حساب الصفقات الحالية
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])

        # تنسيق الإشارات المساعدة
        helpers_list = ''
        if len(helpers) > 1:
            numbered_helpers = [f"┃   {i+1}. {helper}" for i, helper in enumerate(helpers[1:])]
            helpers_list = "\n" + "\n".join(numbered_helpers)

        return (
            "✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 🎯 نوع الصفقة: {'🟢 شراء' if direction=='CALL' else '🔴 بيع'}\n"
            f"┃ 📊 اتجاه الرمز: {trend_icon}\n"
            f"┃ 🎯 محاذاة الاتجاه: {align_text}\n"
            f"┃ 📋 الإشارة الرئيسية: {signal} (تم التأكيد بـ {confirmations} إشارات)\n"
            f"┃ 🔔 الإشارات المساعدة: {len(helpers)-1} إشارة{helpers_list}\n"
            f"┃ 📊 صفقات {symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{self.config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    def format_dual_entry_message(self, trade_info, group1_data, group2_data):
        """تنسيق رسالة الدخول للاستراتيجية المزدوجة - التصميم الأصلي المطلوب"""
        symbol = trade_info['ticker']
        direction = trade_info['direction']
        signal = trade_info['signal_type']
        confirmations1 = trade_info.get('confirmation_count_group1', 0)
        confirmations2 = trade_info.get('confirmation_count_group2', 0)
        helpers1 = trade_info.get('confirmed_signals_group1', [])
        helpers2 = trade_info.get('confirmed_signals_group2', [])
        trend = self.symbol_trends.get(symbol, '')
        trend_icon = '🟢📈 BULLISH' if trend == 'BULLISH' else '🔴📉 BEARISH'
        
        # التحقق من محاذاة الاتجاه
        align_text = '🟢 مطابق للاتجاه العام' if (
            (direction == 'CALL' and trend == 'BULLISH') or 
            (direction == 'PUT' and trend == 'BEARISH')
        ) else '🔴 غير مطابق'
        
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        # حساب الصفقات الحالية
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])

        # تنسيق الإشارات المساعدة للمجموعتين
        helpers_list1 = ''
        if helpers1:
            numbered_helpers1 = [f"┃   {i+1}. {helper}" for i, helper in enumerate(helpers1)]
            helpers_list1 = "\n" + "\n".join(numbered_helpers1)

        helpers_list2 = ''
        if helpers2:
            numbered_helpers2 = [f"┃   {i+1}. {helper}" for i, helper in enumerate(helpers2)]
            helpers_list2 = "\n" + "\n".join(numbered_helpers2)

        return (
            "✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 🎯 نوع الصفقة: {'🟢 شراء' if direction=='CALL' else '🔴 بيع'}\n"
            f"┃ 📊 اتجاه الرمز: {trend_icon}\n"
            f"┃ 🎯 محاذاة الاتجاه: {align_text}\n"
            f"┃ 🎯 الاستراتيجية: تأكيد مزدوج (مجموعتين)\n"
            f"┃ 📋 الإشارة الرئيسية: {signal}\n"
            f"┃ 🔔 تأكيدات المجموعة الأولى: {confirmations1} إشارة{helpers_list1}\n"
            f"┃ 🔔 تأكيدات المجموعة الثانية: {confirmations2} إشارة{helpers_list2}\n"
            f"┃ 📊 صفقات {symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{self.config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    def format_exit_message(self, trade):
        """تنسيق رسالة الخروج - التصميم الأصلي المطلوب"""
        symbol = trade['ticker']
        exit_signal = trade.get('exit_signal', 'غير محدد')
        direction = trade.get('direction', 'CALL')
        dir_text = '🟢 شراء' if direction == 'CALL' else '🔴 بيع (PUT)'
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        return (
            "════ 🚪 إشـــــــارة خــــــروج ════\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 📝 السبب: إشارة خروج: {exit_signal}\n"
            f"┃ 🎯 نوع الصفقة المغلقة: {dir_text}\n"
            f"┃ 📊 صفقات {symbol} المتبقية: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{self.config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    def format_auto_close_message(self, trade, reason):
        """تنسيق رسالة الإغلاق التلقائي - التصميم الأصلي المطلوب"""
        symbol = trade['ticker']
        direction = trade.get('direction', 'CALL')
        dir_text = '🟢 شراء' if direction == 'CALL' else '🔴 بيع (PUT)'
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        return (
            "⚠️ إغلاق تلقائي للصفقة\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 📝 السبب: {reason}\n"
            f"┃ 🎯 نوع الصفقة المغلقة: {dir_text}\n"
            f"┃ 📊 صفقات {symbol} المتبقية: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']}\n"
            f"┃ 📊 الصفقات الإجمالية: {total_active}/{self.config['MAX_OPEN_TRADES']}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    def format_general_message(self, signal_data):
        """تنسيق الرسائل العامة - التصميم الأصلي المطلوب"""
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        
        return (
            "ℹ️ إشـــــــــــارة عامـــــــــــــة\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 📝 التفاصيل: {signal}\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )

    # =============================
    # الإرسال
    # =============================
    def send_telegram(self, message):
        """إرسال رسالة إلى Telegram"""
        if not self.config['TELEGRAM_ENABLED']:
            return False

        token = self.safe_get_token('TELEGRAM_BOT_TOKEN')
        chat_id = self.safe_get_token('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            return False

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            success = response.status_code == 200
            if success:
                print("✅ تم إرسال Telegram بنجاح")
            else:
                print(f"❌ فشل إرسال Telegram: {response.status_code}")
            return success
        except Exception as e:
            print(f"💥 خطأ في إرسال Telegram: {e}")
            return False

    def send_to_external_server(self, message_text, message_type):
        """إرسال رسالة إلى الخادم الخارجي"""
        if not self.config['EXTERNAL_SERVER_ENABLED']:
            return False
            
        url = self.config['EXTERNAL_SERVER_URL']
        if not url or url == 'https://api.example.com/webhook/trading':
            return False
            
        try:
            response = requests.post(
                url,
                data=message_text.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=10,
            )
            success = response.status_code in (200, 201, 204)
            if success:
                print("✅ تم إرسال الرسالة للخادم الخارجي بنجاح")
            else:
                print(f"❌ فشل إرسال الرسالة للخادم الخارجي: {response.status_code}")
            return success
        except Exception as e:
            print(f"💥 خطأ في إرسال الرسالة للخادم الخارجي: {e}")
            return False

    def send_to_external_server_with_retry(self, message_text, message_type, max_retries=2):
        """إرسال رسالة مع إعادة المحاولة"""
        if not self.should_send_message(message_type):
            return False

        for attempt in range(max_retries + 1):
            if self.send_to_external_server(message_text, message_type):
                return True
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"🔄 إعادة المحاولة بعد {wait_time} ثوانٍ... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
        return False


# =============================
# تشغيل النظام
# =============================
def create_app():
    """دالة إنشاء التطبيق لـ Gunicorn"""
    system = TradingSystem()
    return system.app

if __name__ == '__main__':
    try:
        print("🚀 بدء تشغيل نظام التداول...")
        system = TradingSystem()
        app = system.app
        
        print(f"🌐 جاري تشغيل الخادم على المنفذ {system.port}...")
        print("📡 الخادم يعمل وجاهز لاستقبال الإشارات")
        print("⏹️  لإيقاف الخادم، اضغط Ctrl+C")
        
        app.run(host='0.0.0.0', port=system.port, debug=False)
        
    except KeyboardInterrupt:
        print("\n🛑 إيقاف الخادم...")
    except Exception as e:
        print(f"💥 خطأ غير متوقع: {e}")
        print("🔧 جاري إعادة تشغيل النظام...")
        time.sleep(5)

# جعل التطبيق متاحاً لـ Gunicorn
system_instance = TradingSystem()
app = system_instance.app
