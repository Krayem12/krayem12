# config/config_manager.py
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from .validators import ConfigValidator

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# 🛠️ الإصلاح: تهيئة النظام الأساسي للتسجيل أولاً
logging.basicConfig(
    level=logging.ERROR,  # المستوى الافتراضي حتى يتم تحميل الإعدادات
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.signals = {}
        self.keywords = {}
        self.port = 10000
        self.setup_config()

    def setup_config(self):
        """Final configuration setup with SEPARATE GROUP3 LISTS"""
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

            # 🎯 MULTI-MODE Trading Strategy Settings
            'TRADING_MODE': os.getenv('TRADING_MODE', 'GROUP1_GROUP2_GROUP3').strip().upper(),
            'TRADING_MODE1': os.getenv('TRADING_MODE1', 'GROUP1').strip().upper(),
            'TRADING_MODE2': os.getenv('TRADING_MODE2', 'GROUP1').strip().upper(),
            'TRADING_MODE1_ENABLED': os.getenv('TRADING_MODE1_ENABLED', 'false').lower() == 'true',
            'TRADING_MODE2_ENABLED': os.getenv('TRADING_MODE2_ENABLED', 'false').lower() == 'true',

            # Group1 Settings
            'REQUIRED_CONFIRMATIONS_GROUP1': self._safe_int_convert('REQUIRED_CONFIRMATIONS_GROUP1', 2),
            'GROUP1_TREND_MODE': os.getenv('GROUP1_TREND_MODE', 'ONLY_TREND').strip().upper(),

            # Group2 Settings
            'GROUP2_ENABLED': os.getenv('GROUP2_ENABLED', 'true').lower() == 'true',
            'REQUIRED_CONFIRMATIONS_GROUP2': self._safe_int_convert('REQUIRED_CONFIRMATIONS_GROUP2', 1),

            # Group3 Settings
            'GROUP3_ENABLED': os.getenv('GROUP3_ENABLED', 'true').lower() == 'true',
            'REQUIRED_CONFIRMATIONS_GROUP3': self._safe_int_convert('REQUIRED_CONFIRMATIONS_GROUP3', 1),

            # 🆕 إزالة: إعدادات التنظيف المضللة
            # 'SIGNAL_CLEANUP_INTERVAL_MINUTES': self._safe_int_convert('SIGNAL_CLEANUP_INTERVAL_MINUTES', 5),

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

            # Daily Cleanup Settings
            'DAILY_CLEANUP_ENABLED': os.getenv('DAILY_CLEANUP_ENABLED', 'true').lower() == 'true',
            'DAILY_CLEANUP_TIME': os.getenv('DAILY_CLEANUP_TIME', '01:00'),
        }

        self.port = self._robust_port_handling()
        self.config['PORT'] = self.port
        
        # 🛠️ الإصلاح: تطبيق مستوى التسجيل على جميع اللوجرات
        self._apply_logging_config()

        # 🎯 تحميل الإشارات مع قوائم GROUP3 المنفصلة
        self.signals = {
            'trend': self._load_signal_list('TREND_SIGNALS', 'switch_bullish_catcher,switch_bearish_catcher,bullish_catcher,bearish_catcher'),
            'trend_confirm': self._load_signal_list('TREND_CONFIRM_SIGNALS', 'switch_bullish_tracer,switch_bearish_tracer'),
            'entry_bullish': self._load_signal_list('ENTRY_SIGNALS_BULLISH', 'bullish moneyflow_co_50,oversold_bullish_hyperwave_signal,bullish_divergence'),
            'entry_bearish': self._load_signal_list('ENTRY_SIGNALS_BEARISH', 'Bearish moneyflow_cu_50,overbought_bearish_hyperwave_signal,bearish_divergence'),
            'exit': self._load_signal_list('EXIT_SIGNALS', 'bullish_exit,bearish_exit,take_profit,stop_loss'),
            'general': self._load_signal_list('GENERAL_SIGNALS', 'krayem yhia alanizy'),
            'entry_bullish1': self._load_signal_list('ENTRY_SIGNALS_BULLISH1', 'Discount'),
            'entry_bearish1': self._load_signal_list('ENTRY_SIGNALS_BEARISH1', 'Premium'),
            # 🆕 قوائم GROUP3 المنفصلة للإشارات الصاعدة والهابطة
            'group3_bullish': self._load_signal_list('ENTRY_SIGNALS_GROUP3_BULLISH', 'moneyflow_above_50,moneyflow_co_50'),
            'group3_bearish': self._load_signal_list('ENTRY_SIGNALS_GROUP3_BEARISH', 'moneyflow_below_50,moneyflow_cu_50')
        }

        self.setup_keywords()
        self.validate_configuration()

    def _apply_logging_config(self):
        """🛠️ تطبيق إعدادات التسجيل على جميع اللوجرات"""
        try:
            log_level = self.config['LOG_LEVEL']
            debug_mode = self.config['DEBUG']
            
            # تحديد مستوى التسجيل الفعلي
            if log_level == 'ERROR':
                level = logging.ERROR
            elif log_level == 'WARNING':
                level = logging.WARNING
            elif log_level == 'INFO':
                level = logging.INFO
            elif log_level == 'DEBUG':
                level = logging.DEBUG
            else:
                level = logging.INFO  # افتراضي
            
            # 🛠️ تطبيق على جميع اللوجرات
            logging.getLogger().setLevel(level)
            
            # إذا كان DEBUG=false، نخفي الرسائل التفصيلية
            if not debug_mode:
                # إخفاء رسائل التصحيح التفصيلية
                logging.getLogger('werkzeug').setLevel(logging.WARNING)
                logging.getLogger('schedule').setLevel(logging.WARNING)
                logging.getLogger('urllib3').setLevel(logging.WARNING)
            
            logger.info(f"✅ تم تطبيق إعدادات التسجيل: LOG_LEVEL={log_level}, DEBUG={debug_mode}")
            
        except Exception as e:
            logger.error(f"⚠️ خطأ في تطبيق إعدادات التسجيل: {e}")
            # القيم الافتراضية في حالة الخطأ
            logging.getLogger().setLevel(logging.ERROR)

    def _robust_port_handling(self):
        """ROBUST port handling - works even with empty or invalid PORT"""
        try:
            port_value = os.getenv('PORT', '').strip()
            
            if not port_value:
                logger.info("🔧 PORT is empty or not set, using default: 10000")
                return 10000
            
            port_int = int(port_value)
            
            if 1 <= port_int <= 65535:
                logger.info(f"✅ PORT successfully loaded: {port_int}")
                return port_int
            else:
                logger.warning(f"⚠️ PORT {port_int} is out of range (1-65535), using default: 10000")
                return 10000
                
        except (ValueError, TypeError) as e:
            logger.error(f"⚠️ Invalid PORT value '{os.getenv('PORT')}', using default 10000: {e}")
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
            logger.error(f"⚠️ Invalid {env_key} value '{os.getenv(env_key)}', using default {default}: {e}")
            return default

    def _load_signal_list(self, env_key, default_signals=""):
        """Load signals from environment with default values"""
        try:
            signal_str = os.getenv(env_key, default_signals)
            if signal_str:
                signals = [s.strip() for s in signal_str.split(',') if s.strip()]
                logger.info(f"   ✅ Loaded {len(signals)} signals from {env_key}")
                return signals
            else:
                logger.warning(f"   ⚠️ No signals found for {env_key}, using defaults")
                return [s.strip() for s in default_signals.split(',') if s.strip()]
        except Exception as e:
            logger.error(f"   ❌ Error loading {env_key}: {e}, using defaults")
            return [s.strip() for s in default_signals.split(',') if s.strip()]

    def setup_keywords(self):
        """🎯 إعداد الكلمات المفتاحية - للتوافق فقط ولكن لا تستخدم"""
        # 🚨 هذه الكلمات لا تستخدم في التصنيف بعد الآن
        bullish_kw = os.getenv('BULLISH_KEYWORDS', '')
        bearish_kw = os.getenv('BEARISH_KEYWORDS', '')
        trend_kw = os.getenv('TREND_KEYWORDS', '')
        trend_confirm_kw = os.getenv('TREND_CONFIRM_KEYWORDS', '')
        exit_kw = os.getenv('EXIT_KEYWORDS', '')
        group3_kw = os.getenv('GROUP3_KEYWORDS', '')

        self.keywords = {
            'bullish': [kw.strip() for kw in bullish_kw.split(',') if kw.strip()],
            'bearish': [kw.strip() for kw in bearish_kw.split(',') if kw.strip()],
            'trend': [kw.strip() for kw in trend_kw.split(',') if kw.strip()],
            'trend_confirm': [kw.strip() for kw in trend_confirm_kw.split(',') if kw.strip()],
            'exit': [kw.strip() for kw in exit_kw.split(',') if kw.strip()],
            'group3': [kw.strip() for kw in group3_kw.split(',') if kw.strip()]
        }
        
        logger.info("🚨 ملاحظة: نظام الكلمات المفتاحية غير مفعل - التطابق التام فقط")

    def validate_configuration(self):
        """Validate system configuration"""
        logger.info("\n🔍 Validating configuration...")
        
        errors, warnings = ConfigValidator.validate_config(self.config)
        
        if errors or warnings:
            validation_report = ConfigValidator.format_validation_report(errors, warnings)
            logger.info(f"📋 Configuration Validation Report:\n{validation_report}")
            
            if errors:
                logger.error("❌ Critical configuration errors detected")
                raise ValueError("Critical configuration errors detected")
            else:
                logger.warning("⚠️ Configuration has warnings but will continue...")
        else:
            logger.info("✅ All configuration validations passed")

    def display_config(self):
        """Display loaded configuration for verification"""
        logger.info("\n🔧 LOADED CONFIGURATION:")
        logger.info("   📱 Telegram: " + ("✅ ENABLED" if self.config['TELEGRAM_ENABLED'] else "❌ DISABLED"))
        logger.info("   🌐 External Server: " + ("✅ ENABLED" if self.config['EXTERNAL_SERVER_ENABLED'] else "❌ DISABLED"))
        logger.info("   🧹 Daily Cleanup: " + ("✅ ENABLED" if self.config['DAILY_CLEANUP_ENABLED'] else "❌ DISABLED"))
        if self.config['DAILY_CLEANUP_ENABLED']:
            logger.info(f"   🕐 Cleanup Time: {self.config['DAILY_CLEANUP_TIME']}")
        
        # 🎯 MULTI-MODE: Display Multi-Mode Strategy Settings
        logger.info("   🎯 Multi-Mode Trading Strategy:")
        logger.info(f"      • Mode: {self.config['TRADING_MODE']}")
        logger.info(f"      • Mode1: {self.config['TRADING_MODE1']} ({'✅ ENABLED' if self.config['TRADING_MODE1_ENABLED'] else '❌ DISABLED'})")
        logger.info(f"      • Mode2: {self.config['TRADING_MODE2']} ({'✅ ENABLED' if self.config['TRADING_MODE2_ENABLED'] else '❌ DISABLED'})")
        
        logger.info(f"      • Group1 Trend Mode: {self.config['GROUP1_TREND_MODE']}")
        logger.info(f"      • Required Group1: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']}")
        logger.info(f"      • Group2 Enabled: {'✅ YES' if self.config['GROUP2_ENABLED'] else '❌ NO'}")
        if self.config['GROUP2_ENABLED']:
            logger.info(f"      • Required Group2: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']}")
        logger.info(f"      • Group3 Enabled: {'✅ YES' if self.config['GROUP3_ENABLED'] else '❌ NO'}")
        if self.config['GROUP3_ENABLED']:
            logger.info(f"      • Required Group3: {self.config['REQUIRED_CONFIRMATIONS_GROUP3']}")
        
        # 🆕 إزالة: إعدادات التنظيف المضللة
        # logger.info("   ⚙️ Cleanup Settings:")
        # logger.info(f"      • Cleanup Interval: {cleanup_interval} minutes")
        # logger.info(f"      • Signal Max Age: {cleanup_interval * 3} minutes (تلقائي)")
        
        # 🆕 عرض إشارات GROUP3 المنفصلة
        if self.config['GROUP3_ENABLED']:
            logger.info("   🟢 Group3 Signals:")
            logger.info(f"      • Bullish: {len(self.signals['group3_bullish'])} signals")
            logger.info(f"      • Bearish: {len(self.signals['group3_bearish'])} signals")
        
        logger.info("   📊 Message Controls:")
        logger.info("      • Trend Messages: " + ("✅ ON" if self.config['SEND_TREND_MESSAGES'] else "❌ OFF"))
        logger.info("      • Entry Messages: " + ("✅ ON" if self.config['SEND_ENTRY_MESSAGES'] else "❌ OFF"))
        logger.info("      • Exit Messages: " + ("✅ ON" if self.config['SEND_EXIT_MESSAGES'] else "❌ OFF"))
        logger.info(f"   🌐 Server Port: {self.port}")