# config/config_manager.py
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from .validators import ConfigValidator

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.signals = {}
        self.keywords = {}
        self.port = 10000
        self.setup_config()

    def setup_config(self):
        """Final configuration setup with NEW STRATEGY SETTINGS"""
        self.config = {
            # Basic Settings
            'DEBUG': os.getenv('DEBUG', 'true').lower() == 'true',
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'DEBUG').upper(),

            # Telegram Settings
            'TELEGRAM_ENABLED': os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true',
            'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN', 'dummy_token_for_development'),
            'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', 'dummy_chat_id'),

            # External Server Settings
            'EXTERNAL_SERVER_ENABLED': os.getenv('EXTERNAL_SERVER_ENABLED', 'true').lower() == 'true',
            'EXTERNAL_SERVER_URL': os.getenv('EXTERNAL_SERVER_URL', 'https://example.com'),

            # Trade Management Settings
            'MAX_OPEN_TRADES': self._safe_int_convert('MAX_OPEN_TRADES', 10),
            'MAX_TRADES_PER_SYMBOL': self._safe_int_convert('MAX_TRADES_PER_SYMBOL', 3),

            # 🎯 NEW: Trading Strategy Settings
            'TRADING_MODE': os.getenv('TRADING_MODE', 'GROUP1_GROUP2_GROUP3').strip().upper(),
            
            # Group1 Settings
            'REQUIRED_CONFIRMATIONS_GROUP1': self._safe_int_convert('REQUIRED_CONFIRMATIONS_GROUP1', 2),
            'GROUP1_TREND_MODE': os.getenv('GROUP1_TREND_MODE', 'ONLY_TREND').strip().upper(),

            # Group2 Settings
            'GROUP2_ENABLED': os.getenv('GROUP2_ENABLED', 'true').lower() == 'true',
            'REQUIRED_CONFIRMATIONS_GROUP2': self._safe_int_convert('REQUIRED_CONFIRMATIONS_GROUP2', 1),

            # Group3 Settings
            'GROUP3_ENABLED': os.getenv('GROUP3_ENABLED', 'true').lower() == 'true',
            'REQUIRED_CONFIRMATIONS_GROUP3': self._safe_int_convert('REQUIRED_CONFIRMATIONS_GROUP3', 1),

            # Trend Settings
            'RESPECT_TREND_FOR_REGULAR_TRADES': os.getenv('RESPECT_TREND_FOR_REGULAR_TRADES', 'true').lower() == 'true',
            'RESPECT_TREND_FOR_GROUP2': os.getenv('RESPECT_TREND_FOR_GROUP2', 'true').lower() == 'true',
            'RESET_TRADES_ON_TREND_CHANGE': os.getenv('RESET_TRADES_ON_TREND_CHANGE', 'true').lower() == 'true',
            'ENABLE_COUNTER_TREND_PRESERVATION': False,

            # Notification Controls
            'SEND_TREND_MESSAGES': os.getenv('SEND_TREND_MESSAGES', 'false').lower() == 'true',
            'SEND_ENTRY_MESSAGES': os.getenv('SEND_ENTRY_MESSAGES', 'true').lower() == 'true',
            'SEND_EXIT_MESSAGES': os.getenv('SEND_EXIT_MESSAGES', 'true').lower() == 'true',
            'SEND_CONFIRMATION_MESSAGES': os.getenv('SEND_CONFIRMATION_MESSAGES', 'false').lower() == 'true',
            'SEND_GENERAL_MESSAGES': os.getenv('SEND_GENERAL_MESSAGES', 'false').lower() == 'true',
            'SEND_BULLISH_SIGNALS': os.getenv('SEND_BULLISH_SIGNALS', 'true').lower() == 'true',
            'SEND_BEARISH_SIGNALS': os.getenv('SEND_BEARISH_SIGNALS', 'true').lower() == 'true',

            # Timeout Settings
            'CONFIRMATION_TIMEOUT': self._safe_int_convert('CONFIRMATION_TIMEOUT', 900),
            'DUAL_CONFIRMATION_TIMEOUT': self._safe_int_convert('DUAL_CONFIRMATION_TIMEOUT', 3600),

            # Daily Cleanup Settings
            'DAILY_CLEANUP_ENABLED': os.getenv('DAILY_CLEANUP_ENABLED', 'true').lower() == 'true',
            'DAILY_CLEANUP_TIME': os.getenv('DAILY_CLEANUP_TIME', '01:00'),
        }

        self.port = self._robust_port_handling()
        self.config['PORT'] = self.port
        
        logger.setLevel(getattr(logging, self.config['LOG_LEVEL'], logging.INFO))

        # تحميل الإشارات مع قيم افتراضية
        self.signals = {
            'trend': self._load_signal_list('TREND_SIGNALS', 'switch_bullish_catcher,switch_bearish_catcher,bullish_catcher,bearish_catcher'),
            'trend_confirm': self._load_signal_list('TREND_CONFIRM_SIGNALS', 'switch_bullish_tracer,switch_bearish_tracer'),
            'entry_bullish': self._load_signal_list('ENTRY_SIGNALS_BULLISH', 'bullish moneyflow_co_50,oversold_bullish_hyperwave_signal,bullish_divergence'),
            'entry_bearish': self._load_signal_list('ENTRY_SIGNALS_BEARISH', 'Bearish moneyflow_cu_50,overbought_bearish_hyperwave_signal,bearish_divergence'),
            'exit': self._load_signal_list('EXIT_SIGNALS', 'bullish_exit,bearish_exit,take_profit,stop_loss'),
            'general': self._load_signal_list('GENERAL_SIGNALS', 'krayem yhia alanizy'),
            'entry_bullish1': self._load_signal_list('ENTRY_SIGNALS_BULLISH1', 'Discount'),
            'entry_bearish1': self._load_signal_list('ENTRY_SIGNALS_BEARISH1', 'Premium'),
            'group3': self._load_signal_list('ENTRY_SIGNALS_GROUP3', 'moneyflow_above_50,moneyflow_below_50')
        }

        self.setup_keywords()
        self.validate_configuration()

    def _robust_port_handling(self):
        """ROBUST port handling - works even with empty or invalid PORT"""
        try:
            port_value = os.getenv('PORT', '').strip()
            
            if not port_value:
                print("🔧 PORT is empty or not set, using default: 10000")
                return 10000
            
            port_int = int(port_value)
            
            if 1 <= port_int <= 65535:
                print(f"✅ PORT successfully loaded: {port_int}")
                return port_int
            else:
                print(f"⚠️ PORT {port_int} is out of range (1-65535), using default: 10000")
                return 10000
                
        except (ValueError, TypeError) as e:
            print(f"⚠️ Invalid PORT value '{os.getenv('PORT')}', using default 10000: {e}")
            return 10000

    def _safe_int_convert(self, env_key, default):
        """Safe integer conversion with error handling"""
        try:
            value = os.getenv(env_key)
            if value is None:
                return default

            cleaned_value = value.strip()
            if not cleaned_value:
                return default

            return int(cleaned_value)
        except (ValueError, TypeError) as e:
            print(f"⚠️ Invalid {env_key} value '{os.getenv(env_key)}', using default {default}: {e}")
            return default

    def _load_signal_list(self, env_key, default_signals=""):
        """Load signals from environment with default values"""
        try:
            signal_str = os.getenv(env_key, default_signals)
            if signal_str:
                signals = [s.strip() for s in signal_str.split(',') if s.strip()]
                print(f"   ✅ Loaded {len(signals)} signals from {env_key}")
                return signals
            else:
                print(f"   ⚠️ No signals found for {env_key}, using defaults")
                return [s.strip() for s in default_signals.split(',') if s.strip()]
        except Exception as e:
            print(f"   ❌ Error loading {env_key}: {e}, using defaults")
            return [s.strip() for s in default_signals.split(',') if s.strip()]

    def setup_keywords(self):
        """Setup keywords from .env"""
        bullish_kw = os.getenv('BULLISH_KEYWORDS', 'bullish,buy,long,call,up,upside')
        bearish_kw = os.getenv('BEARISH_KEYWORDS', 'bearish,sell,short,put,down,downside')
        trend_kw = os.getenv('TREND_KEYWORDS', 'catcher')
        trend_confirm_kw = os.getenv('TREND_CONFIRM_KEYWORDS', 'tracer')
        exit_kw = os.getenv('EXIT_KEYWORDS', 'exit,close,take profit,stop loss')
        group3_kw = os.getenv('GROUP3_KEYWORDS', 'moneyflow_above_50,moneyflow_below_50,SPX500')

        self.keywords = {
            'bullish': [kw.strip() for kw in bullish_kw.split(',')],
            'bearish': [kw.strip() for kw in bearish_kw.split(',')],
            'trend': [kw.strip() for kw in trend_kw.split(',')],
            'trend_confirm': [kw.strip() for kw in trend_confirm_kw.split(',')],
            'exit': [kw.strip() for kw in exit_kw.split(',')],
            'group3': [kw.strip() for kw in group3_kw.split(',')]
        }

    def validate_configuration(self):
        """Validate system configuration"""
        print("\n🔍 Validating configuration...")
        
        errors, warnings = ConfigValidator.validate_config(self.config)
        
        if errors or warnings:
            validation_report = ConfigValidator.format_validation_report(errors, warnings)
            print(f"📋 Configuration Validation Report:\n{validation_report}")
            
            if errors:
                print("❌ Critical configuration errors detected")
                raise ValueError("Critical configuration errors detected")
            else:
                print("⚠️ Configuration has warnings but will continue...")
        else:
            print("✅ All configuration validations passed")

    def display_config(self):
        """Display loaded configuration for verification"""
        print("\n🔧 LOADED CONFIGURATION:")
        print("   📱 Telegram:", "✅ ENABLED" if self.config['TELEGRAM_ENABLED'] else "❌ DISABLED")
        print("   🌐 External Server:", "✅ ENABLED" if self.config['EXTERNAL_SERVER_ENABLED'] else "❌ DISABLED")
        print("   🧹 Daily Cleanup:", "✅ ENABLED" if self.config['DAILY_CLEANUP_ENABLED'] else "❌ DISABLED")
        if self.config['DAILY_CLEANUP_ENABLED']:
            print(f"   🕐 Cleanup Time: {self.config['DAILY_CLEANUP_TIME']}")
        
        # 🎯 NEW: Display Strategy Settings
        print("   🎯 Trading Strategy:")
        print(f"      • Mode: {self.config['TRADING_MODE']}")
        print(f"      • Group1 Trend Mode: {self.config['GROUP1_TREND_MODE']}")
        print(f"      • Required Group1: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']}")
        print(f"      • Group2 Enabled: {'✅ YES' if self.config['GROUP2_ENABLED'] else '❌ NO'}")
        if self.config['GROUP2_ENABLED']:
            print(f"      • Required Group2: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']}")
        print(f"      • Group3 Enabled: {'✅ YES' if self.config['GROUP3_ENABLED'] else '❌ NO'}")
        if self.config['GROUP3_ENABLED']:
            print(f"      • Required Group3: {self.config['REQUIRED_CONFIRMATIONS_GROUP3']}")
        
        print("   📊 Message Controls:")
        print("      • Trend Messages:", "✅ ON" if self.config['SEND_TREND_MESSAGES'] else "❌ OFF")
        print("      • Entry Messages:", "✅ ON" if self.config['SEND_ENTRY_MESSAGES'] else "❌ OFF")
        print("      • Exit Messages:", "✅ ON" if self.config['SEND_EXIT_MESSAGES'] else "❌ OFF")
        print(f"   🌐 Server Port: {self.port}")