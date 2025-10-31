#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AbuRayan_Bot_V8.9_Controlled_Trades.py
Trading Signal Processing System - Full Trade Control with Dual Group Strategy
"""

import os
import json
import logging
import uuid
import re
import requests
import sys
import time
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# =============================
# Load Environment Variables
# =============================
load_dotenv()

class TradingSystem:
    """Main Integrated Trading Signal System with Full Trade Control"""

    def __init__(self):
        print("🚀 Starting Trading System Initialization...")
        self.setup_config()
        self.setup_managers()
        self.setup_flask()
        self.display_loaded_signals()
        self.check_settings()

    def setup_config(self):
        """Setup complete configuration from environment variables"""
        print("⚙️ Loading settings...")
        
        self.config = {
            # 🔧 Basic
            'APP_NAME': self.get_config_value('APP_NAME', 'TradingSignalProcessor'),
            'DEBUG': self.get_config_value('DEBUG', False, bool),
            'LOG_LEVEL': self.get_config_value('LOG_LEVEL', 'INFO'),

            # 📱 Telegram
            'TELEGRAM_ENABLED': self.get_config_value('TELEGRAM_ENABLED', True, bool),
            'TELEGRAM_BOT_TOKEN': self.get_config_value('TELEGRAM_BOT_TOKEN', ''),
            'TELEGRAM_CHAT_ID': self.get_config_value('TELEGRAM_CHAT_ID', ''),

            # 🌐 External Server
            'EXTERNAL_SERVER_ENABLED': self.get_config_value('EXTERNAL_SERVER_ENABLED', True, bool),
            'EXTERNAL_SERVER_URL': self.get_config_value('EXTERNAL_SERVER_URL', ''),

            # ⚙️ Confirmation and Trade Management
            'REQUIRED_CONFIRMATIONS': self.get_config_value('REQUIRED_CONFIRMATIONS', 3, int),
            'CONFIRMATION_TIMEOUT': self.get_config_value('CONFIRMATION_TIMEOUT', 1200, int),
            'MAX_OPEN_TRADES': self.get_config_value('MAX_OPEN_TRADES', 10, int),
            'MAX_TRADES_PER_SYMBOL': self.get_config_value('MAX_TRADES_PER_SYMBOL', 1, int),
            
            # 🆕 إعدادات احترام الاتجاه للمجموعتين
            'RESPECT_TREND_FOR_REGULAR_TRADES': self.get_config_value('RESPECT_TREND_FOR_REGULAR_TRADES', True, bool),
            'RESPECT_TREND_FOR_GROUP2': self.get_config_value('RESPECT_TREND_FOR_GROUP2', True, bool),  # ⭐ الجديد
            'RESET_TRADES_ON_TREND_CHANGE': self.get_config_value('RESET_TRADES_ON_TREND_CHANGE', True, bool),

            # 🆕 Dual Group Strategy
            'DUAL_CONFIRMATION_STRATEGY': self.get_config_value('DUAL_CONFIRMATION_STRATEGY', False, bool),
            'REQUIRED_CONFIRMATIONS_GROUP1': self.get_config_value('REQUIRED_CONFIRMATIONS_GROUP1', 2, int),
            'REQUIRED_CONFIRMATIONS_GROUP2': self.get_config_value('REQUIRED_CONFIRMATIONS_GROUP2', 1, int),
            'DUAL_CONFIRMATION_TIMEOUT': self.get_config_value('DUAL_CONFIRMATION_TIMEOUT', 1800, int),

            # 🔔 Send Control
            'SEND_TREND_MESSAGES': self.get_config_value('SEND_TREND_MESSAGES', True, bool),
            'SEND_ENTRY_MESSAGES': self.get_config_value('SEND_ENTRY_MESSAGES', True, bool),
            'SEND_EXIT_MESSAGES': self.get_config_value('SEND_EXIT_MESSAGES', True, bool),
            'SEND_CONFIRMATION_MESSAGES': self.get_config_value('SEND_CONFIRMATION_MESSAGES', True, bool),
            'SEND_GENERAL_MESSAGES': self.get_config_value('SEND_GENERAL_MESSAGES', False, bool),
            'SEND_BULLISH_SIGNALS': self.get_config_value('SEND_BULLISH_SIGNALS', True, bool),
            'SEND_BEARISH_SIGNALS': self.get_config_value('SEND_BEARISH_SIGNALS', True, bool),
        }

        self.port = self.get_config_value('PORT', 10000, int)

        # Load signals
        print("📥 Loading signal lists from environment variables...")
        self.signals = {
            'trend': self._load_signal_list('TREND_SIGNALS'),
            'trend_confirm': self._load_signal_list('TREND_CONFIRM_SIGNALS'),
            'entry_bullish': self._load_signal_list('ENTRY_SIGNALS_BULLISH'),
            'entry_bearish': self._load_signal_list('ENTRY_SIGNALS_BEARISH'),
            'exit': self._load_signal_list('EXIT_SIGNALS'),
            'general': self._load_signal_list('GENERAL_SIGNALS'),
            'entry_bullish1': self._load_signal_list('ENTRY_SIGNALS_BULLISH1'),
            'entry_bearish1': self._load_signal_list('ENTRY_SIGNALS_BEARISH1')
        }

        self.setup_keywords()
        self.setup_signal_index()

    def get_config_value(self, key, default=None, cast_type=str):
        """Get configuration value from environment variables"""
        try:
            value = os.environ.get(key)
            if value is None:
                print(f"   ⚠️ {key}: Using default value '{default}'")
                return default
            
            print(f"   ✅ {key}: '{value}'")
                
            if cast_type == bool:
                return value.lower() in ('true', '1', 'yes', 'y', 'on')
            elif cast_type == int:
                return int(value)
            elif cast_type == float:
                return float(value)
            else:
                return str(value)
                
        except Exception as e:
            print(f"⚠️ Warning: Error reading setting {key}: {e}, using default: {default}")
            return default

    def _load_signal_list(self, key):
        """Load signal list with loading details"""
        try:
            signal_str = os.environ.get(key, '')
            if not signal_str:
                print(f"   📭 {key}: Empty")
                return []
            
            signals = [s.strip() for s in signal_str.split(',') if s.strip()]
            print(f"   ✅ {key}: {len(signals)} signals - {signals}")
            return signals
            
        except Exception as e:
            print(f"   ❌ Error loading {key}: {e}")
            return []

    def setup_keywords(self):
        """تحميل الكلمات المفتاحية من ملف .env - إنجليزية فقط"""
        
        print("📖 جاري تحميل الكلمات المفتاحية من إعدادات البيئة...")
        
        self.keywords = {
            'bullish': self._load_keywords_from_env('BULLISH_KEYWORDS'),
            'bearish': self._load_keywords_from_env('BEARISH_KEYWORDS'),
            'trend': self._load_keywords_from_env('TREND_KEYWORDS'),
            'trend_confirm': self._load_keywords_from_env('TREND_CONFIRM_KEYWORDS'),
            'exit': self._load_keywords_from_env('EXIT_KEYWORDS')
        }
        
        self._display_loaded_keywords()

    def _load_keywords_from_env(self, env_key):
        """تحميل قائمة الكلمات المفتاحية من متغير بيئة"""
        try:
            keywords_str = os.environ.get(env_key, '')
            if not keywords_str:
                print(f"   ⚠️ {env_key}: فارغ - سيتم استخدام القيمة الافتراضية")
                return self._get_default_keywords(env_key)
            
            # تقسيم الكلمات بالفاصلة وإزالة المسافات
            keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            print(f"   ✅ {env_key}: تم تحميل {len(keywords)} كلمة")
            return keywords
            
        except Exception as e:
            print(f"   ❌ خطأ في تحميل {env_key}: {e}")
            return self._get_default_keywords(env_key)

    def _get_default_keywords(self, env_key):
        """الحصول على القيم الافتراضية للكلمات المفتاحية (إنجليزية فقط)"""
        default_keywords = {
            'BULLISH_KEYWORDS': [
                'bullish', 'bull', 'buy', 'long', 'call', 'up', 'upside', 
                'rising', 'rise', 'upward', 'positive', 'support', 'bounce',
                'recovery', 'rally', 'breakout', 'break up', 'strength',
                'accumulate', 'bull market', 'uptrend', 'green', 'gain',
                'higher', 'climb', 'surge', 'jump', 'soar', 'rebound'
            ],
            'BEARISH_KEYWORDS': [
                'bearish', 'bear', 'sell', 'short', 'put', 'down', 'downside',
                'falling', 'fall', 'downward', 'negative', 'resistance', 'drop',
                'decline', 'correction', 'breakdown', 'break down', 'weakness',
                'distribution', 'bear market', 'downtrend', 'red', 'loss',
                'lower', 'slide', 'plunge', 'crash', 'collapse', 'pullback'
            ],
            'TREND_KEYWORDS': [
                'catcher'  # القيمة الافتراضية المطلوبة
            ],
            'TREND_CONFIRM_KEYWORDS': [
                'tracer', 'confirmation', 'confirm', 'validation', 'valid',
                'confirmed', 'strength', 'weakness', 'follow through',
                'momentum confirmation', 'trend confirmation',
                'breakout confirmation', 'breakdown confirmation'
            ],
            'EXIT_KEYWORDS': [
                'exit', 'close', 'close position', 'take profit', 'stop loss',
                'tp', 'sl', 'target', 'profit taking', 'cut loss',
                'stop', 'stop out', 'liquidate', 'square off',
                'end trade', 'close trade', 'position close'
            ]
        }
        
        return default_keywords.get(env_key, [])

    def _display_loaded_keywords(self):
        """عرض الكلمات المفتاحية التي تم تحميلها"""
        print("\n📚 الكلمات المفتاحية المحملة (إنجليزية فقط):")
        for category, keywords in self.keywords.items():
            sample = keywords[:3]  # عرض أول 3 كلمات فقط كمثال
            print(f"   📁 {category}: {len(keywords)} كلمة - مثال: {sample}...")

    def setup_signal_index(self):
        """Create fast signal index"""
        self.signal_index = {}
        total_signals = 0
        
        for category, signals in self.signals.items():
            total_signals += len(signals)
            for signal in signals:
                normalized = self.normalize_signal(signal)
                self.signal_index[normalized] = category
                self.signal_index[signal] = category
        
        print(f"   🔍 Index ready: {len(self.signal_index)} entries from {total_signals} signals")

    def normalize_signal(self, signal):
        """Normalize signal for comparison"""
        return signal.lower().strip().replace(' ', '')

    def setup_managers(self):
        """Setup managers and variables"""
        self.pending_signals = {}
        self.active_trades = {}
        self.symbol_trends = {}
        self.signal_history = []

    def setup_flask(self):
        """Setup Flask application"""
        self.app = Flask(__name__)
        self.setup_routes()
        self.setup_logging()

    def setup_logging(self):
        """Setup logging system"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('trading_system')
        self.logger.setLevel(getattr(logging, self.config['LOG_LEVEL'], logging.INFO))

    def setup_routes(self):
        """Setup web routes"""
        @self.app.route('/')
        def home():
            return jsonify({"status": "active", "service": self.config['APP_NAME']})

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
    # Core Signal Processing
    # =============================

    def handle_webhook(self, request):
        """Process Webhook requests"""
        try:
            raw_signal = self.extract_signal_data(request)
            
            if not raw_signal or not self.validate_signal_content(raw_signal):
                return jsonify({"status": "error", "message": "Invalid signal"}), 400

            self.logger.info(f"Signal received: {raw_signal}")
            self.record_signal_history(raw_signal)
            
            success = self.process_signal(raw_signal)
            return jsonify({"status": "success" if success else "error"})

        except Exception as e:
            self.logger.error(f"Webhook error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def extract_signal_data(self, request):
        """Extract signal data"""
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            data = request.get_json(silent=True)
            if data:
                return self.convert_json_to_signal(data)
        
        return request.get_data(as_text=True).strip()

    def convert_json_to_signal(self, data):
        """Convert JSON to signal text"""
        if isinstance(data, dict):
            ticker = data.get('ticker', data.get('symbol', 'UNKNOWN'))
            signal_type = data.get('signal', data.get('action', 'UNKNOWN'))
            return f"Ticker : {ticker} Signal : {signal_type}"
        return str(data)

    def validate_signal_content(self, raw_signal):
        """Validate signal content"""
        return bool(raw_signal and len(raw_signal.strip()) > 0 and len(raw_signal) <= 10000)

    def record_signal_history(self, raw_signal):
        """Record signal in history"""
        self.signal_history.append({
            'timestamp': datetime.now(),
            'signal': raw_signal[:100],
            'processed': False
        })
        
        if len(self.signal_history) > 500:
            self.signal_history = self.signal_history[-500:]

    def process_signal(self, raw_signal):
        """Main signal processing"""
        signal_data = self.parse_signal(raw_signal)
        if not signal_data:
            return False

        category = self.classify_signal(signal_data)
        signal_data['category'] = category

        # Update history
        for record in self.signal_history[-5:]:
            if record['signal'].startswith(raw_signal[:50]):
                record.update({'processed': True, 'category': category})
                break

        print(f"🎯 Signal classification: '{signal_data['signal_type']}' -> '{category}'")

        # Route by type
        handlers = {
            'trend': self.handle_trend_signal,
            'trend_confirm': self.handle_trend_confirmation,
            'exit': self.handle_exit_signal,
            'unknown': self.handle_unknown_signal,
            'general': self.handle_general_signal
        }
        
        if category in ('entry_bullish', 'entry_bearish', 'entry_bullish1', 'entry_bearish1'):
            return self.handle_entry_signal(signal_data, category)
        else:
            handler = handlers.get(category, self.handle_general_signal)
            return handler(signal_data)

    def parse_signal(self, raw_signal):
        """Parse signal text"""
        try:
            text = raw_signal.strip()
            if not text:
                return None
            
            # Main pattern
            pattern = r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+)'
            match = re.match(pattern, text)
            if match:
                ticker, signal_type = match.groups()
                return {
                    'ticker': ticker.strip(),
                    'signal_type': signal_type.strip(),
                    'original_signal': signal_type,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            # Alternative pattern
            pattern2 = r'([A-Za-z0-9]+)\s+(.+)'
            match2 = re.match(pattern2, text)
            if match2:
                ticker, signal_type = match2.groups()
                return {
                    'ticker': ticker.strip(),
                    'signal_type': signal_type.strip(),
                    'original_signal': signal_type.strip(),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            return {
                'ticker': "UNKNOWN",
                'signal_type': text,
                'original_signal': text,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
                
        except Exception as e:
            self.logger.error(f"Signal parsing error: {e}")
            return None

    def classify_signal(self, signal_data):
        """Classify signal"""
        signal_type = signal_data['signal_type']
        signal_lower = signal_type.lower()
        
        print(f"🔍 Classifying signal: '{signal_type}'")
        
        # Keywords first
        if any(keyword in signal_lower for keyword in self.keywords['trend_confirm']):
            print("✅ Classified as 'trend_confirm' based on keywords")
            return 'trend_confirm'
        if any(keyword in signal_lower for keyword in self.keywords['trend']):
            print("✅ Classified as 'trend' based on keywords")
            return 'trend'
        
        # Exact match
        if signal_type in self.signal_index:
            category = self.signal_index[signal_type]
            print(f"✅ Classified as '{category}' based on exact match")
            return category
        
        # Normalized match
        normalized = self.normalize_signal(signal_type)
        if normalized in self.signal_index:
            category = self.signal_index[normalized]
            print(f"✅ Classified as '{category}' based on normalized match")
            return category
        
        # Keyword-based classification
        for category, keywords in self.keywords.items():
            if any(keyword in signal_lower for keyword in keywords):
                print(f"✅ Classified as '{category}' based on general keywords")
                return category
        
        print("❌ Signal not recognized - classified as 'unknown'")
        return 'unknown'

    # =============================
    # Signal Handlers
    # =============================

    def handle_trend_signal(self, signal_data):
        """Handle trend signals"""
        symbol = signal_data['ticker']
        signal_lower = signal_data['original_signal'].lower()
        
        # Determine new trend
        if any(keyword in signal_lower for keyword in self.keywords['bullish']):
            new_trend = 'BULLISH'
        elif any(keyword in signal_lower for keyword in self.keywords['bearish']):
            new_trend = 'BEARISH'
        else:
            return False

        current_trend = self.symbol_trends.get(symbol)
        
        # Ignore if trend hasn't changed
        if current_trend == new_trend:
            print(f"🔄 Ignoring duplicate trend signal: {symbol} still {current_trend}")
            return True
        
        print(f"🔧 Changing trend {symbol} from {current_trend} to {new_trend}")
        
        # Close trades if setting enabled
        if self.config['RESET_TRADES_ON_TREND_CHANGE']:
            self.close_all_trades_for_symbol(symbol, f"Trend change from {current_trend} to {new_trend}")
        
        # 🆕 Reset group2 signals when trend changes
        self.reset_group2_signals(symbol)
        
        # Update trend
        self.symbol_trends[symbol] = new_trend

        # Send notification
        msg = self.format_trend_message(signal_data, new_trend, current_trend)
        self.send_notifications(msg, 'trend', signal_data)
        
        self.logger.info(f"Trend change {symbol}: {current_trend} -> {new_trend}")
        return True

    def handle_trend_confirmation(self, signal_data):
        """Handle trend confirmation"""
        symbol = signal_data['ticker']
        signal_lower = signal_data['original_signal'].lower()
        
        # Determine signal trend
        if any(keyword in signal_lower for keyword in self.keywords['bullish']):
            signal_trend = 'BULLISH'
        elif any(keyword in signal_lower for keyword in self.keywords['bearish']):
            signal_trend = 'BEARISH'
        else:
            return False

        # Check trend match
        current_trend = self.symbol_trends.get(symbol)
        if current_trend != signal_trend:
            print(f"❌ Ignoring non-matching trend confirmation: {symbol} ({signal_trend}) doesn't match ({current_trend})")
            return False

        print(f"✅ Matching trend confirmation: {symbol} ({signal_trend})")
        # Send trend confirmation
        msg = self.format_trend_confirmation_message(signal_data, signal_trend)
        self.send_notifications(msg, 'confirmation', signal_data)
        
        return True

    def handle_entry_signal(self, signal_data, signal_category):
        """Handle entry signals"""
        symbol = signal_data['ticker']

        # Check if new trade can be opened
        if not self.can_open_new_trade(symbol):
            active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
            total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
            
            self.logger.warning(
                f"Ignoring trade opening: Trade limits reached - "
                f"{symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']}, "
                f"Total: {total_active}/{self.config['MAX_OPEN_TRADES']}"
            )
            return False

        # Check trend
        symbol_trend = self.symbol_trends.get(symbol)
        if self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and symbol_trend:
            expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
            if symbol_trend != expected_trend:
                print(f"❌ Rejecting trade: {signal_category} signal against {symbol_trend} trend for {symbol}")
                return False
            else:
                print(f"✅ Trade matches trend: {signal_category} with {symbol_trend}")

        # Choose strategy
        if self.config['DUAL_CONFIRMATION_STRATEGY']:
            return self.handle_dual_confirmation(signal_data, symbol, signal_category)
        else:
            return self.handle_single_confirmation(signal_data, symbol, signal_category)

    def handle_dual_confirmation(self, signal_data, symbol, signal_category):
        """Handle dual confirmation strategy with trend control for both groups"""
        # Determine group type
        group_type = 'group1' if signal_category in ['entry_bullish', 'entry_bearish'] else 'group2'
        key = f"{symbol}_{signal_category}_{group_type}"
        
        self.clean_expired_signals()

        # Create/update group
        if key not in self.pending_signals:
            self.pending_signals[key] = self.create_signal_group(signal_category, group_type)

        group = self.pending_signals[key]
        clean_type = self.normalize_signal(signal_data['signal_type'])

        # Add unique signal
        if clean_type not in group['unique_signals']:
            group['unique_signals'].add(clean_type)
            group['signals_data'].append(signal_data)
            group['updated_at'] = datetime.now()
            
            print(f"✅ Adding unique signal to group {group_type}: '{signal_data['signal_type']}'")
            
            # 🆕 التحقق من الاتجاه بناءً على نوع المجموعة والإعدادات
            symbol_trend = self.symbol_trends.get(symbol)
            if symbol_trend:
                if group_type == 'group1' and self.config['RESPECT_TREND_FOR_REGULAR_TRADES']:
                    if not self.check_trend_match(signal_category, symbol_trend):
                        print(f"❌ Rejecting group1 signal: {signal_category} against trend {symbol_trend}")
                        group['unique_signals'].remove(clean_type)
                        group['signals_data'].pop()
                        return True
                        
                elif group_type == 'group2' and self.config['RESPECT_TREND_FOR_GROUP2']:
                    if not self.check_trend_match(signal_category, symbol_trend):
                        print(f"❌ Rejecting group2 signal: {signal_category} against trend {symbol_trend}")
                        group['unique_signals'].remove(clean_type)
                        group['signals_data'].pop()
                        return True
                        
                else:
                    print(f"✅ Trend check skipped for {group_type} based on settings")
                    
        else:
            print(f"🔄 Ignoring duplicate signal for group {group_type}: '{signal_data['signal_type']}'")
            return True

        # Check conditions
        return self.check_dual_conditions(symbol, signal_category)

    def handle_single_confirmation(self, signal_data, symbol, signal_category):
        """Handle single confirmation strategy"""
        key = f"{symbol}_{signal_category}"
        self.clean_expired_signals()

        if key not in self.pending_signals:
            self.pending_signals[key] = self.create_signal_group(signal_category)

        group = self.pending_signals[key]
        clean_type = self.normalize_signal(signal_data['signal_type'])

        # Add unique signal
        if clean_type not in group['unique_signals']:
            group['unique_signals'].add(clean_type)
            group['signals_data'].append(signal_data)
            group['updated_at'] = datetime.now()
            print(f"✅ Adding unique signal: '{signal_data['signal_type']}'")
        else:
            print(f"🔄 Ignoring duplicate signal: '{signal_data['signal_type']}'")
            return True

        # Open trade if conditions met
        if len(group['unique_signals']) >= self.config['REQUIRED_CONFIRMATIONS']:
            return self.open_confirmed_trade(key, signal_category)
        
        print(f"📊 Waiting for confirmation: {len(group['unique_signals'])}/{self.config['REQUIRED_CONFIRMATIONS']}")
        return True

    def handle_exit_signal(self, signal_data):
        """Handle exit signals"""
        trade = self.find_active_trade(signal_data['ticker'])
        if not trade:
            self.logger.warning(f"No active trade for symbol {signal_data['ticker']}")
            return False

        # Update trade
        trade.update({
            'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'CLOSED',
            'exit_signal': signal_data['signal_type']
        })

        # Send exit notification
        msg = self.format_exit_message(trade)
        self.send_notifications(msg, 'exit', {'signal_type': trade.get('exit_signal', '')})
        
        print(f"✅ Closing trade #{trade['trade_id']}")
        return True

    def handle_unknown_signal(self, signal_data):
        """Handle unknown signals"""
        self.logger.warning(f"Unknown signal: '{signal_data['signal_type']}' for symbol {signal_data['ticker']}")
        return False

    def handle_general_signal(self, signal_data):
        """Handle general signals"""
        msg = self.format_general_message(signal_data)
        self.send_notifications(msg, 'general', signal_data)
        return True

    # =============================
    # Trade Management
    # =============================

    def get_active_trades_for_symbol(self, symbol):
        """Get active trades for symbol"""
        return [trade for trade in self.active_trades.values() 
                if trade['ticker'].upper() == symbol.upper() and trade['status'] == 'OPEN']

    def find_active_trade(self, ticker):
        """Find active trade"""
        active_trades = self.get_active_trades_for_symbol(ticker)
        return active_trades[0] if active_trades else None

    def can_open_new_trade(self, symbol):
        """Check if new trade can be opened"""
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        symbol_ok = active_for_symbol < self.config['MAX_TRADES_PER_SYMBOL']
        total_ok = total_active < self.config['MAX_OPEN_TRADES']
        
        if not symbol_ok:
            print(f"❌ Max trades for symbol {symbol} reached: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']}")
        if not total_ok:
            print(f"❌ Total max trades reached: {total_active}/{self.config['MAX_OPEN_TRADES']}")
        
        return symbol_ok and total_ok

    def close_all_trades_for_symbol(self, symbol, reason):
        """Close all trades for symbol"""
        active_trades = self.get_active_trades_for_symbol(symbol)
        
        if not active_trades:
            print(f"📭 No open trades for symbol {symbol}")
            return

        print(f"🔻 Closing {len(active_trades)} trades for {symbol} due to {reason}")
        
        for trade in active_trades:
            trade.update({
                'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'CLOSED',
                'exit_signal': f"Auto close - {reason}",
                'auto_closed': True
            })
            
            msg = self.format_auto_close_message(trade, reason)
            self.send_notifications(msg, 'exit', {'signal_type': trade.get('exit_signal', '')})
            print(f"🔻 Closing trade #{trade['trade_id']}")

    # =============================
    # Dual Strategy
    # =============================

    def create_signal_group(self, signal_category, group_type=None):
        """Create new signal group"""
        return {
            'unique_signals': set(),
            'signals_data': [],
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'signal_category': signal_category,
            'group_type': group_type
        }

    def check_trend_match(self, signal_category, symbol_trend):
        """Check trend match"""
        is_bullish = 'bullish' in signal_category
        expected_trend = 'BULLISH' if is_bullish else 'BEARISH'
        return symbol_trend == expected_trend

    def reset_group2_signals(self, symbol):
        """Reset (clear) all pending group2 signals for a symbol when trend changes"""
        if not symbol:
            return

        print(f"🔄 تصفير إشارات المجموعة الثانية للرمز {symbol} بسبب تغيير الاتجاه...")
        
        # البحث عن جميع المفاتيح الخاصة بالمجموعة الثانية لهذا الرمز
        keys_to_delete = []
        for key in self.pending_signals.keys():
            # التحقق إذا كان المفتاح يحتوي على الرمز والمجموعة الثانية
            if symbol in key and ('group2' in key or 'bearish1' in key or 'bullish1' in key):
                keys_to_delete.append(key)
        
        # حذف المفاتيح التي وجدناها
        deleted_count = 0
        for key in keys_to_delete:
            group_data = self.pending_signals[key]
            signal_count = len(group_data['unique_signals'])
            del self.pending_signals[key]
            deleted_count += 1
            print(f"   🗑️ تم حذف مجموعة {key} تحتوي على {signal_count} إشارة")
        
        if deleted_count > 0:
            print(f"✅ تم تصفير {deleted_count} مجموعة من المجموعة الثانية للرمز {symbol}")
        else:
            print(f"📭 لا توجد إشارات للمجموعة الثانية للرمز {symbol} لتصفيرها")

    def check_dual_conditions(self, symbol, signal_category):
        """Check dual strategy conditions with trend control for both groups"""
        base_category = 'entry_bullish' if 'bullish' in signal_category else 'entry_bearish'
        group1_key = f"{symbol}_{base_category}_group1"
        group2_key = f"{symbol}_{base_category}1_group2"

        # 🆕 التحقق النهائي من الاتجاه مع مراعاة إعدادات كل مجموعة
        symbol_trend = self.symbol_trends.get(symbol)
        if symbol_trend:
            expected_trend = 'BULLISH' if base_category == 'entry_bullish' else 'BEARISH'
            
            # إذا كانت كلا المجموعتين تحترمان الاتجاه
            if self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and self.config['RESPECT_TREND_FOR_GROUP2']:
                if symbol_trend != expected_trend:
                    print(f"❌ Rejecting trade opening: Current trend {symbol_trend} doesn't match signal {expected_trend}")
                    self.pending_signals.pop(group1_key, None)
                    self.pending_signals.pop(group2_key, None)
                    return False
                    
            # إذا كانت المجموعة الأولى فقط تحترم الاتجاه
            elif self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and not self.config['RESPECT_TREND_FOR_GROUP2']:
                group1_ready = self.check_group_ready(group1_key, self.config['REQUIRED_CONFIRMATIONS_GROUP1'])
                if group1_ready and symbol_trend != expected_trend:
                    print(f"❌ Rejecting trade opening: Group1 requires trend match - {symbol_trend} vs {expected_trend}")
                    self.pending_signals.pop(group1_key, None)
                    self.pending_signals.pop(group2_key, None)
                    return False
                    
            # إذا كانت المجموعة الثانية فقط تحترم الاتجاه  
            elif not self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and self.config['RESPECT_TREND_FOR_GROUP2']:
                group2_ready = self.check_group_ready(group2_key, self.config['REQUIRED_CONFIRMATIONS_GROUP2'])
                if group2_ready and symbol_trend != expected_trend:
                    print(f"❌ Rejecting trade opening: Group2 requires trend match - {symbol_trend} vs {expected_trend}")
                    self.pending_signals.pop(group1_key, None)
                    self.pending_signals.pop(group2_key, None)
                    return False

        # Check both groups readiness
        group1_ready = self.check_group_ready(group1_key, self.config['REQUIRED_CONFIRMATIONS_GROUP1'])
        group2_ready = self.check_group_ready(group2_key, self.config['REQUIRED_CONFIRMATIONS_GROUP2'])

        if group1_ready and group2_ready:
            return self.open_dual_confirmed_trade(symbol, base_category, group1_key, group2_key)
        
        # Show progress
        group1_count = len(self.pending_signals[group1_key]['unique_signals']) if group1_key in self.pending_signals else 0
        group2_count = len(self.pending_signals[group2_key]['unique_signals']) if group2_key in self.pending_signals else 0
        
        print(f"📊 Dual confirmation progress - {symbol}:")
        print(f"   📁 Group 1: {group1_count}/{self.config['REQUIRED_CONFIRMATIONS_GROUP1']}")
        print(f"   📁 Group 2: {group2_count}/{self.config['REQUIRED_CONFIRMATIONS_GROUP2']}")
        print(f"   📈 Trend Settings - Group1: {self.config['RESPECT_TREND_FOR_REGULAR_TRADES']}, Group2: {self.config['RESPECT_TREND_FOR_GROUP2']}")
        
        return True

    def check_group_ready(self, group_key, required_count):
        """Check group readiness"""
        if group_key not in self.pending_signals:
            return False
        return len(self.pending_signals[group_key]['unique_signals']) >= required_count

    def open_dual_confirmed_trade(self, symbol, base_category, group1_key, group2_key):
        """Open dual confirmed trade"""
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

        # Send entry message
        msg = self.format_dual_entry_message(trade_info, group1_data, group2_data)
        self.send_notifications(msg, 'entry', {'signal_type': trade_info['signal_type'], 'direction': direction})

        # Clean groups
        del self.pending_signals[group1_key]
        del self.pending_signals[group2_key]

        # Show trade statistics
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        print(f"📊 Trade statistics: {symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']} | Total: {total_active}/{self.config['MAX_OPEN_TRADES']}")
        
        self.logger.info(f"Opened {direction} trade #{trade_id} with dual strategy")
        return True

    def open_confirmed_trade(self, key, category):
        """Open confirmed trade"""
        data = self.pending_signals[key]
        if len(data['unique_signals']) < self.config['REQUIRED_CONFIRMATIONS']:
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
        self.send_notifications(msg, 'entry', {'signal_type': trade_info['signal_type'], 'direction': direction})

        del self.pending_signals[key]
        
        # Show trade statistics
        symbol = main_signal['ticker']
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])
        
        print(f"📊 Trade statistics: {symbol}: {active_for_symbol}/{self.config['MAX_TRADES_PER_SYMBOL']} | Total: {total_active}/{self.config['MAX_OPEN_TRADES']}")
        
        self.logger.info(f"Opened {direction} trade #{trade_id}")
        return True

    def clean_expired_signals(self):
        """Clean expired signals"""
        now = datetime.now()
        timeout = self.config['DUAL_CONFIRMATION_TIMEOUT'] if self.config['DUAL_CONFIRMATION_STRATEGY'] else self.config['CONFIRMATION_TIMEOUT']
        
        expired_keys = [
            key for key, data in self.pending_signals.items()
            if (now - data.get('updated_at', data['created_at'])).total_seconds() > timeout
        ]
        
        for key in expired_keys:
            group_type = self.pending_signals[key].get('group_type', 'unknown')
            signal_count = len(self.pending_signals[key]['unique_signals'])
            del self.pending_signals[key]
            print(f"🗑️ Cleaning expired group: {key} ({group_type}) - {signal_count} signals")

    # =============================
    # Notifications and Sending
    # =============================

    def should_send_message(self, message_type, signal_data=None):
        """Check if message should be sent"""
        type_controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }
        
        if not type_controls.get(message_type, False):
            print(f"🔕 {message_type} messages disabled")
            return False

        if signal_data:
            signal_text = str(signal_data.get('signal_type', '')).lower()
            direction = signal_data.get('direction', '').upper()
            
            if ('bullish' in signal_text or direction == 'CALL') and not self.config['SEND_BULLISH_SIGNALS']:
                print("🔕 Bullish signals disabled")
                return False
            if ('bearish' in signal_text or direction == 'PUT') and not self.config['SEND_BEARISH_SIGNALS']:
                print("🔕 Bearish signals disabled")
                return False

        return True

    def send_notifications(self, message, message_type, signal_data=None):
        """Send notifications"""
        if not self.should_send_message(message_type, signal_data):
            return

        # Send Telegram
        if self.config['TELEGRAM_ENABLED']:
            telegram_sent = self.send_telegram(message)
            if telegram_sent:
                print(f"✅ [Telegram] Sent {message_type} message")

        # Send to external server
        if self.config['EXTERNAL_SERVER_ENABLED']:
            external_sent = self.send_to_external_server_with_retry(message, message_type)
            if external_sent:
                print(f"✅ [Server] Sent {message_type} message")

    def send_telegram(self, message):
        """Send to Telegram"""
        token = self.config['TELEGRAM_BOT_TOKEN']
        chat_id = self.config['TELEGRAM_CHAT_ID']
        
        if not token or not chat_id:
            return False

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"💥 Telegram send error: {e}")
            return False

    def send_to_external_server_with_retry(self, message_text, message_type, max_retries=2):
        """Send with retry"""
        for attempt in range(max_retries + 1):
            if self.send_to_external_server(message_text, message_type):
                return True
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"🔄 Retrying in {wait_time} seconds... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
        return False

    def send_to_external_server(self, message_text, message_type):
        """Send to external server"""
        url = self.config['EXTERNAL_SERVER_URL']
        if not url:
            return False
            
        try:
            response = requests.post(
                url,
                data=message_text.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=10,
            )
            return response.status_code in (200, 201, 204)
        except Exception as e:
            print(f"💥 External server send error: {e}")
            return False

    # =============================
    # Message Templates (Arabic)
    # =============================

    def format_trend_message(self, signal_data, new_trend, old_trend):
        """Format trend message - Arabic"""
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        
        trend_icon, trend_text = ("🟢📈", "شراء (اتجاه صاعد)") if new_trend == 'BULLISH' else ("🔴📉", "بيع (اتجاه هابط)")
        
        return f"""☰☰☰ 📊 تغيير الاتجاه ☰☰☰
┏━━━━━━━━━━━━━━━━━━━━
┃ 💰 الرمز: {symbol}
┃ 📈 الاتجاه: {trend_icon} {trend_text}
┃ 📋 الإشارة: {signal}
┃ 🔄 الحالة: تغيير اتجاه ({old_trend or 'لا يوجد'} → {new_trend})
┗━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp}"""

    def format_trend_confirmation_message(self, signal_data, signal_trend):
        """Format trend confirmation message - Arabic"""
        symbol = signal_data['ticker']
        signal = signal_data['signal_type']
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        
        trend_icon, trend_text = ("🟢📈", "شراء (اتجاه صاعد)") if signal_trend == 'BULLISH' else ("🔴📉", "بيع (اتجاه هابط)")
        
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
        """Format entry message - Arabic"""
        symbol = trade_info['ticker']
        direction = trade_info['direction']
        signal = trade_info['signal_type']
        confirmations = trade_info.get('confirmation_count', 1)
        helpers = trade_info.get('confirmed_signals', [])
        trend = self.symbol_trends.get(symbol, '')
        trend_icon = '🟢📈 BULLISH' if trend == 'BULLISH' else '🔴📉 BEARISH'
        
        align_text = '🟢 مطابق للاتجاه العام' if (
            (direction == 'CALL' and trend == 'BULLISH') or 
            (direction == 'PUT' and trend == 'BEARISH')
        ) else '🔴 غير مطابق'
        
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])

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
        """Format dual entry message - Arabic"""
        symbol = trade_info['ticker']
        direction = trade_info['direction']
        signal = trade_info['signal_type']
        confirmations1 = trade_info.get('confirmation_count_group1', 0)
        confirmations2 = trade_info.get('confirmation_count_group2', 0)
        helpers1 = trade_info.get('confirmed_signals_group1', [])
        helpers2 = trade_info.get('confirmed_signals_group2', [])
        trend = self.symbol_trends.get(symbol, '')
        trend_icon = '🟢📈 BULLISH' if trend == 'BULLISH' else '🔴📉 BEARISH'
        
        align_text = '🟢 مطابق للاتجاه العام' if (
            (direction == 'CALL' and trend == 'BULLISH') or 
            (direction == 'PUT' and trend == 'BEARISH')
        ) else '🔴 غير مطابق'
        
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        active_for_symbol = len(self.get_active_trades_for_symbol(symbol))
        total_active = len([t for t in self.active_trades.values() if t['status'] == 'OPEN'])

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
        """Format exit message - Arabic"""
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
        """Format auto close message - Arabic"""
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
        """Format general message - Arabic"""
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
    # Helper Tools
    # =============================

    def get_system_status(self):
        """Get system status"""
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

    def display_loaded_signals(self):
        """Display loaded signals"""
        print("\n📊 Loaded Signals:")
        for category, signals in self.signals.items():
            print(f"   📁 {category}: {len(signals)} signals")

    def check_settings(self):
        """Check settings"""
        print(f"\n🔍 System Settings:")
        print(f"📊 Trade Management:")
        print(f"   • Max Open Trades: {self.config['MAX_OPEN_TRADES']}")
        print(f"   • Max Trades Per Symbol: {self.config['MAX_TRADES_PER_SYMBOL']}")
        
        if self.config['DUAL_CONFIRMATION_STRATEGY']:
            print("🎯 Dual Group Strategy:")
            print(f"   • Group 1: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']} signals")
            print(f"   • Group 2: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']} signals")
            print(f"   • Confirmation Timeout: {self.config['DUAL_CONFIRMATION_TIMEOUT']} seconds")
            print(f"   • Respect Trend for Group 1: {self.config['RESPECT_TREND_FOR_REGULAR_TRADES']}")
            print(f"   • Respect Trend for Group 2: {self.config['RESPECT_TREND_FOR_GROUP2']}")
            # 🆕 إضافة إعداد تصفير المجموعة الثانية
            print(f"   • Reset Group2 Signals on Trend Change: Enabled")  # هذا الإعداد ثابت حالياً
        else:
            print(f"   • Required Confirmations: {self.config['REQUIRED_CONFIRMATIONS']}")
            print(f"   • Respect Trend for Trades: {self.config['RESPECT_TREND_FOR_REGULAR_TRADES']}")
        
        print(f"   • Close Trades on Trend Change: {'Enabled' if self.config['RESET_TRADES_ON_TREND_CHANGE'] else 'Disabled'}")
        
        print("🔑 Keywords Configuration:")
        for category, keywords in self.keywords.items():
            print(f"   • {category}: {len(keywords)} keywords")
        
        print("🔔 Notifications:")
        print(f"   • Trend Messages: {'Enabled' if self.config['SEND_TREND_MESSAGES'] else 'Disabled'}")
        print(f"   • Entry Messages: {'Enabled' if self.config['SEND_ENTRY_MESSAGES'] else 'Disabled'}")
        print(f"   • Exit Messages: {'Enabled' if self.config['SEND_EXIT_MESSAGES'] else 'Disabled'}")

# =============================
# Main Execution
# =============================

def create_app():
    """App creation function for Gunicorn"""
    system = TradingSystem()
    return system.app

if __name__ == '__main__':
    try:
        print("🚀 Starting Trading System...")
        system = TradingSystem()
        app = system.app
        
        print(f"🌐 Running server on port {system.port}...")
        app.run(host='0.0.0.0', port=system.port, debug=False)
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")

# Make app available for Gunicorn
system_instance = TradingSystem()
app = system_instance.app
