#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AbuRayan_Bot_V8_Controlled_Trades.py#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AbuRayan_Bot_V8_Controlled_Trades.py
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
        self.debug_pending_signals()

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
            
            # 🆕 Trading Strategy - الأسماء المحدثة
            'OPEN_TRADE_FROM_2_GROUP': self.get_config_value('OPEN_TRADE_FROM_2_GROUP', False, bool),
            'OPEN_TRADE_FROM_1_GROUP': self.get_config_value('OPEN_TRADE_FROM_1_GROUP', False, bool),
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

            # 🆕 Smart Settings
            'RESPECT_TREND_FOR_REGULAR_TRADES': self.get_config_value('RESPECT_TREND_FOR_REGULAR_TRADES', True, bool),
            'RESPECT_TREND_FOR_GROUP2': self.get_config_value('RESPECT_TREND_FOR_GROUP2', True, bool),
            'RESET_TRADES_ON_TREND_CHANGE': self.get_config_value('RESET_TRADES_ON_TREND_CHANGE', True, bool),
            'ENABLE_SMART_TIMING': self.get_config_value('ENABLE_SMART_TIMING', True, bool),
            'TREND_CONFIRMATION_DELAY': self.get_config_value('TREND_CONFIRMATION_DELAY', 2, int),
            'ENABLE_COUNTER_TREND_PRESERVATION': self.get_config_value('ENABLE_COUNTER_TREND_PRESERVATION', True, bool),
            'MAX_COUNTER_TREND_SAVE_TIME': self.get_config_value('MAX_COUNTER_TREND_SAVE_TIME', 600, int),
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
                return default
                
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
                return []
            
            signals = [s.strip() for s in signal_str.split(',') if s.strip()]
            return signals
            
        except Exception as e:
            print(f"   ❌ Error loading {key}: {e}")
            return []

    def setup_keywords(self):
        """Load keywords from environment"""
        self.keywords = {
            'bullish': self._load_keywords_from_env('BULLISH_KEYWORDS'),
            'bearish': self._load_keywords_from_env('BEARISH_KEYWORDS'),
            'trend': self._load_keywords_from_env('TREND_KEYWORDS'),
            'trend_confirm': self._load_keywords_from_env('TREND_CONFIRM_KEYWORDS'),
            'exit': self._load_keywords_from_env('EXIT_KEYWORDS')
        }

    def _load_keywords_from_env(self, env_key):
        """Load keywords from environment variable"""
        try:
            keywords_str = os.environ.get(env_key, '')
            if not keywords_str:
                return self._get_default_keywords(env_key)
            
            keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            return keywords
            
        except Exception as e:
            print(f"   ❌ Error loading {env_key}: {e}")
            return self._get_default_keywords(env_key)

    def _get_default_keywords(self, env_key):
        """Get default keywords (English only)"""
        default_keywords = {
            'BULLISH_KEYWORDS': ['bullish', 'bull', 'buy', 'long', 'call', 'up', 'upside'],
            'BEARISH_KEYWORDS': ['bearish', 'bear', 'sell', 'short', 'put', 'down', 'downside'],
            'TREND_KEYWORDS': ['catcher'],
            'TREND_CONFIRM_KEYWORDS': ['tracer', 'confirmation', 'confirm'],
            'EXIT_KEYWORDS': ['exit', 'close', 'close position', 'take profit', 'stop loss']
        }
        return default_keywords.get(env_key, [])

    def setup_signal_index(self):
        """Create fast signal index"""
        self.signal_index = {}
        for category, signals in self.signals.items():
            for signal in signals:
                normalized = self.normalize_signal(signal)
                self.signal_index[normalized] = category
                self.signal_index[signal] = category

    def normalize_signal(self, signal):
        """Normalize signal for comparison"""
        return signal.lower().strip().replace(' ', '')

    def setup_managers(self):
        """Setup managers and variables"""
        self.pending_signals = {}
        self.active_trades = {}
        self.symbol_trends = {}
        self.signal_history = []
        self.trend_change_history = {}
        self.saved_group2_signals = {}

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
        
        # Keywords first
        if any(keyword in signal_lower for keyword in self.keywords['trend_confirm']):
            return 'trend_confirm'
        if any(keyword in signal_lower for keyword in self.keywords['trend']):
            return 'trend'
        
        # Exact match
        if signal_type in self.signal_index:
            return self.signal_index[signal_type]
        
        # Normalized match
        normalized = self.normalize_signal(signal_type)
        if normalized in self.signal_index:
            return self.signal_index[normalized]
        
        # Keyword-based classification
        for category, keywords in self.keywords.items():
            if any(keyword in signal_lower for keyword in keywords):
                return category
        
        return 'unknown'

    # =============================
    # Signal Handlers
    # =============================

    def handle_trend_signal(self, signal_data):
        """Handle trend signals with smart signal preservation"""
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
        
        # Update trend change history
        self.trend_change_history[symbol] = datetime.now()
        
        # Close trades if setting enabled
        if self.config['RESET_TRADES_ON_TREND_CHANGE']:
            self.close_all_trades_for_symbol(symbol, f"Trend change from {current_trend} to {new_trend}")
        
        # Reset and preserve counter-trend signals
        self.reset_group2_signals(symbol, new_trend)
        
        # Check saved signals against new trend
        self.check_saved_signals_against_new_trend(symbol, new_trend)
        
        # Update trend
        self.symbol_trends[symbol] = new_trend

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('trend', signal_data):
            msg = self.format_trend_message(signal_data, new_trend, current_trend)
            self.send_notifications(msg, 'trend', signal_data)
        else:
            print(f"🔇 Trend notification blocked by settings")
        
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
        
        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('confirmation', signal_data):
            msg = self.format_trend_confirmation_message(signal_data, signal_trend)
            self.send_notifications(msg, 'confirmation', signal_data)
        else:
            print(f"🔇 Confirmation notification blocked by settings")
        
        return True

    def handle_entry_signal(self, signal_data, signal_category):
        """Handle entry signals"""
        symbol = signal_data['ticker']

        # 🛠️ التصحيح المبكر: رفض إشارات المجموعة الثانية المعاكسة للاتجاه إذا كان RESPECT_TREND_FOR_GROUP2=true
        symbol_trend = self.symbol_trends.get(symbol)
        if (self.config['RESPECT_TREND_FOR_GROUP2'] and symbol_trend and 
            signal_category in ['entry_bullish1', 'entry_bearish1']):
            expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
            if symbol_trend != expected_trend:
                print(f"❌ Rejecting Group2 trade: {signal_category} against {symbol_trend} trend for {symbol}")
                return True  # نرفض الإشارة تماماً

        # Check if new trade can be opened
        if not self.can_open_new_trade(symbol):
            return False

        # 🛠️ التصحيح المهم: التحقق من الاتجاه لكلا المجموعتين
        # للمجموعة الأولى
        if (self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and symbol_trend and 
            signal_category in ['entry_bullish', 'entry_bearish']):
            expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
            if symbol_trend != expected_trend:
                print(f"❌ Rejecting trade: {signal_category} signal against {symbol_trend} trend for {symbol}")
                return False

        # Choose strategy based on new settings
        if self.config['OPEN_TRADE_FROM_2_GROUP']:
            return self.handle_dual_confirmation(signal_data, symbol, signal_category)
        else:
            return self.handle_single_confirmation(signal_data, symbol, signal_category)

    def handle_dual_confirmation(self, signal_data, symbol, signal_category):
        """Handle dual confirmation strategy"""
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
            
            # Check trend based on group type and settings
            symbol_trend = self.symbol_trends.get(symbol)
            if symbol_trend and group_type == 'group1' and self.config['RESPECT_TREND_FOR_REGULAR_TRADES']:
                if not self.check_trend_match(signal_category, symbol_trend):
                    print(f"❌ Rejecting group1 signal: {signal_category} against trend {symbol_trend}")
                    group['unique_signals'].remove(clean_type)
                    group['signals_data'].pop()
                    return True
                    
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
        else:
            print(f"🔄 Ignoring duplicate signal: '{signal_data['signal_type']}'")
            return True

        # Open trade if conditions met
        if len(group['unique_signals']) >= self.config['REQUIRED_CONFIRMATIONS']:
            return self.open_confirmed_trade(key, signal_category)
        
        print(f"📊 Waiting for confirmation: {len(group['unique_signals'])}/{self.config['REQUIRED_CONFIRMATIONS']}")
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

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            msg = self.format_entry_message(trade_info, data)
            self.send_notifications(msg, 'entry', {'signal_type': trade_info['signal_type'], 'direction': direction})
        else:
            print(f"🔇 Entry notification blocked by settings")

        del self.pending_signals[key]
        
        self.logger.info(f"Opened {direction} trade #{trade_id}")
        return True

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

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            msg = self.format_dual_entry_message(trade_info, group1_data, group2_data)
            self.send_notifications(msg, 'entry', {'signal_type': trade_info['signal_type'], 'direction': direction})
        else:
            print(f"🔇 Dual entry notification blocked by settings")

        # Clean groups
        del self.pending_signals[group1_key]
        del self.pending_signals[group2_key]

        self.logger.info(f"Opened {direction} trade #{trade_id} with dual strategy")
        return True

    def open_group1_only_trade(self, symbol, base_category, group1_key):
        """Open trade with Group1 signals only"""
        group1_data = self.pending_signals[group1_key]

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
            'confirmed_signals_group1': list(group1_data['unique_signals']),
            'strategy_type': 'GROUP1_ONLY'
        }
        self.active_trades[trade_id] = trade_info

        # إرسال إشعار الدخول
        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            msg = self.format_group1_only_entry_message(trade_info, group1_data)
            self.send_notifications(msg, 'entry', {'signal_type': trade_info['signal_type'], 'direction': direction})
        else:
            print(f"🔇 Group1 only entry notification blocked by settings")

        # تنظيف مجموعة المجموعة الأولى فقط
        del self.pending_signals[group1_key]

        self.logger.info(f"Opened {direction} trade #{trade_id} with Group1 only strategy")
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

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
            msg = self.format_exit_message(trade)
            self.send_notifications(msg, 'exit', {'signal_type': trade.get('exit_signal', '')})
        else:
            print(f"🔇 Exit notification blocked by settings")
        
        print(f"✅ Closing trade #{trade['trade_id']}")
        return True

    def handle_unknown_signal(self, signal_data):
        """Handle unknown signals"""
        self.logger.warning(f"Unknown signal: '{signal_data['signal_type']}' for symbol {signal_data['ticker']}")
        return False

    def handle_general_signal(self, signal_data):
        """Handle general signals"""
        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('general', signal_data):
            msg = self.format_general_message(signal_data)
            self.send_notifications(msg, 'general', signal_data)
        else:
            print(f"🔇 General notification blocked by settings")
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
            
            # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
            if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
                msg = self.format_auto_close_message(trade, reason)
                self.send_notifications(msg, 'exit', {'signal_type': trade.get('exit_signal', '')})
            else:
                print(f"🔇 Auto-close notification blocked by settings")

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

    def reset_group2_signals(self, symbol, new_trend):
        """Reset group2 signals while preserving counter-trend signals"""
        if not symbol:
            return

        print(f"🔄 Resetting group2 signals for {symbol} due to trend change...")
        
        saved_signals = {}
        keys_to_delete = []
        
        for key in list(self.pending_signals.keys()):
            if symbol in key and ('group2' in key or 'bearish1' in key or 'bullish1' in key):
                signal_category = self.pending_signals[key]['signal_category']
                expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
                
                # 🛠️ التصحيح المهم: إذا كانت المجموعة الثانية لا تحترم الاتجاه، لا نحفظ أي إشارات
                if not self.config['RESPECT_TREND_FOR_GROUP2']:
                    # لا نحفظ أي إشارات - نتركها في pending_signals
                    print(f"🎯 Group2 doesn't respect trend - keeping signals: {key}")
                    continue  # لا تحفظ ولا تحذف
                else:
                    # إذا كانت تحترم الاتجاه، نحفظ فقط الإشارات المعاكسة
                    if expected_trend != new_trend:
                        saved_signals[key] = {
                            'unique_signals': self.pending_signals[key]['unique_signals'].copy(),
                            'signals_data': self.pending_signals[key]['signals_data'].copy(),
                            'signal_category': signal_category,
                            'saved_at': datetime.now(),
                            'expected_trend': expected_trend,
                            'original_trend': new_trend
                        }
                        print(f"💾 حفظ إشارات معاكسة: {key} (تتوقع {expected_trend}, الاتجاه الجديد {new_trend})")
                        print(f"   📊 الإشارات المحفوظة: {list(self.pending_signals[key]['unique_signals'])}")
                
                keys_to_delete.append(key)
        
        # 🛠️ التصحيح: تخزين الإشارات المحفوظة بشكل صحيح
        if saved_signals:
            if symbol not in self.saved_group2_signals:
                self.saved_group2_signals[symbol] = {}
            self.saved_group2_signals[symbol].update(saved_signals)
            print(f"💾 تم حفظ {len(saved_signals)} مجموعة إشارات للرمز {symbol}")
            print(f"   📁 الإجمالي المحفوظ لـ {symbol}: {len(self.saved_group2_signals[symbol])}")
    
        # حذف المفاتيح من pending_signals
        for key in keys_to_delete:
            if key in self.pending_signals:
                signal_count = len(self.pending_signals[key]['unique_signals'])
                del self.pending_signals[key]
                print(f"   🗑️ تم حذف مجموعة {key} تحتوي على {signal_count} إشارة")

    def check_saved_signals_against_new_trend(self, symbol, new_trend):
        """Check saved signals that match the new trend"""
        if symbol not in self.saved_group2_signals:
            print(f"📭 لا توجد إشارات محفوظة للرمز {symbol}")
            return False
        
        saved_data = self.saved_group2_signals[symbol]
        activated_count = 0
        
        print(f"🔍 التحقق من الإشارات المحفوظة للرمز {symbol} مقابل الاتجاه الجديد {new_trend}")
        print(f"   📊 المجموعات المحفوظة: {list(saved_data.keys())}")
        
        for key, group_data in list(saved_data.items()):
            expected_trend = group_data['expected_trend']
            
            # 🛠️ التصحيح: إذا كانت المجموعة الثانية لا تحترم الاتجاه، نفعّل جميع الإشارات
            if not self.config['RESPECT_TREND_FOR_GROUP2']:
                # نفعّل جميع الإشارات المحفوظة
                self.activate_saved_group(key, group_data)
                activated_count += 1
                print(f"🎯 تم تفعيل إشارات المجموعة الثانية المحفوظة: {key} ({len(group_data['unique_signals'])} إشارة)")
            else:
                # إذا كانت تحترم الاتجاه، نفعّل فقط المطابقة
                if expected_trend == new_trend:
                    self.activate_saved_group(key, group_data)
                    activated_count += 1
                    print(f"🎯 تم تفعيل الإشارات المحفوظة: {key} ({len(group_data['unique_signals'])} إشارة)")
                    print(f"   📊 الإشارات المفعلة: {list(group_data['unique_signals'])}")
                else:
                    print(f"⏸️  إشارات محفوظة غير مطابقة للاتجاه: {key} (تتوقع {expected_trend}, الاتجاه {new_trend})")
            
            # حذف المجموعة من المحفوظات بعد تفعيلها
            del saved_data[key]
            
            # التحقق فوراً إذا كانت الشروط مكتملة لفتح صفقة
            self.check_immediate_trade_opening(symbol, group_data['signal_category'])
        
        if activated_count > 0:
            print(f"🚀 تم تفعيل {activated_count} مجموعة إشارات محفوظة للرمز {symbol}")
            # إذا تم تفعيل كل المجموعات المحفوظة، احذف الرمز من saved_group2_signals
            if not self.saved_group2_signals[symbol]:
                del self.saved_group2_signals[symbol]
            return True
        
        return False

    def activate_saved_group(self, key, group_data):
        """Activate saved signal group"""
        self.pending_signals[key] = {
            'unique_signals': group_data['unique_signals'].copy(),
            'signals_data': group_data['signals_data'].copy(),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'signal_category': group_data['signal_category'],
            'group_type': 'group2',
            'activated_from_saved': True
        }

    def check_immediate_trade_opening(self, symbol, signal_category):
        """Check immediate trade opening after activating saved signals"""
        base_category = 'entry_bullish' if 'bullish' in signal_category else 'entry_bearish'
        group1_key = f"{symbol}_{base_category}_group1"
        group2_key = f"{symbol}_{base_category}1_group2"
        
        # Check both groups readiness
        group1_ready = self.check_group_ready(group1_key, self.config['REQUIRED_CONFIRMATIONS_GROUP1'])
        group2_ready = self.check_group_ready(group2_key, self.config['REQUIRED_CONFIRMATIONS_GROUP2'])
        
        if group1_ready and group2_ready:
            print(f"🎉 Signals complete after activation - opening immediate trade!")
            return self.open_dual_confirmed_trade(symbol, base_category, group1_key, group2_key)
        
        return False

    def check_dual_conditions(self, symbol, signal_category):
        """Check dual strategy conditions with CORRECT priority"""
        base_category = 'entry_bullish' if 'bullish' in signal_category else 'entry_bearish'
        group1_key = f"{symbol}_{base_category}_group1"
        group2_key = f"{symbol}_{base_category}1_group2"

        symbol_trend = self.symbol_trends.get(symbol)
        
        # Smart timing: Check trend stability
        if symbol_trend and self.config['ENABLE_SMART_TIMING']:
            if self.is_trend_recently_changed(symbol):
                delay_minutes = self.config['TREND_CONFIRMATION_DELAY']
                time_since_change = (datetime.now() - self.trend_change_history[symbol]).total_seconds()
                remaining_time = (delay_minutes * 60) - time_since_change
                
                print(f"⏳ Trend recently changed for {symbol} - waiting {remaining_time:.0f} seconds for stability...")
                return True

        # Check both groups readiness
        group1_ready = self.check_group_ready(group1_key, self.config['REQUIRED_CONFIRMATIONS_GROUP1'])
        group2_ready = self.check_group_ready(group2_key, self.config['REQUIRED_CONFIRMATIONS_GROUP2'])

        print(f"📊 Groups status - {symbol}: Group1={group1_ready}({len(self.pending_signals[group1_key]['unique_signals']) if group1_key in self.pending_signals else 0}), Group2={group2_ready}({len(self.pending_signals[group2_key]['unique_signals']) if group2_key in self.pending_signals else 0})")

        # 🎯 الأولوية الأولى: فتح صفقات من المجموعتين معاً
        if self.config['OPEN_TRADE_FROM_2_GROUP'] and group1_ready and group2_ready:
            # Final smart timing check
            if self.config['ENABLE_SMART_TIMING'] and self.is_trend_recently_changed(symbol):
                delay_minutes = self.config['TREND_CONFIRMATION_DELAY']
                print(f"⏸️  Dual signals collected but waiting {delay_minutes} minutes for trend stability")
                return True
                
            print(f"🎯 DUAL STRATEGY: Opening trade with both groups for {symbol}")
            return self.open_dual_confirmed_trade(symbol, base_category, group1_key, group2_key)

        # 🎯 الأولوية الثانية: فتح صفقات من المجموعة الأولى فقط
        elif self.config['OPEN_TRADE_FROM_1_GROUP'] and group1_ready:
            # Final smart timing check for Group1 only
            if self.config['ENABLE_SMART_TIMING'] and self.is_trend_recently_changed(symbol):
                delay_minutes = self.config['TREND_CONFIRMATION_DELAY']
                print(f"⏸️  Group1 signals collected but waiting {delay_minutes} minutes for trend stability")
                return True
                
            print(f"🎯 GROUP1 ONLY: Opening trade with Group1 only for {symbol}")
            return self.open_group1_only_trade(symbol, base_category, group1_key)
        
        # إذا لم تتحقق أي من الشروط
        print(f"⏳ Waiting for signals - {symbol}: Need Group1={self.config['REQUIRED_CONFIRMATIONS_GROUP1']}, Group2={self.config['REQUIRED_CONFIRMATIONS_GROUP2']}")
        return True

    def is_trend_recently_changed(self, symbol):
        """Check if trend was recently changed"""
        if not self.config['ENABLE_SMART_TIMING']:
            return False
        
        last_trend_change = self.trend_change_history.get(symbol)
        if not last_trend_change:
            return False
        
        time_since_change = (datetime.now() - last_trend_change).total_seconds()
        delay_period = self.config['TREND_CONFIRMATION_DELAY'] * 60
        
        return time_since_change < delay_period

    def check_group_ready(self, group_key, required_count):
        """Check group readiness"""
        if group_key not in self.pending_signals:
            return False
        return len(self.pending_signals[group_key]['unique_signals']) >= required_count

    def clean_expired_signals(self):
        """Clean expired signals"""
        now = datetime.now()
        timeout = self.config['DUAL_CONFIRMATION_TIMEOUT'] if self.config['OPEN_TRADE_FROM_2_GROUP'] else self.config['CONFIRMATION_TIMEOUT']
        
        expired_keys = [
            key for key, data in self.pending_signals.items()
            if (now - data.get('updated_at', data['created_at'])).total_seconds() > timeout
        ]
        
        for key in expired_keys:
            signal_count = len(self.pending_signals[key]['unique_signals'])
            del self.pending_signals[key]
            print(f"🗑️ Cleaning expired group: {key} - {signal_count} signals")

        # Clean expired saved signals
        self.clean_expired_saved_signals()

    def clean_expired_saved_signals(self):
        """Clean expired saved signals"""
        if not self.config['ENABLE_COUNTER_TREND_PRESERVATION']:
            return
            
        now = datetime.now()
        expired_symbols = []
        
        for symbol, saved_data in self.saved_group2_signals.items():
            for key, group_data in saved_data.items():
                save_time = group_data['saved_at']
                if (now - save_time).total_seconds() > self.config['MAX_COUNTER_TREND_SAVE_TIME']:
                    expired_symbols.append(symbol)
                    break
        
        for symbol in expired_symbols:
            signal_count = len(self.saved_group2_signals[symbol])
            del self.saved_group2_signals[symbol]
            print(f"🧹 Cleaned {signal_count} expired saved signals for {symbol}")

    # =============================
    # Notifications and Sending
    # =============================

    def should_send_message(self, message_type, signal_data=None):
        """Check if message should be sent - FIXED VERSION"""
        type_controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }
        
        # 🛠️ التصحيح: التحقق من القيمة الفعلية للإعداد
        if message_type not in type_controls:
            return False
        
        if not type_controls[message_type]:
            return False

        if signal_data:
            signal_text = str(signal_data.get('signal_type', '')).lower()
            direction = signal_data.get('direction', '').upper()
            
            if ('bullish' in signal_text or direction == 'CALL') and not self.config['SEND_BULLISH_SIGNALS']:
                return False
            if ('bearish' in signal_text or direction == 'PUT') and not self.config['SEND_BEARISH_SIGNALS']:
                return False

        return True

    def send_notifications(self, message, message_type, signal_data=None):
        """Send notifications - FIXED VERSION"""
        # 🛠️ التصحيح: التحقق المزدوج للتأكد من تطبيق الإعدادات
        if not self.should_send_message(message_type, signal_data):
            print(f"🔇 Notification blocked by settings: {message_type}")
            return

        # Send Telegram
        if self.config['TELEGRAM_ENABLED']:
            success = self.send_telegram(message)
            if success:
                print(f"📤 Telegram notification sent: {message_type}")
            else:
                print(f"❌ Failed to send Telegram notification: {message_type}")

        # Send to external server
        if self.config['EXTERNAL_SERVER_ENABLED']:
            success = self.send_to_external_server_with_retry(message, message_type)
            if success:
                print(f"🌐 External server notification sent: {message_type}")
            else:
                print(f"❌ Failed to send external server notification: {message_type}")

    def send_telegram(self, message):
        """Send to Telegram"""
        token = self.config['TELEGRAM_BOT_TOKEN']
        chat_id = self.config['TELEGRAM_CHAT_ID']
        
        if not token or not chat_id:
            print("❌ Telegram not configured: missing token or chat_id")
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
                time.sleep(2 ** attempt)
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

    def format_group1_only_entry_message(self, trade_info, group1_data):
        """Format Group1 only entry message - Arabic"""
        symbol = trade_info['ticker']
        direction = trade_info['direction']
        signal = trade_info['signal_type']
        confirmations1 = trade_info.get('confirmation_count_group1', 0)
        helpers1 = trade_info.get('confirmed_signals_group1', [])
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
        if len(helpers1) > 1:
            numbered_helpers1 = [f"┃   {i+1}. {helper}" for i, helper in enumerate(helpers1[1:])]
            helpers_list1 = "\n" + "\n".join(numbered_helpers1)

        return (
            "✦✦✦ 🚀 دخـــــول صفـــــقة (المجموعة الأولى فقط) ✦✦✦\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 💰 الرمز: {symbol}\n"
            f"┃ 🎯 نوع الصفقة: {'🟢 شراء' if direction=='CALL' else '🔴 بيع'}\n"
            f"┃ 📊 اتجاه الرمز: {trend_icon}\n"
            f"┃ 🎯 محاذاة الاتجاه: {align_text}\n"
            f"┃ 🎯 الاستراتيجية: المجموعة الأولى فقط\n"
            f"┃ 📋 الإشارة الرئيسية: {signal} (تم التأكيد بـ {confirmations1} إشارات)\n"
            f"┃ 🔔 الإشارات المساعدة: {len(helpers1)-1} إشارة{helpers_list1}\n"
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
            "open_trade_from_2_group": self.config['OPEN_TRADE_FROM_2_GROUP'],
            "open_trade_from_1_group": self.config['OPEN_TRADE_FROM_1_GROUP'],
            "saved_signals_count": len(self.saved_group2_signals),
            "notification_settings": {
                "SEND_TREND_MESSAGES": self.config['SEND_TREND_MESSAGES'],
                "SEND_ENTRY_MESSAGES": self.config['SEND_ENTRY_MESSAGES'],
                "SEND_EXIT_MESSAGES": self.config['SEND_EXIT_MESSAGES'],
                "SEND_CONFIRMATION_MESSAGES": self.config['SEND_CONFIRMATION_MESSAGES'],
                "SEND_GENERAL_MESSAGES": self.config['SEND_GENERAL_MESSAGES'],
                "SEND_BULLISH_SIGNALS": self.config['SEND_BULLISH_SIGNALS'],
                "SEND_BEARISH_SIGNALS": self.config['SEND_BEARISH_SIGNALS']
            }
        }

    def display_loaded_signals(self):
        """Display loaded signals"""
        print("\n📊 Loaded Signals:")
        for category, signals in self.signals.items():
            print(f"   📁 {category}: {len(signals)} signals")
        
        # 🆕 عرض إعدادات الاستراتيجية المحدثة
        print(f"\n🎯 Trading Strategy Settings:")
        print(f"   • Open Trade From 2 Groups: {'✅ Enabled' if self.config['OPEN_TRADE_FROM_2_GROUP'] else '❌ Disabled'}")
        print(f"   • Open Trade From 1 Group: {'✅ Enabled' if self.config['OPEN_TRADE_FROM_1_GROUP'] else '❌ Disabled'}")
        print(f"   • Required Group1: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']} signals")
        print(f"   • Required Group2: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']} signals")

    def check_settings(self):
        """Check settings"""
        print(f"\n🔍 System Settings:")
        print(f"📊 Trade Management:")
        print(f"   • Max Open Trades: {self.config['MAX_OPEN_TRADES']}")
        print(f"   • Max Trades Per Symbol: {self.config['MAX_TRADES_PER_SYMBOL']}")
        
        # 🆕 تحديث عرض إعدادات التداول
        print("🎯 Trading Strategy:")
        print(f"   • Open Trade From 2 Groups: {'✅ Enabled' if self.config['OPEN_TRADE_FROM_2_GROUP'] else '❌ Disabled'}")
        print(f"   • Open Trade From 1 Group: {'✅ Enabled' if self.config['OPEN_TRADE_FROM_1_GROUP'] else '❌ Disabled'}")
        print(f"   • Required Group1: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']} signals")
        print(f"   • Required Group2: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']} signals")
        
        # 🛠️ عرض إعدادات RESPECT_TREND_FOR_GROUP2
        print(f"   • Respect Trend For Group2: {'✅ Enabled' if self.config['RESPECT_TREND_FOR_GROUP2'] else '❌ Disabled'}")
        
        print("🔔 Notifications:")
        print(f"   • Trend Messages: {'Enabled' if self.config['SEND_TREND_MESSAGES'] else 'Disabled'}")
        print(f"   • Entry Messages: {'Enabled' if self.config['SEND_ENTRY_MESSAGES'] else 'Disabled'}")
        print(f"   • Exit Messages: {'Enabled' if self.config['SEND_EXIT_MESSAGES'] else 'Disabled'}")
        print(f"   • Confirmation Messages: {'Enabled' if self.config['SEND_CONFIRMATION_MESSAGES'] else 'Disabled'}")
        print(f"   • General Messages: {'Enabled' if self.config['SEND_GENERAL_MESSAGES'] else 'Disabled'}")
        print(f"   • Bullish Signals: {'Enabled' if self.config['SEND_BULLISH_SIGNALS'] else 'Disabled'}")
        print(f"   • Bearish Signals: {'Enabled' if self.config['SEND_BEARISH_SIGNALS'] else 'Disabled'}")

    def debug_pending_signals(self):
        """عرض حالة الإشارات المنتظرة للتصحيح"""
        print("\n🔍 DEBUG - Pending Signals Status:")
        if not self.pending_signals:
            print("   • No pending signals")
        else:
            for key, data in self.pending_signals.items():
                print(f"   • {key}: {len(data['unique_signals'])} signals")
                print(f"     {list(data['unique_signals'])}")
        
        print("🔍 DEBUG - Saved Signals Status:")
        if not self.saved_group2_signals:
            print("   • No saved signals")
        else:
            for symbol, saved_data in self.saved_group2_signals.items():
                print(f"   • {symbol}: {len(saved_data)} saved groups")
                for key, group_data in saved_data.items():
                    print(f"     - {key}: {len(group_data['unique_signals'])} signals")

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

            # 🆕 Smart Settings
            'RESPECT_TREND_FOR_REGULAR_TRADES': self.get_config_value('RESPECT_TREND_FOR_REGULAR_TRADES', True, bool),
            'RESPECT_TREND_FOR_GROUP2': self.get_config_value('RESPECT_TREND_FOR_GROUP2', True, bool),
            'RESET_TRADES_ON_TREND_CHANGE': self.get_config_value('RESET_TRADES_ON_TREND_CHANGE', True, bool),
            'ENABLE_SMART_TIMING': self.get_config_value('ENABLE_SMART_TIMING', True, bool),
            'TREND_CONFIRMATION_DELAY': self.get_config_value('TREND_CONFIRMATION_DELAY', 2, int),
            'ENABLE_COUNTER_TREND_PRESERVATION': self.get_config_value('ENABLE_COUNTER_TREND_PRESERVATION', True, bool),
            'MAX_COUNTER_TREND_SAVE_TIME': self.get_config_value('MAX_COUNTER_TREND_SAVE_TIME', 600, int),
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
                return default
                
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
                return []
            
            signals = [s.strip() for s in signal_str.split(',') if s.strip()]
            return signals
            
        except Exception as e:
            print(f"   ❌ Error loading {key}: {e}")
            return []

    def setup_keywords(self):
        """Load keywords from environment"""
        self.keywords = {
            'bullish': self._load_keywords_from_env('BULLISH_KEYWORDS'),
            'bearish': self._load_keywords_from_env('BEARISH_KEYWORDS'),
            'trend': self._load_keywords_from_env('TREND_KEYWORDS'),
            'trend_confirm': self._load_keywords_from_env('TREND_CONFIRM_KEYWORDS'),
            'exit': self._load_keywords_from_env('EXIT_KEYWORDS')
        }

    def _load_keywords_from_env(self, env_key):
        """Load keywords from environment variable"""
        try:
            keywords_str = os.environ.get(env_key, '')
            if not keywords_str:
                return self._get_default_keywords(env_key)
            
            keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            return keywords
            
        except Exception as e:
            print(f"   ❌ Error loading {env_key}: {e}")
            return self._get_default_keywords(env_key)

    def _get_default_keywords(self, env_key):
        """Get default keywords (English only)"""
        default_keywords = {
            'BULLISH_KEYWORDS': ['bullish', 'bull', 'buy', 'long', 'call', 'up', 'upside'],
            'BEARISH_KEYWORDS': ['bearish', 'bear', 'sell', 'short', 'put', 'down', 'downside'],
            'TREND_KEYWORDS': ['catcher'],
            'TREND_CONFIRM_KEYWORDS': ['tracer', 'confirmation', 'confirm'],
            'EXIT_KEYWORDS': ['exit', 'close', 'close position', 'take profit', 'stop loss']
        }
        return default_keywords.get(env_key, [])

    def setup_signal_index(self):
        """Create fast signal index"""
        self.signal_index = {}
        for category, signals in self.signals.items():
            for signal in signals:
                normalized = self.normalize_signal(signal)
                self.signal_index[normalized] = category
                self.signal_index[signal] = category

    def normalize_signal(self, signal):
        """Normalize signal for comparison"""
        return signal.lower().strip().replace(' ', '')

    def setup_managers(self):
        """Setup managers and variables"""
        self.pending_signals = {}
        self.active_trades = {}
        self.symbol_trends = {}
        self.signal_history = []
        self.trend_change_history = {}
        self.saved_group2_signals = {}

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
        
        # Keywords first
        if any(keyword in signal_lower for keyword in self.keywords['trend_confirm']):
            return 'trend_confirm'
        if any(keyword in signal_lower for keyword in self.keywords['trend']):
            return 'trend'
        
        # Exact match
        if signal_type in self.signal_index:
            return self.signal_index[signal_type]
        
        # Normalized match
        normalized = self.normalize_signal(signal_type)
        if normalized in self.signal_index:
            return self.signal_index[normalized]
        
        # Keyword-based classification
        for category, keywords in self.keywords.items():
            if any(keyword in signal_lower for keyword in keywords):
                return category
        
        return 'unknown'

    # =============================
    # Signal Handlers
    # =============================

    def handle_trend_signal(self, signal_data):
        """Handle trend signals with smart signal preservation"""
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
        
        # Update trend change history
        self.trend_change_history[symbol] = datetime.now()
        
        # Close trades if setting enabled
        if self.config['RESET_TRADES_ON_TREND_CHANGE']:
            self.close_all_trades_for_symbol(symbol, f"Trend change from {current_trend} to {new_trend}")
        
        # Reset and preserve counter-trend signals
        self.reset_group2_signals(symbol, new_trend)
        
        # Check saved signals against new trend
        self.check_saved_signals_against_new_trend(symbol, new_trend)
        
        # Update trend
        self.symbol_trends[symbol] = new_trend

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('trend', signal_data):
            msg = self.format_trend_message(signal_data, new_trend, current_trend)
            self.send_notifications(msg, 'trend', signal_data)
        else:
            print(f"🔇 Trend notification blocked by settings")
        
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
        
        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('confirmation', signal_data):
            msg = self.format_trend_confirmation_message(signal_data, signal_trend)
            self.send_notifications(msg, 'confirmation', signal_data)
        else:
            print(f"🔇 Confirmation notification blocked by settings")
        
        return True

    def handle_entry_signal(self, signal_data, signal_category):
        """Handle entry signals"""
        symbol = signal_data['ticker']

        # Check if new trade can be opened
        if not self.can_open_new_trade(symbol):
            return False

        # 🛠️ التصحيح المهم: التحقق من الاتجاه لكلا المجموعتين
        symbol_trend = self.symbol_trends.get(symbol)
        
        # للمجموعة الأولى
        if (self.config['RESPECT_TREND_FOR_REGULAR_TRADES'] and symbol_trend and 
            signal_category in ['entry_bullish', 'entry_bearish']):
            expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
            if symbol_trend != expected_trend:
                print(f"❌ Rejecting trade: {signal_category} signal against {symbol_trend} trend for {symbol}")
                return False

        # 🛠️ التصحيح الحاسم: للمجموعة الثانية - يجب أن تحترم الاتجاه عندما يكون RESPECT_TREND_FOR_GROUP2=true
        if (self.config['RESPECT_TREND_FOR_GROUP2'] and symbol_trend and 
            signal_category in ['entry_bullish1', 'entry_bearish1']):
            expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
            if symbol_trend != expected_trend:
                print(f"❌ Rejecting Group2 trade: {signal_category} signal against {symbol_trend} trend for {symbol}")
                return False

        # Choose strategy
        if self.config['DUAL_CONFIRMATION_STRATEGY']:
            return self.handle_dual_confirmation(signal_data, symbol, signal_category)
        else:
            return self.handle_single_confirmation(signal_data, symbol, signal_category)

    def handle_dual_confirmation(self, signal_data, symbol, signal_category):
        """Handle dual confirmation strategy"""
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
            # 🛠️ التصحيح: التحقق من الاتجاه للمجموعة الثانية بناءً على الإعداد
            symbol_trend = self.symbol_trends.get(symbol)
            if symbol_trend and group_type == 'group2' and self.config['RESPECT_TREND_FOR_GROUP2']:
                expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
                if symbol_trend != expected_trend:
                    print(f"❌ Rejecting group2 signal: {signal_category} against trend {symbol_trend}")
                    return True  # نرفض الإشارة ولا نضيفها
            
            group['unique_signals'].add(clean_type)
            group['signals_data'].append(signal_data)
            group['updated_at'] = datetime.now()
            
            print(f"✅ Adding unique signal to group {group_type}: '{signal_data['signal_type']}'")
            
            # Check trend based on group type and settings
            symbol_trend = self.symbol_trends.get(symbol)
            if symbol_trend and group_type == 'group1' and self.config['RESPECT_TREND_FOR_REGULAR_TRADES']:
                if not self.check_trend_match(signal_category, symbol_trend):
                    print(f"❌ Rejecting group1 signal: {signal_category} against trend {symbol_trend}")
                    group['unique_signals'].remove(clean_type)
                    group['signals_data'].pop()
                    return True
                    
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
        else:
            print(f"🔄 Ignoring duplicate signal: '{signal_data['signal_type']}'")
            return True

        # Open trade if conditions met
        if len(group['unique_signals']) >= self.config['REQUIRED_CONFIRMATIONS']:
            return self.open_confirmed_trade(key, signal_category)
        
        print(f"📊 Waiting for confirmation: {len(group['unique_signals'])}/{self.config['REQUIRED_CONFIRMATIONS']}")
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

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            msg = self.format_entry_message(trade_info, data)
            self.send_notifications(msg, 'entry', {'signal_type': trade_info['signal_type'], 'direction': direction})
        else:
            print(f"🔇 Entry notification blocked by settings")

        del self.pending_signals[key]
        
        self.logger.info(f"Opened {direction} trade #{trade_id}")
        return True

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

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('entry', {'signal_type': trade_info['signal_type'], 'direction': direction}):
            msg = self.format_dual_entry_message(trade_info, group1_data, group2_data)
            self.send_notifications(msg, 'entry', {'signal_type': trade_info['signal_type'], 'direction': direction})
        else:
            print(f"🔇 Dual entry notification blocked by settings")

        # Clean groups
        del self.pending_signals[group1_key]
        del self.pending_signals[group2_key]

        self.logger.info(f"Opened {direction} trade #{trade_id} with dual strategy")
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

        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
            msg = self.format_exit_message(trade)
            self.send_notifications(msg, 'exit', {'signal_type': trade.get('exit_signal', '')})
        else:
            print(f"🔇 Exit notification blocked by settings")
        
        print(f"✅ Closing trade #{trade['trade_id']}")
        return True

    def handle_unknown_signal(self, signal_data):
        """Handle unknown signals"""
        self.logger.warning(f"Unknown signal: '{signal_data['signal_type']}' for symbol {signal_data['ticker']}")
        return False

    def handle_general_signal(self, signal_data):
        """Handle general signals"""
        # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
        if self.should_send_message('general', signal_data):
            msg = self.format_general_message(signal_data)
            self.send_notifications(msg, 'general', signal_data)
        else:
            print(f"🔇 General notification blocked by settings")
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
            
            # 🛠️ التصحيح: التحقق من الإعداد قبل إرسال الإشعار
            if self.should_send_message('exit', {'signal_type': trade.get('exit_signal', '')}):
                msg = self.format_auto_close_message(trade, reason)
                self.send_notifications(msg, 'exit', {'signal_type': trade.get('exit_signal', '')})
            else:
                print(f"🔇 Auto-close notification blocked by settings")

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

    def reset_group2_signals(self, symbol, new_trend):
        """Reset group2 signals while preserving counter-trend signals"""
        if not symbol:
            return

        print(f"🔄 Resetting group2 signals for {symbol} due to trend change...")
        
        saved_signals = {}
        keys_to_delete = []
        
        for key in list(self.pending_signals.keys()):
            if symbol in key and ('group2' in key or 'bearish1' in key or 'bullish1' in key):
                signal_category = self.pending_signals[key]['signal_category']
                expected_trend = 'BULLISH' if 'bullish' in signal_category else 'BEARISH'
                
                # 🛠️ التصحيح المهم: التحقق من إعداد RESPECT_TREND_FOR_GROUP2
                if not self.config['RESPECT_TREND_FOR_GROUP2']:
                    # إذا كانت المجموعة الثانية لا تحترم الاتجاه، نحفظ جميع إشاراتها
                    saved_signals[key] = {
                        'unique_signals': self.pending_signals[key]['unique_signals'].copy(),
                        'signals_data': self.pending_signals[key]['signals_data'].copy(),
                        'signal_category': signal_category,
                        'saved_at': datetime.now(),
                        'expected_trend': expected_trend,
                        'original_trend': new_trend
                    }
                    print(f"💾 حفظ جميع إشارات المجموعة الثانية: {key} (الاتجاه المتوقع: {expected_trend}, الاتجاه الجديد: {new_trend})")
                    print(f"   📊 الإشارات المحفوظة: {list(self.pending_signals[key]['unique_signals'])}")
                else:
                    # 🛠️ التصحيح: إذا كانت تحترم الاتجاه، نحفظ فقط الإشارات المعاكسة
                    if expected_trend != new_trend:
                        saved_signals[key] = {
                            'unique_signals': self.pending_signals[key]['unique_signals'].copy(),
                            'signals_data': self.pending_signals[key]['signals_data'].copy(),
                            'signal_category': signal_category,
                            'saved_at': datetime.now(),
                            'expected_trend': expected_trend,
                            'original_trend': new_trend
                        }
                        print(f"💾 حفظ إشارات معاكسة: {key} (تتوقع {expected_trend}, الاتجاه الجديد {new_trend})")
                        print(f"   📊 الإشارات المحفوظة: {list(self.pending_signals[key]['unique_signals'])}")
                
                keys_to_delete.append(key)
        
        # 🛠️ التصحيح: تخزين الإشارات المحفوظة بشكل صحيح
        if saved_signals:
            if symbol not in self.saved_group2_signals:
                self.saved_group2_signals[symbol] = {}
            self.saved_group2_signals[symbol].update(saved_signals)
            print(f"💾 تم حفظ {len(saved_signals)} مجموعة إشارات للرمز {symbol}")
            print(f"   📁 الإجمالي المحفوظ لـ {symbol}: {len(self.saved_group2_signals[symbol])}")
    
        # حذف المفاتيح من pending_signals
        for key in keys_to_delete:
            if key in self.pending_signals:
                signal_count = len(self.pending_signals[key]['unique_signals'])
                del self.pending_signals[key]
                print(f"   🗑️ تم حذف مجموعة {key} تحتوي على {signal_count} إشارة")

    def check_saved_signals_against_new_trend(self, symbol, new_trend):
        """Check saved signals that match the new trend"""
        if symbol not in self.saved_group2_signals:
            print(f"📭 لا توجد إشارات محفوظة للرمز {symbol}")
            return False
        
        saved_data = self.saved_group2_signals[symbol]
        activated_count = 0
        
        print(f"🔍 التحقق من الإشارات المحفوظة للرمز {symbol} مقابل الاتجاه الجديد {new_trend}")
        print(f"   📊 المجموعات المحفوظة: {list(saved_data.keys())}")
        
        for key, group_data in list(saved_data.items()):
            expected_trend = group_data['expected_trend']
            
            # 🛠️ التصحيح: إذا كانت المجموعة الثانية لا تحترم الاتجاه، نفعّل جميع الإشارات
            if not self.config['RESPECT_TREND_FOR_GROUP2']:
                # نفعّل جميع إشارات المجموعة الثانية بغض النظر عن الاتجاه
                self.pending_signals[key] = {
                    'unique_signals': group_data['unique_signals'].copy(),
                    'signals_data': group_data['signals_data'].copy(),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'signal_category': group_data['signal_category'],
                    'group_type': 'group2',
                    'activated_from_saved': True
                }
                activated_count += 1
                print(f"🎯 تم تفعيل إشارات المجموعة الثانية: {key} ({len(group_data['unique_signals'])} إشارة)")
                print(f"   📊 الإشارات المفعلة: {list(group_data['unique_signals'])}")
            else:
                # إذا كانت تحترم الاتجاه، نفعّل فقط المطابقة
                if expected_trend == new_trend:
                    self.pending_signals[key] = {
                        'unique_signals': group_data['unique_signals'].copy(),
                        'signals_data': group_data['signals_data'].copy(),
                        'created_at': datetime.now(),
                        'updated_at': datetime.now(),
                        'signal_category': group_data['signal_category'],
                        'group_type': 'group2',
                        'activated_from_saved': True
                    }
                    activated_count += 1
                    print(f"🎯 تم تفعيل الإشارات المحفوظة: {key} ({len(group_data['unique_signals'])} إشارة)")
                    print(f"   📊 الإشارات المفعلة: {list(group_data['unique_signals'])}")
            
            # حذف المجموعة من المحفوظات بعد تفعيلها
            del saved_data[key]
            
            # التحقق فوراً إذا كانت الشروط مكتملة لفتح صفقة
            self.check_immediate_trade_opening(symbol, group_data['signal_category'])
        
        if activated_count > 0:
            print(f"🚀 تم تفعيل {activated_count} مجموعة إشارات محفوظة للرمز {symbol}")
            # إذا تم تفعيل كل المجموعات المحفوظة، احذف الرمز من saved_group2_signals
            if not self.saved_group2_signals[symbol]:
                del self.saved_group2_signals[symbol]
            return True
        
        return False

    def check_immediate_trade_opening(self, symbol, signal_category):
        """Check immediate trade opening after activating saved signals"""
        base_category = 'entry_bullish' if 'bullish' in signal_category else 'entry_bearish'
        group1_key = f"{symbol}_{base_category}_group1"
        group2_key = f"{symbol}_{base_category}1_group2"
        
        # Check both groups readiness
        group1_ready = self.check_group_ready(group1_key, self.config['REQUIRED_CONFIRMATIONS_GROUP1'])
        group2_ready = self.check_group_ready(group2_key, self.config['REQUIRED_CONFIRMATIONS_GROUP2'])
        
        if group1_ready and group2_ready:
            print(f"🎉 Signals complete after activation - opening immediate trade!")
            return self.open_dual_confirmed_trade(symbol, base_category, group1_key, group2_key)
        
        return False

    def check_dual_conditions(self, symbol, signal_category):
        """Check dual strategy conditions"""
        base_category = 'entry_bullish' if 'bullish' in signal_category else 'entry_bearish'
        group1_key = f"{symbol}_{base_category}_group1"
        group2_key = f"{symbol}_{base_category}1_group2"

        symbol_trend = self.symbol_trends.get(symbol)
        
        # Smart timing: Check trend stability
        if symbol_trend and self.config['ENABLE_SMART_TIMING']:
            if self.is_trend_recently_changed(symbol):
                delay_minutes = self.config['TREND_CONFIRMATION_DELAY']
                time_since_change = (datetime.now() - self.trend_change_history[symbol]).total_seconds()
                remaining_time = (delay_minutes * 60) - time_since_change
                
                print(f"⏳ Trend recently changed for {symbol} - waiting {remaining_time:.0f} seconds for stability...")
                return True

        # Check both groups readiness
        group1_ready = self.check_group_ready(group1_key, self.config['REQUIRED_CONFIRMATIONS_GROUP1'])
        group2_ready = self.check_group_ready(group2_key, self.config['REQUIRED_CONFIRMATIONS_GROUP2'])

        if group1_ready and group2_ready:
            # Final smart timing check
            if self.config['ENABLE_SMART_TIMING'] and self.is_trend_recently_changed(symbol):
                delay_minutes = self.config['TREND_CONFIRMATION_DELAY']
                print(f"⏸️  Signals collected but waiting {delay_minutes} minutes for trend stability")
                return True
                
            return self.open_dual_confirmed_trade(symbol, base_category, group1_key, group2_key)
        
        return True

    def is_trend_recently_changed(self, symbol):
        """Check if trend was recently changed"""
        if not self.config['ENABLE_SMART_TIMING']:
            return False
        
        last_trend_change = self.trend_change_history.get(symbol)
        if not last_trend_change:
            return False
        
        time_since_change = (datetime.now() - last_trend_change).total_seconds()
        delay_period = self.config['TREND_CONFIRMATION_DELAY'] * 60
        
        return time_since_change < delay_period

    def check_group_ready(self, group_key, required_count):
        """Check group readiness"""
        if group_key not in self.pending_signals:
            return False
        return len(self.pending_signals[group_key]['unique_signals']) >= required_count

    def clean_expired_signals(self):
        """Clean expired signals"""
        now = datetime.now()
        timeout = self.config['DUAL_CONFIRMATION_TIMEOUT'] if self.config['DUAL_CONFIRMATION_STRATEGY'] else self.config['CONFIRMATION_TIMEOUT']
        
        expired_keys = [
            key for key, data in self.pending_signals.items()
            if (now - data.get('updated_at', data['created_at'])).total_seconds() > timeout
        ]
        
        for key in expired_keys:
            signal_count = len(self.pending_signals[key]['unique_signals'])
            del self.pending_signals[key]
            print(f"🗑️ Cleaning expired group: {key} - {signal_count} signals")

        # Clean expired saved signals
        self.clean_expired_saved_signals()

    def clean_expired_saved_signals(self):
        """Clean expired saved signals"""
        if not self.config['ENABLE_COUNTER_TREND_PRESERVATION']:
            return
            
        now = datetime.now()
        expired_symbols = []
        
        for symbol, saved_data in self.saved_group2_signals.items():
            for key, group_data in saved_data.items():
                save_time = group_data['saved_at']
                if (now - save_time).total_seconds() > self.config['MAX_COUNTER_TREND_SAVE_TIME']:
                    expired_symbols.append(symbol)
                    break
        
        for symbol in expired_symbols:
            signal_count = len(self.saved_group2_signals[symbol])
            del self.saved_group2_signals[symbol]
            print(f"🧹 Cleaned {signal_count} expired saved signals for {symbol}")

    # =============================
    # Notifications and Sending
    # =============================

    def should_send_message(self, message_type, signal_data=None):
        """Check if message should be sent - FIXED VERSION"""
        type_controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }
        
        # 🛠️ التصحيح: التحقق من القيمة الفعلية للإعداد
        if message_type not in type_controls:
            return False
        
        if not type_controls[message_type]:
            return False

        if signal_data:
            signal_text = str(signal_data.get('signal_type', '')).lower()
            direction = signal_data.get('direction', '').upper()
            
            if ('bullish' in signal_text or direction == 'CALL') and not self.config['SEND_BULLISH_SIGNALS']:
                return False
            if ('bearish' in signal_text or direction == 'PUT') and not self.config['SEND_BEARISH_SIGNALS']:
                return False

        return True

    def send_notifications(self, message, message_type, signal_data=None):
        """Send notifications - FIXED VERSION"""
        # 🛠️ التصحيح: التحقق المزدوج للتأكد من تطبيق الإعدادات
        if not self.should_send_message(message_type, signal_data):
            print(f"🔇 Notification blocked by settings: {message_type}")
            return

        # Send Telegram
        if self.config['TELEGRAM_ENABLED']:
            success = self.send_telegram(message)
            if success:
                print(f"📤 Telegram notification sent: {message_type}")
            else:
                print(f"❌ Failed to send Telegram notification: {message_type}")

        # Send to external server
        if self.config['EXTERNAL_SERVER_ENABLED']:
            success = self.send_to_external_server_with_retry(message, message_type)
            if success:
                print(f"🌐 External server notification sent: {message_type}")
            else:
                print(f"❌ Failed to send external server notification: {message_type}")

    def send_telegram(self, message):
        """Send to Telegram"""
        token = self.config['TELEGRAM_BOT_TOKEN']
        chat_id = self.config['TELEGRAM_CHAT_ID']
        
        if not token or not chat_id:
            print("❌ Telegram not configured: missing token or chat_id")
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
                time.sleep(2 ** attempt)
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
            "dual_confirmation_strategy": self.config['DUAL_CONFIRMATION_STRATEGY'],
            "saved_signals_count": len(self.saved_group2_signals),
            "notification_settings": {
                "SEND_TREND_MESSAGES": self.config['SEND_TREND_MESSAGES'],
                "SEND_ENTRY_MESSAGES": self.config['SEND_ENTRY_MESSAGES'],
                "SEND_EXIT_MESSAGES": self.config['SEND_EXIT_MESSAGES'],
                "SEND_CONFIRMATION_MESSAGES": self.config['SEND_CONFIRMATION_MESSAGES'],
                "SEND_GENERAL_MESSAGES": self.config['SEND_GENERAL_MESSAGES'],
                "SEND_BULLISH_SIGNALS": self.config['SEND_BULLISH_SIGNALS'],
                "SEND_BEARISH_SIGNALS": self.config['SEND_BEARISH_SIGNALS']
            }
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
        
        print("🔔 Notifications:")
        print(f"   • Trend Messages: {'Enabled' if self.config['SEND_TREND_MESSAGES'] else 'Disabled'}")
        print(f"   • Entry Messages: {'Enabled' if self.config['SEND_ENTRY_MESSAGES'] else 'Disabled'}")
        print(f"   • Exit Messages: {'Enabled' if self.config['SEND_EXIT_MESSAGES'] else 'Disabled'}")
        print(f"   • Confirmation Messages: {'Enabled' if self.config['SEND_CONFIRMATION_MESSAGES'] else 'Disabled'}")
        print(f"   • General Messages: {'Enabled' if self.config['SEND_GENERAL_MESSAGES'] else 'Disabled'}")
        print(f"   • Bullish Signals: {'Enabled' if self.config['SEND_BULLISH_SIGNALS'] else 'Disabled'}")
        print(f"   • Bearish Signals: {'Enabled' if self.config['SEND_BEARISH_SIGNALS'] else 'Disabled'}")

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


