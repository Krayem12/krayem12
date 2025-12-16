import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
import json

from .validators import ConfigValidator

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

logger = logging.getLogger(__name__)

class ConfigManager:
    """🎯 مدير الإعدادات بدون أي قيم افتراضية - يدعم جميع تجميعات المجموعات"""

    def __init__(self):
        self.config = {}
        self.signals = {}
        self.keywords = {}
        self.port = 10000
        self._error_log = []
        self.setup_config()

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """🎯 معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append(full_error)

    def _validate_required_env_vars(self) -> None:
        """التحقق من وجود المتغيرات البيئية المطلوبة - محدث لدعم جميع المجموعات"""
        required_vars = [
            # Basic Settings
            'DEBUG', 'LOG_LEVEL', 'PORT', 
            
            # Telegram Settings
            'TELEGRAM_ENABLED', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
            
            # External Server Settings
            'EXTERNAL_SERVER_ENABLED', 'EXTERNAL_SERVER_URL',
            
            # Trade Management Settings
            'MAX_OPEN_TRADES', 'MAX_TRADES_PER_SYMBOL', 
            'MAX_TRADES_MODE_MAIN', 'MAX_TRADES_MODE1', 'MAX_TRADES_MODE2',
            
            # 🎯 MULTI-MODE Trading Strategy Settings - محدث
            'TRADING_MODE', 'TRADING_MODE1', 'TRADING_MODE2',
            'TRADING_MODE1_ENABLED', 'TRADING_MODE2_ENABLED',
            
            # Group Settings - محدث ليشمل جميع المجموعات
            'REQUIRED_CONFIRMATIONS_GROUP1', 'GROUP1_TREND_MODE',
            'GROUP2_ENABLED', 'REQUIRED_CONFIRMATIONS_GROUP2',
            'GROUP3_ENABLED', 'REQUIRED_CONFIRMATIONS_GROUP3',
            'GROUP4_ENABLED', 'REQUIRED_CONFIRMATIONS_GROUP4',
            'GROUP5_ENABLED', 'REQUIRED_CONFIRMATIONS_GROUP5',
            
            # 🎯 إعدادات نظام تجميع إشارات الاتجاه
            'TREND_REQUIRED_SIGNALS',
            
            # Trend Settings
            'RESET_TRADES_ON_TREND_CHANGE', 'RESPECT_TREND_FOR_REGULAR_TRADES',
            'RESPECT_TREND_FOR_GROUP2',
            
            # Signal Storage
            'STORE_CONTRARIAN_SIGNALS',
            
            # Notification Controls
            'SEND_TREND_MESSAGES', 'SEND_ENTRY_MESSAGES', 'SEND_EXIT_MESSAGES',
            'SEND_CONFIRMATION_MESSAGES', 'SEND_GENERAL_MESSAGES',
            
            # Cleanup Settings
            'DAILY_CLEANUP_ENABLED', 'DAILY_CLEANUP_TIME', 'SIGNAL_TTL_MINUTES',
            
            # 🎯 إعدادات منع التكرار
            'DUPLICATE_SIGNAL_BLOCK_TIME', 'DUPLICATE_CLEANUP_INTERVAL',
        ]
        
        missing_vars = []
        for var in required_vars:
            if os.getenv(var) is None:
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"❌ متغيرات بيئية مطلوبة مفقودة: {', '.join(missing_vars)}")

    def _get_env_str(self, key: str, default: str = None) -> str:
        """قراءة قيمة نصية من البيئة"""
        value = os.getenv(key)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"❌ المتغير البيئي المطلوب '{key}' غير موجود")
        return value.strip()

    def _get_env_int(self, key: str, default: int = None) -> int:
        """قراءة قيمة رقمية من البيئة"""
        value = os.getenv(key)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"❌ المتغير البيئي المطلوب '{key}' غير موجود")
        try:
            return int(value.strip())
        except (ValueError, TypeError) as e:
            if default is not None:
                return default
            raise ValueError(f"❌ قيمة غير صالحة للمتغير '{key}': {value}") from e

    def _get_env_bool(self, key: str, default: bool = None) -> bool:
        """قراءة قيمة منطقية من البيئة"""
        value = os.getenv(key)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"❌ المتغير البيئي المطلوب '{key}' غير موجود")
        
        value_str = value.strip().lower()
        if value_str in ['true', '1', 'yes', 'y', 'on']:
            return True
        elif value_str in ['false', '0', 'no', 'n', 'off']:
            return False
        else:
            if default is not None:
                return default
            raise ValueError(f"❌ قيمة غير صالحة للمتغير '{key}': {value}")

    def setup_config(self) -> None:
        """🎯 الإعداد النهائي للتكوين بدون قيم افتراضية - محدث للتجميعات"""
        try:
            logger.info("🔧 بدء تحميل إعدادات النظام بدون قيم افتراضية...")
            
            # التحقق من وجود المتغيرات الأساسية المطلوبة
            self._validate_required_env_vars()
            
            self.config = {
                # Basic Settings - بدون قيم افتراضية
                'DEBUG': self._get_env_bool('DEBUG'),
                'LOG_LEVEL': self._get_env_str('LOG_LEVEL'),
                'PORT': self._get_env_int('PORT'),

                # Telegram Settings - بدون قيم افتراضية
                'TELEGRAM_ENABLED': self._get_env_bool('TELEGRAM_ENABLED'),
                'TELEGRAM_BOT_TOKEN': self._get_env_str('TELEGRAM_BOT_TOKEN'),
                'TELEGRAM_CHAT_ID': self._get_env_str('TELEGRAM_CHAT_ID'),

                # External Server Settings - بدون قيم افتراضية
                'EXTERNAL_SERVER_ENABLED': self._get_env_bool('EXTERNAL_SERVER_ENABLED'),
                'EXTERNAL_SERVER_URL': self._get_env_str('EXTERNAL_SERVER_URL'),

                # Trade Management Settings - بدون قيم افتراضية
                'MAX_OPEN_TRADES': self._get_env_int('MAX_OPEN_TRADES'),
                'MAX_TRADES_PER_SYMBOL': self._get_env_int('MAX_TRADES_PER_SYMBOL'),
                'MAX_TRADES_MODE_MAIN': self._get_env_int('MAX_TRADES_MODE_MAIN'),
                'MAX_TRADES_MODE1': self._get_env_int('MAX_TRADES_MODE1'),
                'MAX_TRADES_MODE2': self._get_env_int('MAX_TRADES_MODE2'),

                # 🎯 MULTI-MODE Trading Strategy Settings - محدث للتجميعات
                'TRADING_MODE': self._get_env_str('TRADING_MODE'),
                'TRADING_MODE1': self._get_env_str('TRADING_MODE1'),
                'TRADING_MODE2': self._get_env_str('TRADING_MODE2'),
                'TRADING_MODE1_ENABLED': self._get_env_bool('TRADING_MODE1_ENABLED'),
                'TRADING_MODE2_ENABLED': self._get_env_bool('TRADING_MODE2_ENABLED'),

                # Group Settings - محدث لجميع المجموعات
                'GROUP1_ENABLED': True,  # ✅ المجموعة 1 مفعلة دائماً
                'REQUIRED_CONFIRMATIONS_GROUP1': self._get_env_int('REQUIRED_CONFIRMATIONS_GROUP1'),
                'GROUP1_TREND_MODE': self._get_env_str('GROUP1_TREND_MODE'),
                'GROUP2_ENABLED': self._get_env_bool('GROUP2_ENABLED'),
                'REQUIRED_CONFIRMATIONS_GROUP2': self._get_env_int('REQUIRED_CONFIRMATIONS_GROUP2'),
                'GROUP3_ENABLED': self._get_env_bool('GROUP3_ENABLED'),
                'REQUIRED_CONFIRMATIONS_GROUP3': self._get_env_int('REQUIRED_CONFIRMATIONS_GROUP3'),
                'GROUP4_ENABLED': self._get_env_bool('GROUP4_ENABLED'),
                'REQUIRED_CONFIRMATIONS_GROUP4': self._get_env_int('REQUIRED_CONFIRMATIONS_GROUP4'),
                'GROUP5_ENABLED': self._get_env_bool('GROUP5_ENABLED'),
                'REQUIRED_CONFIRMATIONS_GROUP5': self._get_env_int('REQUIRED_CONFIRMATIONS_GROUP5'),

                # 🎯 إعدادات نظام تجميع إشارات الاتجاه - بدون قيم افتراضية
                'TREND_CHANGE_THRESHOLD': self._get_env_int('TREND_REQUIRED_SIGNALS'),

                # Trend Settings - بدون قيم افتراضية
                'RESPECT_TREND_FOR_REGULAR_TRADES': self._get_env_bool('RESPECT_TREND_FOR_REGULAR_TRADES'),
                'RESPECT_TREND_FOR_GROUP2': self._get_env_bool('RESPECT_TREND_FOR_GROUP2'),
                'RESET_TRADES_ON_TREND_CHANGE': self._get_env_bool('RESET_TRADES_ON_TREND_CHANGE'),
                'ENABLE_COUNTER_TREND_PRESERVATION': False,

                # Signal Storage - بدون قيم افتراضية
                'STORE_CONTRARIAN_SIGNALS': self._get_env_bool('STORE_CONTRARIAN_SIGNALS'),

                # Notification Controls - بدون قيم افتراضية
                'SEND_TREND_MESSAGES': self._get_env_bool('SEND_TREND_MESSAGES'),
                'SEND_ENTRY_MESSAGES': self._get_env_bool('SEND_ENTRY_MESSAGES'),
                'SEND_EXIT_MESSAGES': self._get_env_bool('SEND_EXIT_MESSAGES'),
                'SEND_CONFIRMATION_MESSAGES': self._get_env_bool('SEND_CONFIRMATION_MESSAGES'),
                'SEND_GENERAL_MESSAGES': self._get_env_bool('SEND_GENERAL_MESSAGES'),

                # Cleanup Settings - بدون قيم افتراضية
                'DAILY_CLEANUP_ENABLED': self._get_env_bool('DAILY_CLEANUP_ENABLED'),
                'DAILY_CLEANUP_TIME': self._get_env_str('DAILY_CLEANUP_TIME'),
                'SIGNAL_TTL_MINUTES': self._get_env_int('SIGNAL_TTL_MINUTES'),
                
                # 🎯 إعدادات منع التكرار - بدون قيم افتراضية
                'DUPLICATE_SIGNAL_BLOCK_TIME': self._get_env_int('DUPLICATE_SIGNAL_BLOCK_TIME'),
                'DUPLICATE_CLEANUP_INTERVAL': self._get_env_int('DUPLICATE_CLEANUP_INTERVAL'),
            }

            self.port = self.config['PORT']
            
            self._apply_logging_config_enhanced()
            self._validate_trading_modes_strict()

            # 🔧 FIXED: تحميل الإشارات بعد تكوين التطبيق وفحصها
            logger.info("📥 جاري تحميل الإشارات...")
            self.signals = self._load_all_signals_enhanced()
            
            # 🔧 FIXED: التحقق من أن الإشارات محملة بشكل صحيح
            if not self.signals or len(self.signals) == 0:
                raise ValueError("❌ فشل تحميل أي إشارات من ملف .env")
            
            # حساب إجمالي الإشارات
            total_signals = sum(len(signal_list) for signal_list in self.signals.values() if signal_list)
            if total_signals == 0:
                raise ValueError("❌ لا توجد إشارات محددة في ملف .env")
            
            self.config['signals'] = self.signals
            logger.info(f"✅ تم تحميل {total_signals} إشارة من {len(self.signals)} فئة")

            self.setup_keywords_enhanced()
            self.validate_configuration()
            
            logger.info("✅ تم تحميل إعدادات النظام بنجاح بدون قيم افتراضية")

        except Exception as e:
            self._handle_error("❌ فشل إعداد التكوين", e)
            raise

    def _load_all_signals_enhanced(self) -> Dict[str, List[str]]:
        """🎯 تحميل جميع الإشارات مع فحص وتحسين"""
        try:
            signal_categories = {
                'trend': 'TREND_SIGNALS',
                'trend_confirm': 'TREND_CONFIRM_SIGNALS',
                'entry_bullish': 'ENTRY_SIGNALS_BULLISH',
                'entry_bearish': 'ENTRY_SIGNALS_BEARISH',
                'exit': 'EXIT_SIGNALS',
                'general': 'GENERAL_SIGNALS',
                'entry_bullish1': 'ENTRY_SIGNALS_BULLISH1',
                'entry_bearish1': 'ENTRY_SIGNALS_BEARISH1',
                'group3_bullish': 'ENTRY_SIGNALS_GROUP3_BULLISH',
                'group3_bearish': 'ENTRY_SIGNALS_GROUP3_BEARISH',
                'group4_bullish': 'ENTRY_SIGNALS_GROUP4_BULLISH',
                'group4_bearish': 'ENTRY_SIGNALS_GROUP4_BEARISH',
                'group5_bullish': 'ENTRY_SIGNALS_GROUP5_BULLISH',
                'group5_bearish': 'ENTRY_SIGNALS_GROUP5_BEARISH'
            }
            
            loaded_signals = {}
            total_loaded = 0
            
            for category, env_key in signal_categories.items():
                try:
                    signals = self._load_signal_list_enhanced(env_key)
                    loaded_signals[category] = signals
                    total_loaded += len(signals)
                    
                    if len(signals) > 0:
                        logger.debug(f"   ✅ تم تحميل {len(signals)} إشارة من {env_key}")
                    else:
                        logger.debug(f"   ⚠️ لا توجد إشارات في {env_key}")
                        
                except Exception as e:
                    self._handle_error(f"❌ خطأ في تحميل {env_key}", e)
                    loaded_signals[category] = []  # تعيين قائمة فارغة بدلاً من التوقف
            
            logger.info(f"📊 إجمالي الإشارات المحملة: {total_loaded} إشارة")
            return loaded_signals
            
        except Exception as e:
            self._handle_error("❌ خطأ في تحميل جميع الإشارات", e)
            # 🔧 FIXED: إرجاع قاموس فارغ بدلاً من رفع استثناء
            return {cat: [] for cat in signal_categories.keys()}

    def _load_signal_list_enhanced(self, env_key: str) -> List[str]:
        """تحميل قائمة الإشارات من البيئة مع فحص وتحسين"""
        try:
            signal_str = self._get_env_str(env_key, "")
            if not signal_str:
                logger.warning(f"⚠️ القيمة فارغة لـ {env_key}")
                return []
            
            signals = []
            for s in signal_str.split(','):
                s_clean = s.strip()
                if s_clean:
                    signals.append(s_clean)
            
            return signals
        except Exception as e:
            self._handle_error(f"❌ خطأ في تحميل {env_key}", e)
            return []

    def _apply_logging_config_enhanced(self) -> None:
        """🎯 تطبيق إعدادات التسجيل المحسنة مع إصلاح ظهور السجلات"""
        try:
            log_level = self.config['LOG_LEVEL'].upper()
            debug_mode = self.config['DEBUG']
            
            print(f"🔧 تطبيق إعدادات التسجيل: DEBUG={debug_mode}, LOG_LEVEL={log_level}")
            
            # تحديد مستوى التسجيل الفعلي
            level_mapping = {
                'ERROR': logging.ERROR,
                'WARNING': logging.WARNING,
                'INFO': logging.INFO,
                'DEBUG': logging.DEBUG
            }
            level = level_mapping.get(log_level, logging.INFO)
            
            # 🔧 FIXED: إعادة تهيئة نظام التسجيل بشكل كامل
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            
            # إنشاء معالج كونسول جديد
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            
            # تنسيق مفصل للسجلات
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            
            # إعادة التهيئة مع الإعدادات الجديدة
            logging.basicConfig(
                level=level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[console_handler],
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
                'notifications.notification_manager',
                'maintenance.cleanup_manager',
                'werkzeug'
            ]
            
            for logger_name in loggers_to_configure:
                logger_instance = logging.getLogger(logger_name)
                logger_instance.setLevel(level)
                # إزالة أي معالجات قديمة
                for handler in logger_instance.handlers[:]:
                    logger_instance.removeHandler(handler)
                # إضافة المعالج الجديد
                logger_instance.addHandler(console_handler)
                logger_instance.propagate = False
            
            # 🛠️ معالجة جميع لوغرات urllib3 ذات الصلة
            urllib3_related_loggers = [
                'urllib3',
                'urllib3.connectionpool',
                'urllib3.response',
                'urllib3.connection'
            ]
            
            for urllib_logger in urllib3_related_loggers:
                logger_instance = logging.getLogger(urllib_logger)
                logger_instance.setLevel(logging.WARNING)
                for handler in logger_instance.handlers[:]:
                    logger_instance.removeHandler(handler)
            
            # 🛠️ إعداد تسجيل Flask و Werkzeug
            flask_logger = logging.getLogger('werkzeug')
            flask_logger.setLevel(logging.INFO)
            
            # 🛠️ إخفاء رسائل المكتبات الخارجية إذا كان DEBUG=false
            if not debug_mode:
                external_loggers = ['schedule', 'urllib3', 'requests']
                for ext_logger in external_loggers:
                    logging.getLogger(ext_logger).setLevel(logging.WARNING)
            else:
                # في وضع التصحيح، نسمح ببعض رسائل المكتبات
                logging.getLogger('werkzeug').setLevel(logging.INFO)
            
            # 🎯 رسالة تأكيد على مستوى INFO حتى نراها دائماً
            logging.info(f"✅ تم تطبيق إعدادات التسجيل: DEBUG={debug_mode}, LOG_LEVEL={log_level}")
            print(f"🎯 إعدادات التسجيل النهائية: DEBUG={debug_mode}, LOG_LEVEL={log_level}")
            
        except Exception as e:
            print(f"❌ خطأ في تطبيق إعدادات التسجيل: {e}")
            logging.getLogger().setLevel(logging.DEBUG)

    def _validate_trading_mode_strict(self, mode_value: Optional[str]) -> str:
        """التحقق الصارم من نمط التداول - محدث للتجميعات"""
        if mode_value is None:
            raise ValueError("❌ TRADING_MODE غير محدد - مطلوب قيمة في ملف .env")
        
        if not mode_value.strip():
            raise ValueError("❌ TRADING_MODE فارغ - مطلوب قيمة في ملف .env")
            
        mode_clean = mode_value.strip().upper()
        valid_groups = ['GROUP1', 'GROUP2', 'GROUP3', 'GROUP4', 'GROUP5']
        groups_in_mode = mode_clean.split('_')
        
        # 🎯 التحقق من عدم وجود تكرار في التجميع
        if len(groups_in_mode) != len(set(groups_in_mode)):
            raise ValueError(f"❌ يوجد تكرار في المجموعات: {mode_clean}")
        
        for group in groups_in_mode:
            if group not in valid_groups:
                raise ValueError(f"❌ مجموعة غير صالحة في TRADING_MODE: {group}")
        
        if not groups_in_mode:
            raise ValueError("❌ TRADING_MODE يجب أن يحتوي على مجموعة واحدة على الأقل")
        
        logger.info(f"✅ تم تحميل نمط التداول: {mode_clean}")
        return mode_clean

    def _validate_trading_modes_strict(self) -> None:
        """🚫 التحقق النهائي من أنماط التداول - محدث للتجميعات"""
        required_modes = ['TRADING_MODE']
        
        for mode_key in required_modes:
            mode_value = self.config.get(mode_key)
            if mode_value is None:
                raise ValueError(f"❌ {mode_key} مطلوب في ملف .env")
    
        # 🛠️ الإصلاح: النمط الأساسي يجب أن يكون مفعلاً دائماً
        # لا يوجد TRADING_MODE_ENABLED لأنه مفعول دائمًا
        
        # التحقق من الأنماط الإضافية إذا كانت مفعلة
        if self.config.get('TRADING_MODE1_ENABLED') and self.config.get('TRADING_MODE1') is None:
            raise ValueError("❌ TRADING_MODE1 مطلوب في ملف .env لأن TRADING_MODE1_ENABLED=true")
            
        if self.config.get('TRADING_MODE2_ENABLED') and self.config.get('TRADING_MODE2') is None:
            raise ValueError("❌ TRADING_MODE2 مطلوب في ملف .env لأن TRADING_MODE2_ENABLED=true")

        # 🎯 التحقق من أن المجموعات المستخدمة في التجميعات مفعلة
        self._validate_trading_mode_combinations()

    def _validate_trading_mode_combinations(self) -> None:
        """🎯 التحقق من أن جميع المجموعات في التجميعات مفعلة"""
        trading_modes_to_check = [
            self.config['TRADING_MODE'],
            self.config['TRADING_MODE1'],
            self.config['TRADING_MODE2']
        ]
        
        for mode in trading_modes_to_check:
            if mode:
                groups = mode.split('_')
                for group in groups:
                    enabled_key = f"{group}_ENABLED"
                    if not self.config.get(enabled_key, False):
                        logger.warning(f"⚠️ المجموعة {group} مستخدمة في {mode} ولكنها معطلة")

    def setup_keywords_enhanced(self) -> None:
        """إعداد الكلمات المفتاحية مع تحسينات"""
        try:
            keyword_categories = {
                'bullish': 'BULLISH_KEYWORDS',
                'bearish': 'BEARISH_KEYWORDS',
                'trend': 'TREND_KEYWORDS',
                'trend_confirm': 'TREND_CONFIRM_KEYWORDS',
                'exit': 'EXIT_KEYWORDS',
                'group3': 'GROUP3_KEYWORDS',
                'group4': 'GROUP4_KEYWORDS',
                'group5': 'GROUP5_KEYWORDS'
            }
            
            self.keywords = {}
            for category, env_key in keyword_categories.items():
                try:
                    kw_str = self._get_env_str(env_key, "")
                    if kw_str:
                        keywords = [kw.strip() for kw in kw_str.split(',') if kw.strip()]
                        self.keywords[category] = keywords
                        logger.debug(f"   ✅ تم تحميل {len(keywords)} كلمة مفتاحية لـ {category}")
                    else:
                        self.keywords[category] = []
                        logger.warning(f"⚠️ لا توجد كلمات مفتاحية لـ {env_key}")
                except Exception as e:
                    self._handle_error(f"❌ خطأ في تحميل الكلمات المفتاحية لـ {env_key}", e)
                    self.keywords[category] = []
            
            logger.info(f"✅ تم تحميل {len(self.keywords)} فئات من الكلمات المفتاحية")
            
        except Exception as e:
            self._handle_error("❌ خطأ في تحميل الكلمات المفتاحية", e)
            self.keywords = {}

    def validate_configuration(self) -> None:
        """التحقق من صحة التكوين"""
        logging.info("\n🔍 Validating configuration...")
        
        errors, warnings = ConfigValidator.validate_config(self.config)
        
        # 🛠️ الإصلاح: التحقق من أنماط التداول المحددة
        trading_modes_to_check = [
            self.config['TRADING_MODE'],
            self.config['TRADING_MODE1'], 
            self.config['TRADING_MODE2']
        ]
        
        for mode in trading_modes_to_check:
            if not self._validate_trading_mode_internal(mode):
                errors.append(f"❌ نمط تداول غير معروف: {mode}")
        
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

    def _validate_trading_mode_internal(self, mode: str) -> bool:
        """التحقق الداخلي من نمط التداول"""
        if not mode:
            return False
            
        valid_groups = ['GROUP1', 'GROUP2', 'GROUP3', 'GROUP4', 'GROUP5']
        groups_in_mode = mode.split('_')
        
        for group in groups_in_mode:
            if group not in valid_groups:
                return False
                
        return len(groups_in_mode) > 0

    def display_config(self) -> None:
        """عرض الإعدادات المحملة للتحقق - محدث للتجميعات"""
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
        
        # 🆕 عرض إعدادات المجموعتين الجديدتين
        logging.info(f"      • Group4 Enabled: {'✅ YES' if self.config['GROUP4_ENABLED'] else '❌ NO'}")
        if self.config['GROUP4_ENABLED']:
            logging.info(f"      • Required Group4: {self.config['REQUIRED_CONFIRMATIONS_GROUP4']}")
        logging.info(f"      • Group5 Enabled: {'✅ YES' if self.config['GROUP5_ENABLED'] else '❌ NO'}")
        if self.config['GROUP5_ENABLED']:
            logging.info(f"      • Required Group5: {self.config['REQUIRED_CONFIRMATIONS_GROUP5']}")
        
        # 🎯 عرض إعدادات نظام الاتجاه
        logging.info("   🎯 نظام تجميع إشارات الاتجاه:")
        logging.info(f"      • عتبة تغيير الاتجاه: {self.config['TREND_CHANGE_THRESHOLD']} إشارات")
        
        # 🆕 عرض إعداد تخزين الإشارات المخالفة
        logging.info("   🔄 تخزين الإشارات المخالفة: " + ("✅ مفعل" if self.config['STORE_CONTRARIAN_SIGNALS'] else "❌ معطل"))
        
        # 🆕 عرض إشارات المجموعات الجديدة
        if self.config['GROUP3_ENABLED']:
            logging.info("   🟢 Group3 Signals:")
            logging.info(f"      • Bullish: {len(self.signals['group3_bullish'])} signals")
            logging.info(f"      • Bearish: {len(self.signals['group3_bearish'])} signals")
        
        if self.config['GROUP4_ENABLED']:
            logging.info("   🟠 Group4 Signals:")
            logging.info(f"      • Bullish: {len(self.signals['group4_bullish'])} signals")
            logging.info(f"      • Bearish: {len(self.signals['group4_bearish'])} signals")
            
        if self.config['GROUP5_ENABLED']:
            logging.info("   🟣 Group5 Signals:")
            logging.info(f"      • Bullish: {len(self.signals['group5_bullish'])} signals")
            logging.info(f"      • Bearish: {len(self.signals['group5_bearish'])} signals")
        
        # 🆕 عرض إعدادات انتهاء صلاحية الإشارات
        logging.info("   ⏰ Signal Expiration Settings:")
        logging.info(f"      • Signal TTL: {self.config['SIGNAL_TTL_MINUTES']} minutes")
        
        logging.info("   📊 Message Controls:")
        logging.info("      • Trend Messages: " + ("✅ ON" if self.config['SEND_TREND_MESSAGES'] else "❌ OFF"))
        logging.info("      • Entry Messages: " + ("✅ ON" if self.config['SEND_ENTRY_MESSAGES'] else "❌ OFF"))
        logging.info("      • Exit Messages: " + ("✅ ON" if self.config['SEND_EXIT_MESSAGES'] else "❌ OFF"))
        logging.info(f"   🌐 Server Port: {self.port}")

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()

    def clear_error_log(self) -> None:
        """مسح سجل الأخطاء"""
        self._error_log.clear()

    def get_system_info(self) -> Dict:
        """الحصول على معلومات النظام"""
        total_signals = sum(len(signal_list) for signal_list in self.signals.values() if signal_list)
        
        return {
            'port': self.port,
            'debug': self.config['DEBUG'],
            'log_level': self.config['LOG_LEVEL'],
            'telegram_enabled': self.config['TELEGRAM_ENABLED'],
            'external_server_enabled': self.config['EXTERNAL_SERVER_ENABLED'],
            'trading_mode': self.config['TRADING_MODE'],
            'total_signals': total_signals,
            'signal_categories': len(self.signals),
            'keywords_categories': len(self.keywords),
            'error_count': len(self._error_log)
        }

    def reload_config(self) -> bool:
        """إعادة تحميل الإعدادات"""
        try:
            logger.info("🔄 إعادة تحميل الإعدادات...")
            
            # حفظ الإعدادات القديمة
            old_config = self.config.copy()
            old_signals = self.signals.copy()
            
            # إعادة التهيئة
            self.config = {}
            self.signals = {}
            self.keywords = {}
            self._error_log = []
            
            self.setup_config()
            
            logger.info("✅ تم إعادة تحميل الإعدادات بنجاح")
            return True
            
        except Exception as e:
            # استعادة الإعدادات القديمة في حالة الفشل
            self.config = old_config
            self.signals = old_signals
            self._handle_error("❌ فشل إعادة تحميل الإعدادات", e)
            return False