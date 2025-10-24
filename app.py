#!/usr/bin/env python3
"""
نظام معالجة إشارات التداول - النسخة المعدلة مع تحميل كامل للإعدادات من .env
"""

import os
import json
import logging
import uuid
import re
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from decouple import config

# تحميل متغيرات البيئة
load_dotenv()

class TradingSystem:
    """النظام الرئيسي المدمج لإشارات التداول"""
    
    def __init__(self):
        self.setup_config()
        self.setup_managers()
        self.setup_flask()
        self.display_loaded_signals()
        
        print(f"🚀 نظام معالجة الإشارات جاهز - المنفذ {self.port}")
        print(f"✅ التأكيد المطلوب: {self.config['REQUIRED_CONFIRMATIONS']} إشارات")
        print(f"📊 الحد الأقصى للصفقات: {self.config['MAX_OPEN_TRADES']}")
    
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
            'CONFIRMATION_WINDOW': config('CONFIRMATION_WINDOW', default=1200, cast=int),
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
        
        # إنشاء قائمة بجميع الإشارات
        self.all_signals = []
        for category_signals in self.signals.values():
            self.all_signals.extend(category_signals)
    
    def _load_signal_list(self, key):
        """تحميل قائمة الإشارات من .env مع معالجة القوائم الطويلة"""
        try:
            signal_str = config(key, default='')
            if not signal_str:
                return []
            
            # تقسيم الإشارات مع معالجة الفواصل في الأسماء الطويلة
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
            
            # إضافة آخر إشارة
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
        self.current_trend = None
        self.last_trend_notification = None
    
    def setup_flask(self):
        """إعداد تطبيق Flask والمسارات"""
        self.app = Flask(__name__)
        self.setup_routes()
        self.setup_logging()
    
    def setup_logging(self):
        """إعداد نظام التسجيل"""
        logging.basicConfig(
            level=getattr(logging, self.config['LOG_LEVEL']),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['LOG_FILE']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('trading_system')
    
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
    
    def handle_webhook(self, request):
        """معالجة طلبات Webhook"""
        try:
            raw_signal = self.extract_signal_data(request)
            if not raw_signal:
                return jsonify({"status": "error", "message": "إشارة فارغة"}), 400
            
            self.logger.info(f"📨 إشارة مستلمة: {raw_signal}")
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
            self.logger.error(f"❌ خطأ في Webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    def extract_signal_data(self, request):
        """استخراج بيانات الإشارة من الطلب"""
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            data = request.get_json()
            if data:
                return self.convert_json_to_signal(data)
        
        return request.get_data(as_text=True)
    
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
            self.logger.warning(f"⚠️  إشارة غير صالحة: {raw_signal}")
            return False
        
        signal_category = self.classify_signal(signal_data)
        signal_data['category'] = signal_category
        
        self.logger.info(f"🎯 إشارة مصنفة: {signal_data['signal_type']} -> {signal_category}")
        
        # المعالجة حسب التصنيف
        if signal_category == 'trend':
            return self.handle_trend_signal(signal_data)
        elif signal_category == 'exit':
            return self.handle_exit_signal(signal_data)
        elif signal_category == 'trend_confirm':
            return self.handle_trend_confirmation(signal_data)
        elif signal_category == 'general':
            return self.handle_general_signal(signal_data)
        else:  # إشارات الدخول
            return self.handle_entry_signal(signal_data, signal_category)
    
    def parse_signal(self, raw_signal):
        """تحليل الإشارة إلى مكوناتها"""
        try:
            # الصيغة الجديدة: "Ticker : ... Signal : ... Open : ... Close : ..."
            pattern = r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+?)\s+Open\s*:\s*(.+?)\s+Close\s*:\s*(.+)'
            match = re.match(pattern, raw_signal)
            
            if match:
                ticker, signal_type, open_price, close_price = match.groups()
            else:
                # المحاولة مع الصيغ الأخرى
                if '|' in raw_signal:
                    parts = [p.strip() for p in raw_signal.split('|')]
                    if len(parts) >= 2:
                        ticker, signal_type = parts[0], parts[1]
                        open_price, close_price = "0", "0"
                    else:
                        return None
                else:
                    # إذا كانت مجرد اسم إشارة
                    ticker, signal_type = "BTCUSDT", raw_signal
                    open_price, close_price = "0", "0"
            
            # تنظيف الإشارة من NaN
            if 'NaN' in signal_type:
                signal_type = self.clean_nan_signal(signal_type, raw_signal)
                if not signal_type:
                    return None
            
            return {
                'ticker': ticker.strip(),
                'signal_type': signal_type.strip(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'TradingView'
            }
            
        except Exception as e:
            self.logger.error(f"❌ خطأ في تحليل الإشارة: {e}")
            return None
    
    def clean_nan_signal(self, signal_type, raw_signal):
        """تنظيف إشارات NaN"""
        if 'bullish' in raw_signal.lower():
            return 'bullish_trend'
        elif 'bearish' in raw_signal.lower():
            return 'bearish_trend'
        return None
    
    def classify_signal(self, signal_data):
        """تصنيف الإشارة"""
        signal_type = self.clean_signal_type(signal_data['signal_type'])
        signal_data['signal_type'] = signal_type  # تحديث بالنظيف
        
        # البحث في القوائم
        for category, signals in self.signals.items():
            if signal_type in signals:
                return category
        
        # المطابقة الجزئية
        for category, signals in self.signals.items():
            for signal in signals:
                if signal.lower() in signal_type.lower() or signal_type.lower() in signal.lower():
                    self.logger.info(f"🔍 مطابقة جزئية: {signal_type} -> {signal}")
                    return category
        
        return 'unknown'
    
    def clean_signal_type(self, signal_type):
        """تنظيف نوع الإشارة"""
        # إزالة المحتوى بين الأقواس والأرقام
        cleaned = re.sub(r'\[.*?\]|\(.*?\)|\d+\.?\d*', '', signal_type)
        # إزالة الفراغات الزائدة
        return ' '.join(cleaned.split()).strip()
    
    def handle_trend_signal(self, signal_data):
        """معالجة إشارات الاتجاه"""
        signal_type = signal_data['signal_type']
        
        if 'bullish' in signal_type.lower():
            new_trend = 'BULLISH'
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        elif 'bearish' in signal_type.lower():
            new_trend = 'BEARISH'
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        else:
            return False
        
        # التحقق من تغير الاتجاه
        trend_changed = self.current_trend != new_trend
        self.current_trend = new_trend
        
        # إرسال الإشعار إذا تغير الاتجاه أو أول مرة
        if (trend_changed or self.last_trend_notification != new_trend) and self.config['SEND_TREND_MESSAGES']:
            message = self.format_trend_message(signal_data, trend_icon, trend_text)
            self.send_telegram(message)
            self.last_trend_notification = new_trend
            self.logger.info(f"📊 إشعار اتجاه: {new_trend}")
        
        # إغلاق الصفقات إذا كان الإعداد مفعلاً
        if self.config['RESET_TRADES_ON_TREND_CHANGE'] and trend_changed and self.active_trades:
            closed_count = 0
            for trade_id in list(self.active_trades.keys()):
                if self.active_trades[trade_id]['status'] == 'OPEN':
                    self.active_trades[trade_id].update({
                        'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'CLOSED',
                        'exit_signal': 'trend_change'
                    })
                    closed_count += 1
            self.logger.info(f"🔄 إغلاق {closed_count} صفقة بسبب تغيير الاتجاه")
        
        return True
    
    def handle_entry_signal(self, signal_data, signal_category):
        """معالجة إشارات الدخول"""
        # التحقق من الحد الأقصى للصفقات
        active_trades_count = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        if active_trades_count >= self.config['MAX_OPEN_TRADES']:
            self.logger.warning("⏹️  الحد الأقصى للصفقات مكتفي")
            return False
        
        # التحقق من مطابقة الاتجاه إذا كان الإعداد مفعلاً
        if self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and self.current_trend:
            if (signal_category == 'entry_bullish' and self.current_trend != 'BULLISH') or \
               (signal_category == 'entry_bearish' and self.current_trend != 'BEARISH'):
                self.logger.warning("⏹️  الإشارة لا تتطابق مع الاتجاه الحالي")
                return False
        
        # نظام التأكيد
        ticker = signal_data['ticker']
        direction = 'bullish' if signal_category == 'entry_bullish' else 'bearish'
        signal_key = f"{ticker}_{direction}"
        
        # تنظيف الإشارات المنتهية
        self.clean_expired_signals()
        
        # إضافة الإشارة المعلقة
        if signal_key not in self.pending_signals:
            self.pending_signals[signal_key] = {
                'unique_signals': set(),
                'signals_data': [],
                'created_at': datetime.now()
            }
        
        # إضافة الإشارة إذا كانت فريدة
        if signal_data['signal_type'] not in self.pending_signals[signal_key]['unique_signals']:
            self.pending_signals[signal_key]['unique_signals'].add(signal_data['signal_type'])
            self.pending_signals[signal_key]['signals_data'].append(signal_data)
            self.pending_signals[signal_key]['updated_at'] = datetime.now()
            self.logger.info(f"📥 إشارة فريدة: {signal_data['signal_type']}")
        
        # التحقق من اكتمال التأكيد
        unique_count = len(self.pending_signals[signal_key]['unique_signals'])
        if unique_count >= self.config['REQUIRED_CONFIRMATIONS']:
            return self.open_confirmed_trade(signal_key, signal_category)
        else:
            self.logger.info(f"⏳ في انتظار التأكيد: {unique_count}/{self.config['REQUIRED_CONFIRMATIONS']}")
            return True
    
    def clean_expired_signals(self):
        """تنظيف الإشارات المنتهية الصلاحية"""
        current_time = datetime.now()
        expired_keys = []
        
        for signal_key, signal_data in self.pending_signals.items():
            time_diff = (current_time - signal_data['created_at']).total_seconds()
            if time_diff > self.config['CONFIRMATION_TIMEOUT']:
                expired_keys.append(signal_key)
                self.logger.info(f"🗑️  تنظيف إشارات منتهية: {signal_key}")
        
        for key in expired_keys:
            del self.pending_signals[key]
    
    def open_confirmed_trade(self, signal_key, signal_category):
        """فتح صفقة مؤكدة"""
        pending_data = self.pending_signals[signal_key]
        main_signal = pending_data['signals_data'][0]
        
        trade_id = str(uuid.uuid4())[:8]
        direction = 'CALL' if signal_category == 'entry_bullish' else 'PUT'
        
        trade_info = {
            'trade_id': trade_id,
            'ticker': main_signal['ticker'],
            'direction': direction,
            'signal_type': main_signal['signal_type'],
            'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'OPEN',
            'confirmation_count': len(pending_data['unique_signals'])
        }
        
        self.active_trades[trade_id] = trade_info
        
        # إرسال إشعار الدخول بالنموذج المطلوب
        if self.config['SEND_ENTRY_MESSAGES']:
            message = self.format_entry_message(trade_info, pending_data)
            self.send_telegram(message)
        
        # تنظيف الإشارات المعلقة
        del self.pending_signals[signal_key]
        
        self.logger.info(f"📈 فتح صفقة {direction} (#{trade_id}) بـ {trade_info['confirmation_count']} إشارات")
        return True
    
    def handle_exit_signal(self, signal_data):
        """معالجة إشارات الخروج"""
        trade = self.find_active_trade(signal_data['ticker'])
        if not trade:
            self.logger.warning(f"⚠️  لا توجد صفقة نشطة للرمز {signal_data['ticker']}")
            return False
        
        # إغلاق الصفقة
        trade.update({
            'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'CLOSED',
            'exit_signal': signal_data['signal_type']
        })
        
        # إرسال إشعار الخروج
        if self.config['SEND_EXIT_MESSAGES']:
            message = self.format_exit_message(trade)
            self.send_telegram(message)
        
        self.logger.info(f"📉 إغلاق صفقة #{trade['trade_id']}")
        return True
    
    def handle_trend_confirmation(self, signal_data):
        """معالجة تأكيد الاتجاه"""
        if self.config['SEND_CONFIRMATION_MESSAGES']:
            message = self.format_confirmation_message(signal_data)
            self.send_telegram(message)
        
        self.logger.info(f"✅ تأكيد اتجاه: {signal_data['signal_type']}")
        return True
    
    def handle_general_signal(self, signal_data):
        """معالجة الإشارات العامة"""
        if self.config['SEND_GENERAL_MESSAGES']:
            message = self.format_general_message(signal_data)
            self.send_telegram(message)
        
        self.logger.info(f"🔔 إشارة عامة: {signal_data['signal_type']}")
        return True
    
    def find_active_trade(self, ticker):
        """البحث عن صفقة نشطة"""
        for trade in self.active_trades.values():
            if trade['ticker'] == ticker and trade['status'] == 'OPEN':
                return trade
        return None
    
    def should_send_message(self, message_type, signal_data=None):
        """التحقق مما إذا كان يجب إرسال الرسالة"""
        # التحكم العام في Telegram
        if not self.config['TELEGRAM_ENABLED']:
            return False
        
        # التحكم في أنواع الرسائل
        type_controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }
        
        if message_type not in type_controls or not type_controls[message_type]:
            return False
        
        # التحكم في أنواع الإشارات (bullish/bearish)
        if signal_data:
            signal_type = signal_data.get('signal_type', '').lower()
            direction = signal_data.get('direction', '')
            
            if ('bullish' in signal_type or direction == 'CALL') and not self.config['SEND_BULLISH_SIGNALS']:
                return False
            
            if ('bearish' in signal_type or direction == 'PUT') and not self.config['SEND_BEARISH_SIGNALS']:
                return False
        
        return True
    
    def send_telegram(self, message):
        """إرسال رسالة إلى Telegram"""
        if not self.config['TELEGRAM_ENABLED']:
            return False
            
        if not self.config['TELEGRAM_BOT_TOKEN'] or self.config['TELEGRAM_BOT_TOKEN'] == 'your_bot_token_here':
            print(f"📲 محاكاة إرسال Telegram:\n{message}")
            return True
        
        try:
            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            payload = {
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            success = response.status_code == 200
            
            if success:
                self.logger.info("✅ تم إرسال الرسالة إلى Telegram")
            else:
                self.logger.error(f"❌ فشل إرسال Telegram: {response.status_code}")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ خطأ في إرسال Telegram: {e}")
            return False
    
    # 🔧 دوال تنسيق الرسائل - محدثة حسب الطلب
    def format_trend_message(self, signal_data, trend_icon, trend_text):
        """تنسيق رسالة الاتجاه"""
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
        """تنسيق رسالة دخول الصفقة بالنموذج المطلوب"""
        ticker = trade_info['ticker']
        direction = trade_info['direction']
        
        if direction == 'CALL':
            direction_icon, direction_text = "🟢", "شراء"
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        else:
            direction_icon, direction_text = "🔴", "بيع"
            trend_icon, trend_text = "🔴📉", "بيع (اتجاه هابط)"
        
        # معالجة بيانات التأكيد
        confirm_count = len(confirmation_data['unique_signals'])
        secondary_signals = []
        
        # جمع الإشارات المساعدة (باستثناء الإشارة الرئيسية)
        main_signal = trade_info['signal_type']
        for signal in confirmation_data['unique_signals']:
            if signal != main_signal:
                secondary_signals.append(signal)
        
        secondary_count = len(secondary_signals)
        
        # بناء قائمة الإشارات المساعدة
        secondary_listing = ""
        for i, signal in enumerate(secondary_signals[:3], 1):
            clean_signal = signal.replace('+', '').replace('-', '')
            secondary_listing += f"┃   {i}. {clean_signal}\n"
        
        if secondary_count > 3:
            secondary_listing += f"┃   ... و{secondary_count - 3} إشارات أخرى\n"
        elif secondary_count == 0:
            secondary_listing = "┃    - لا توجد إشارات مساعدة\n"
        
        open_trades = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        max_open_trades = self.config['MAX_OPEN_TRADES']
        
        # تنظيف اسم الإشارة الرئيسية
        main_signal_clean = main_signal.replace('+', '').replace('-', '')
        
        message = f"""
✦✦✦ 🚀 دخـــــول صفـــــقة ✦✦✦
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {ticker}
┃ 🎯 نوع الصفقة: {direction_icon} {direction_text}
┃ 📊 الاتجاه الحالي: {trend_icon} {trend_text}
┃ 🎯 محاذاة الاتجاه: 🟢 مطابق للاتجاه العام
┃ 📋 الإشارة الرئيسية: {main_signal_clean} (تم التأكيد بـ {confirm_count} إشارات)
┃ 🔔 الإشارات المساعدة: {secondary_count} إشارة
{secondary_listing}┃ 📊 الصفقات المفتوحة: {open_trades} من {max_open_trades}
┗━━━━━━━━━━━━━━━━━━━━
🕐 {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}
        """.strip()
        
        return message
    
    def format_exit_message(self, trade_info):
        """تنسيق رسالة خروج الصفقة"""
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
        """تنسيق رسالة تأكيد الاتجاه"""
        if 'bullish' in signal_data['signal_type'].lower() or self.current_trend == 'BULLISH':
            trend_icon, trend_text = "🟢📈", "شراء (اتجاه صاعد)"
        elif 'bearish' in signal_data['signal_type'].lower() or self.current_trend == 'BEARISH':
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
        """تنسيق رسالة الإشارة العامة"""
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
    
    def get_system_status(self):
        """الحصول على حالة النظام"""
        active_trades = [t for t in self.active_trades.values() if t['status'] == 'OPEN']
        
        return {
            "status": "operational",
            "app_name": self.config['APP_NAME'],
            "app_version": self.config['APP_VERSION'],
            "active_trades": len(active_trades),
            "max_open_trades": self.config['MAX_OPEN_TRADES'],
            "pending_signals": len(self.pending_signals),
            "current_trend": self.current_trend,
            "required_confirmations": self.config['REQUIRED_CONFIRMATIONS'],
            "telegram_enabled": self.config['TELEGRAM_ENABLED'],
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
        """عرض الإشارات المحملة"""
        print("📋 الإشارات المحملة من ملف .env:")
        total_signals = 0
        for category, signals in self.signals.items():
            print(f"   {category}: {len(signals)} إشارة")
            total_signals += len(signals)
        print(f"   📈 الإجمالي: {total_signals} إشارة")
        
        # عرض بعض الإعدادات المهمة
        print("\n⚙️  الإعدادات المحملة:")
        print(f"   🔔 إشعارات الاتجاه: {'مفعّل' if self.config['SEND_TREND_MESSAGES'] else 'معطل'}")
        print(f"   🔔 إشعارات الدخول: {'مفعّل' if self.config['SEND_ENTRY_MESSAGES'] else 'معطل'}")
        print(f"   🔔 إشعارات الخروج: {'مفعّل' if self.config['SEND_EXIT_MESSAGES'] else 'معطل'}")
        print(f"   🔔 إشعارات عامة: {'مفعّل' if self.config['SEND_GENERAL_MESSAGES'] else 'معطل'}")
        print(f"   📊 التأكيدات المطلوبة: {self.config['REQUIRED_CONFIRMATIONS']}")
        print(f"   📈 الحد الأقصى للصفقات: {self.config['MAX_OPEN_TRADES']}")
    
    def handle_test(self, request):
        """معالجة صفحة الاختبار"""
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
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🧪 اختبار نظام إشارات التداول</h1>
                    <form method="POST">
                        <textarea name="signal" placeholder="Ticker : BTCUSDT Signal : bullish_catcher Open : 0 Close : 0" required>Ticker : SPX500 Signal : Bearish New Imbalance Open : 0 Close : 0</textarea>
                        <br>
                        <button type="submit">إرسال الإشارة</button>
                    </form>
                </div>
            </body>
            </html>
            '''
        else:
            signal = request.form.get('signal', '')
            success = self.process_signal(signal)
            
            if success:
                return f'''
                <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 5px;">
                    <h3>✅ تمت المعالجة بنجاح!</h3>
                    <p><strong>الإشارة:</strong> {signal}</p>
                </div>
                <a href="/test">⟲ اختبار إشارة أخرى</a>
                '''
            else:
                return f'''
                <div style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">
                    <h3>❌ فشل في المعالجة</h3>
                    <p><strong>الإشارة:</strong> {signal}</p>
                </div>
                <a href="/test">⟲ محاولة مرة أخرى</a>
                '''
    
    def run(self):
        """تشغيل التطبيق"""
        self.logger.info(f"🌐 بدء التشغيل على المنفذ {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=self.config['DEBUG'])

# الحل: إنشاء النظام وتعيين app لكائن Flask
system = TradingSystem()
app = system.app

if __name__ == '__main__':
    system.run()
