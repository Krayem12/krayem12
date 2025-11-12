# config/config_manager.py
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from .validators import ConfigValidator

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# 🛠️ الإصلاح: تهيئة نظام الأساسي للتسجيل أولاً
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
        """Final configuration setup with VALIDATION"""
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

            # 🎯 MULTI-MODE Trading Strategy Settings - مع التحقق من الصحة
            'TRADING_MODE': self._validate_trading_mode(os.getenv('TRADING_MODE', 'GROUP1_GROUP2_GROUP3')),
            'TRADING_MODE1': self._validate_trading_mode(os.getenv('TRADING_MODE1', 'GROUP1')),
            'TRADING_MODE2': self._validate_trading_mode(os.getenv('TRADING_MODE2', 'GROUP1')),
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

            # Trend Settings
            'RESPECT_TREND_FOR_REGULAR_TRADES': os.getenv('RESPECT_TREND_FOR_REGULAR_TRADES', 'true').lower() == 'true',
            'RESPECT_TREND_FOR_GROUP2': os.getenv('RESPECT_TREND_FOR_GROUP2', 'true').lower() == 'true',
            'RESET_TRADES_ON_TREND_CHANGE': os.getenv('RESET_TRADES_ON_TREND_CHANGE', 'true').lower() == 'true',
            'ENABLE_COUNTER_TREND_PRESERVATION': False,

            # 🆕 إعداد تخزين الإشارات المخالفة
            'STORE_CONTRARIAN_SIGNALS': os.getenv('STORE_CONTRARIAN_SIGNALS', 'false').lower() == 'true',

            # Notification Controls
            'SEND_TREND_MESSAGES': os.getenv('SEND_TREND_MESSAGES', 'false').lower() == 'true',
            'SEND_ENTRY_MESSAGES': os.getenv('SEND_ENTRY_MESSAGES', 'true').lower() == 'true',
            'SEND_EXIT_MESSAGES': os.getenv('SEND_EXIT_MESSAGES', 'true').lower() == 'true',
            'SEND_CONFIRMATION_MESSAGES': os.getenv('SEND_CONFIRMATION_MESSAGES', 'false').lower() == 'true',
            'SEND_GENERAL_MESSAGES': os.getenv('SEND_GENERAL_MESSAGES', 'false').lower() == 'true',

            # Daily Cleanup Settings
            'DAILY_CLEANUP_ENABLED': os.getenv('DAILY_CLEANUP_ENABLED', 'true').lower() == 'true',
            'DAILY_CLEANUP_TIME': os.getenv('DAILY_CLEANUP_TIME', '01:00'),

            # 🆕 إعدادات انتهاء صلاحية الإشارات
            'SIGNAL_TTL_MINUTES': self._safe_int_convert('SIGNAL_TTL_MINUTES', 180),  # 180 دقيقة افتراضياً
        }

        self.port = self._robust_port_handling()
        self.config['PORT'] = self.port
        
        # 🛠️ الإصلاح: تطبيق مستوى التسجيل على جميع اللوجرات
        self._apply_logging_config_enhanced()

        # 🎯 تحميل الإشارات مع قوائم GROUP3 المنفصلة
        self.signals = {
            'trend': self._load_signal_list('TREND_SIGNALS', 'bullish_tracer,bearish_tracer'),
            'trend_confirm': self._load_signal_list('TREND_CONFIRM_SIGNALS', 'rayian'),
            'entry_bullish': self._load_signal_list('ENTRY_SIGNALS_BULLISH', 'oversold_bullish_hyperwave_signal,regular_bullish_hyperwave_signal'),
            'entry_bearish': self._load_signal_list('ENTRY_SIGNALS_BEARISH', 'overbought_bearish_hyperwave_signal,regular_bullish_hyperwave_signal'),
            'exit': self._load_signal_list('EXIT_SIGNALS', 'exit_buy,exit_sell'),
            'general': self._load_signal_list('GENERAL_SIGNALS', 'krayem yhia alanizy'),
            'entry_bullish1': self._load_signal_list('ENTRY_SIGNALS_BULLISH1', 'Discount,bullish_catcher'),
            'entry_bearish1': self._load_signal_list('ENTRY_SIGNALS_BEARISH1', 'Premium,bearish_catcher'),
            # 🆕 قوائم GROUP3 المنفصلة للإشارات الصاعدة والهابطة
            'group3_bullish': self._load_signal_list('ENTRY_SIGNALS_GROUP3_BULLISH', 'bullish_moneyflow_above_50,bullish_moneyflow_co_50'),
            'group3_bearish': self._load_signal_list('ENTRY_SIGNALS_GROUP3_BEARISH', 'bearish_moneyflow_below_50,bearish_moneyflow_cu_50')
        }

        # 🛠️ الإصلاح: إضافة الإشارات إلى config للوصول العالمي
        self.config['signals'] = self.signals

        self.setup_keywords()
        self.validate_configuration()

    def _validate_trading_mode(self, mode_value):
        """🆕 التحقق من صحة نمط التداول"""
        valid_modes = ['GROUP1', 'GROUP1_GROUP2', 'GROUP1_GROUP3', 'GROUP1_GROUP2_GROUP3', 
                      'GROUP2_GROUP3', 'GROUP2', 'GROUP3']
        
        mode_clean = mode_value.strip().upper()
        
        if mode_clean not in valid_modes:
            logger.warning(f"⚠️ نمط تداول غير صالح: {mode_value}, استخدام GROUP1 افتراضي")
            return 'GROUP1'
        
        logger.info(f"✅ تم تحميل نمط التداول: {mode_clean}")
        return mode_clean

    def _apply_logging_config_enhanced(self):
        """🛠️ الإصلاح المحسّن النهائي: تطبيق إعدادات التسجيل مع معالجة urllib3"""
        try:
            log_level = self.config['LOG_LEVEL']
            debug_mode = self.config['DEBUG']
            
            print(f"🔧 تطبيق إعدادات التسجيل: DEBUG={debug_mode}, LOG_LEVEL={log_level}")
            
            # تحديد مستوى التسجيل الفعلي
            level_mapping = {
                'ERROR': logging.ERROR,
                'WARNING': logging.WARNING,
                'INFO': logging.INFO,
                'DEBUG': logging.DEBUG
            }
            level = level_mapping.get(log_level, logging.DEBUG)
            
            # 🛠️ الإصلاح: إعادة تهيئة نظام التسجيل بشكل كامل
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
                
            # إعادة التهيئة مع الإعدادات الجديدة
            logging.basicConfig(
                level=level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                force=True
            )
            
            # 🛠️ تطبيق مستوى التسجيل على جميع اللوجرات المعروفة في النظام
            loggers_to_configure = [
                '',  # اللوجر الرئيسي
                '__main__',
                'config_manager',
                'webhook_handler', 
                'signal_processor',
                'trade_manager',
                'group_manager',
                'notification_manager',
                'cleanup_manager',
                'trading_system',
                'core.webhook_handler',
                'core.signal_processor',
                'core.trade_manager',
                'core.group_manager',
                'notifications.notification_manager'
            ]
            
            for logger_name in loggers_to_configure:
                logger_instance = logging.getLogger(logger_name)
                logger_instance.setLevel(level)
                # إزالة أي معالجات قديمة
                for handler in logger_instance.handlers[:]:
                    logger_instance.removeHandler(handler)
            
            # 🛠️ الإصلاح النهائي: معالجة مشكلة urllib3 بشكل خاص
            urllib3_logger = logging.getLogger('urllib3.connectionpool')
            urllib3_logger.setLevel(logging.INFO)  # تقليل الضوضاء من DEBUG إلى INFO
            urllib3_logger.propagate = True
            
            # 🛠️ معالجة جميع لوغرات urllib3 ذات الصلة
            urllib3_related_loggers = [
                'urllib3',
                'urllib3.connectionpool',
                'urllib3.response',
                'urllib3.connection'
            ]
            
            for urllib_logger in urllib3_related_loggers:
                logger_instance = logging.getLogger(urllib_logger)
                logger_instance.setLevel(logging.INFO)
                # التأكد من أن الرسائل تظهر مع التنسيق الصحيح
                for handler in logger_instance.handlers[:]:
                    logger_instance.removeHandler(handler)
            
            # 🛠️ إخفاء رسائل المكتبات الخارجية إذا كان DEBUG=false
            if not debug_mode:
                external_loggers = ['werkzeug', 'schedule', 'urllib3', 'requests', 'urllib3.connectionpool']
                for ext_logger in external_loggers:
                    logging.getLogger(ext_logger).setLevel(logging.WARNING)
            else:
                # في وضع التصحيح، نسمح ببعض رسائل المكتبات
                logging.getLogger('werkzeug').setLevel(logging.INFO)
                # 🛠️ تقليل ضوضاء urllib3 حتى في وضع DEBUG
                for urllib_logger in urllib3_related_loggers:
                    logging.getLogger(urllib_logger).setLevel(logging.INFO)
            
            # 🎯 رسالة تأكيد على مستوى INFO حتى نراها دائماً
            logging.info(f"✅ تم تطبيق إعدادات التسجيل: DEBUG={debug_mode}, LOG_LEVEL={log_level}")
            print(f"🎯 إعدادات التسجيل النهائية: DEBUG={debug_mode}, LOG_LEVEL={log_level}")
            
            # 🆕 اختبار مباشر للوقو
            logging.debug("🔍 اختبار رسالة DEBUG - يجب أن تظهر إذا كان DEBUG=true")
            logging.info("ℹ️ اختبار رسالة INFO - يجب أن تظهر دائماً")
            
            # 🛠️ اختبار إضافي للتأكد من إعدادات urllib3
            urllib3_test_logger = logging.getLogger('urllib3.connectionpool')
            current_level = urllib3_test_logger.getEffectiveLevel()
            level_name = logging.getLevelName(current_level)
            print(f"🔧 مستوى تسجيل urllib3.connectionpool: {level_name}")
            
        except Exception as e:
            print(f"❌ خطأ في تطبيق إعدادات التسجيل: {e}")
            # القيم الافتراضية في حالة الخطأ
            logging.getLogger().setLevel(logging.DEBUG)

    def _robust_port_handling(self):
        """ROBUST port handling - works even with empty or invalid PORT"""
        try:
            port_value = os.getenv('PORT', '').strip()
            
            if not port_value:
                logging.info("🔧 PORT is empty or not set, using default: 10000")
                return 10000
            
            port_int = int(port_value)
            
            if 1 <= port_int <= 65535:
                logging.info(f"✅ PORT successfully loaded: {port_int}")
                return port_int
            else:
                logging.warning(f"⚠️ PORT {port_int} is out of range (1-65535), using default: 10000")
                return 10000
                
        except (ValueError, TypeError) as e:
            logging.error(f"⚠️ Invalid PORT value '{os.getenv('PORT')}', using default 10000: {e}")
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
            logging.error(f"⚠️ Invalid {env_key} value '{os.getenv(env_key)}', using default {default}: {e}")
            return default

    def _load_signal_list(self, env_key, default_signals=""):
        """Load signals from environment with default values"""
        try:
            signal_str = os.getenv(env_key, default_signals)
            if signal_str:
                signals = [s.strip() for s in signal_str.split(',') if s.strip()]
                logging.info(f"   ✅ Loaded {len(signals)} signals from {env_key}")
                return signals
            else:
                logging.warning(f"   ⚠️ No signals found for {env_key}, using defaults")
                return [s.strip() for s in default_signals.split(',') if s.strip()]
        except Exception as e:
            logging.error(f"   ❌ Error loading {env_key}: {e}, using defaults")
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
        
        logging.info("🚨 ملاحظة: نظام الكلمات المفتاحية غير مفعل - التطابق التام فقط")

    def validate_configuration(self):
        """Validate system configuration"""
        logging.info("\n🔍 Validating configuration...")
        
        errors, warnings = ConfigValidator.validate_config(self.config)
        
        if errors or warnings:
            validation_report = ConfigValidator.format_validation_report(errors, warnings)
            logging.info(f"📋 Configuration Validation Report:\n{validation_report}")
            
            if errors:
                logging.error("❌ Critical configuration errors detected")
                raise ValueError("Critical configuration errors detected")
            else:
                logging.warning("⚠️ Configuration has warnings but will continue...")
        else:
            logging.info("✅ All configuration validations passed")

    def display_config(self):
        """Display loaded configuration for verification"""
        logging.info("\n🔧 LOADED CONFIGURATION:")
        logging.info("   📱 Telegram: " + ("✅ ENABLED" if self.config['TELEGRAM_ENABLED'] else "❌ DISABLED"))
        logging.info("   🌐 External Server: " + ("✅ ENABLED" if self.config['EXTERNAL_SERVER_ENABLED'] else "❌ DISABLED"))
        logging.info("   🧹 Daily Cleanup: " + ("✅ ENABLED" if self.config['DAILY_CLEANUP_ENABLED'] else "❌ DISABLED"))
        if self.config['DAILY_CLEANUP_ENABLED']:
            logging.info(f"   🕐 Cleanup Time: {self.config['DAILY_CLEANUP_TIME']}")
        
        # 🎯 MULTI-MODE: Display Multi-Mode Strategy Settings
        logging.info("   🎯 Multi-Mode Trading Strategy:")
        logging.info(f"      • Mode: {self.config['TRADING_MODE']}")
        logging.info(f"      • Mode1: {self.config['TRADING_MODE1']} ({'✅ ENABLED' if self.config['TRADING_MODE1_ENABLED'] else '❌ DISABLED'})")
        logging.info(f"      • Mode2: {self.config['TRADING_MODE2']} ({'✅ ENABLED' if self.config['TRADING_MODE2_ENABLED'] else '❌ DISABLED'})")
        
        logging.info(f"      • Group1 Trend Mode: {self.config['GROUP1_TREND_MODE']}")
        logging.info(f"      • Required Group1: {self.config['REQUIRED_CONFIRMATIONS_GROUP1']}")
        logging.info(f"      • Group2 Enabled: {'✅ YES' if self.config['GROUP2_ENABLED'] else '❌ NO'}")
        if self.config['GROUP2_ENABLED']:
            logging.info(f"      • Required Group2: {self.config['REQUIRED_CONFIRMATIONS_GROUP2']}")
        logging.info(f"      • Group3 Enabled: {'✅ YES' if self.config['GROUP3_ENABLED'] else '❌ NO'}")
        if self.config['GROUP3_ENABLED']:
            logging.info(f"      • Required Group3: {self.config['REQUIRED_CONFIRMATIONS_GROUP3']}")
        
        # 🆕 عرض إعداد تخزين الإشارات المخالفة
        logging.info("   🔄 تخزين الإشارات المخالفة: " + ("✅ مفعل" if self.config['STORE_CONTRARIAN_SIGNALS'] else "❌ معطل"))
        
        # 🆕 عرض إشارات GROUP3 المنفصلة
        if self.config['GROUP3_ENABLED']:
            logging.info("   🟢 Group3 Signals:")
            logging.info(f"      • Bullish: {len(self.signals['group3_bullish'])} signals")
            logging.info(f"      • Bearish: {len(self.signals['group3_bearish'])} signals")
        
        # 🆕 عرض إعدادات انتهاء صلاحية الإشارات
        logging.info("   ⏰ Signal Expiration Settings:")
        logging.info(f"      • Signal TTL: {self.config['SIGNAL_TTL_MINUTES']} minutes")
        
        logging.info("   📊 Message Controls:")
        logging.info("      • Trend Messages: " + ("✅ ON" if self.config['SEND_TREND_MESSAGES'] else "❌ OFF"))
        logging.info("      • Entry Messages: " + ("✅ ON" if self.config['SEND_ENTRY_MESSAGES'] else "❌ OFF"))
        logging.info("      • Exit Messages: " + ("✅ ON" if self.config['SEND_EXIT_MESSAGES'] else "❌ OFF"))
        logging.info(f"   🌐 Server Port: {self.port}")