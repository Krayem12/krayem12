# config/config_manager.py
"""
🎯 مدير الإعدادات مع تحويل أنواع دقيق وآمن
===========================================
"""

import os
import logging
from typing import Any, Dict, Optional, Union
from dotenv import load_dotenv
import json

logger = logging.getLogger(__name__)

class ConfigManager:
    """مدير الإعدادات مع تحويل أنواع آمن"""
    
    def __init__(self):
        self.config = {}
        self.signals = {}
        self.keywords = {}
        self.port = 10000
        
        self._load_config()
        self._load_signals()
        self._load_keywords()
    
    def _load_config(self):
        """تحميل الإعدادات من .env مع تحويل أنواع آمن"""
        load_dotenv()
        
        # قراءة جميع متغيرات البيئة
        for key, value in os.environ.items():
            if key and value is not None:
                self.config[key] = value
        
        # تعيين البورت
        self.port = self.get_int('PORT', 10000)
        
        logger.info(f"✅ تم تحميل {len(self.config)} إعداد من .env")
    
    def _load_signals(self):
        """تحميل الإشارات من الإعدادات"""
        self.signals = self._parse_list_config('signals')
        logger.info(f"📡 تم تحميل {len(self.signals)} فئة إشارات")
    
    def _load_keywords(self):
        """تحميل الكلمات المفتاحية"""
        self.keywords = self._parse_list_config('keywords')
        logger.info(f"🔑 تم تحميل {len(self.keywords)} فئة كلمات مفتاحية")
    
    def _parse_list_config(self, prefix: str) -> Dict:
        """تحليل الإعدادات كقوائم"""
        result = {}
        for key in list(self.config.keys()):
            if key.lower().startswith(prefix.lower()):
                value = self.config[key]
                if value:
                    # تحليل القيم كمصفوفة (مفصولة بفواصل)
                    items = [item.strip() for item in value.split(',') if item.strip()]
                    result[key] = items
        return result
    
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    # ✅ الدوال الجديدة لتحويل الأنواع الآمن
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        الحصول على قيمة عدد صحيح بشكل آمن
        
        Args:
            key: مفتاح الإعداد
            default: القيمة الافتراضية
        
        Returns:
            قيمة عددية صحيحة
        """
        try:
            value = self.config.get(key)
            if value is None:
                return default
            
            # التحويل الآمن للعدد الصحيح
            if isinstance(value, int):
                return value
            elif isinstance(value, str):
                # إزالة أي مسافات وحروف غير رقمية
                cleaned = ''.join(filter(str.isdigit, value))
                if cleaned:
                    return int(cleaned)
                else:
                    # محاولة التحويل من منطقي
                    if value.lower() in ('true', 'yes', 'on'):
                        return 1
                    elif value.lower() in ('false', 'no', 'off'):
                        return 0
            elif isinstance(value, bool):
                return 1 if value else 0
            elif isinstance(value, float):
                return int(value)
            
            return default
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى int: {e}, استخدام القيمة الافتراضية {default}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        الحصول على قيمة عشرية بشكل آمن
        
        Args:
            key: مفتاح الإعداد
            default: القيمة الافتراضية
        
        Returns:
            قيمة عشرية
        """
        try:
            value = self.config.get(key)
            if value is None:
                return default
            
            # التحويل الآمن للعدد العشري
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # إزالة أي أحرف غير رقمية باستثناء النقطة
                cleaned = ''.join(c for c in value if c.isdigit() or c == '.' or c == '-')
                if cleaned and cleaned.replace('.', '', 1).replace('-', '', 1).isdigit():
                    return float(cleaned)
            
            return default
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى float: {e}, استخدام القيمة الافتراضية {default}")
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        الحصول على قيمة منطقية بشكل آمن
        
        Args:
            key: مفتاح الإعداد
            default: القيمة الافتراضية
        
        Returns:
            قيمة منطقية (True/False)
        """
        try:
            value = self.config.get(key)
            if value is None:
                return default
            
            # التحويل الآمن للمنطقي
            if isinstance(value, bool):
                return value
            elif isinstance(value, (int, float)):
                return bool(value)
            elif isinstance(value, str):
                val_lower = value.lower().strip()
                
                # قيم True
                if val_lower in ('true', '1', 'yes', 'on', 'y', 't', 'active', 'enabled'):
                    return True
                # قيم False
                elif val_lower in ('false', '0', 'no', 'off', 'n', 'f', 'inactive', 'disabled'):
                    return False
                # القيم الرقمية
                elif val_lower.isdigit():
                    return int(val_lower) != 0
                # القيم العشرية
                else:
                    try:
                        return float(val_lower) != 0.0
                    except ValueError:
                        pass
            
            return default
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى bool: {e}, استخدام القيمة الافتراضية {default}")
            return default
    
    def get_str(self, key: str, default: str = '') -> str:
        """
        الحصول على قيمة نصية بشكل آمن
        
        Args:
            key: مفتاح الإعداد
            default: القيمة الافتراضية
        
        Returns:
            قيمة نصية
        """
        try:
            value = self.config.get(key)
            if value is None:
                return default
            
            # التحويل إلى نص
            if isinstance(value, str):
                return value.strip()
            else:
                return str(value).strip()
                
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى str: {e}, استخدام القيمة الافتراضية '{default}'")
            return default
    
    def get_list(self, key: str, default: list = None, separator: str = ',') -> list:
        """
        الحصول على قائمة بشكل آمن
        
        Args:
            key: مفتاح الإعداد
            default: القيمة الافتراضية
            separator: فاصل العناصر
        
        Returns:
            قائمة من العناصر
        """
        if default is None:
            default = []
        
        try:
            value = self.config.get(key)
            if value is None:
                return default
            
            if isinstance(value, list):
                return value
            elif isinstance(value, str):
                # تقسيم النص إلى قائمة
                items = [item.strip() for item in value.split(separator) if item.strip()]
                return items
            else:
                # محاولة التحويل إلى قائمة
                return [str(value)]
                
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى list: {e}, استخدام القيمة الافتراضية")
            return default
    
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    # ✅ دوال التوافق للكود الحالي
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        دالة التوافق - استرجاع القيمة كما هي
        
        Note: يُفضّل استخدام الدوال المخصصة (get_int, get_bool, etc.)
        """
        return self.config.get(key, default)
    
    def display_config(self):
        """عرض الإعدادات المهمة"""
        logger.info("=" * 50)
        logger.info("🎯 إعدادات النظام")
        logger.info("=" * 50)
        
        important_settings = {
            'PORT': self.port,
            'DEBUG': self.get_bool('DEBUG'),
            'TELEGRAM_ENABLED': self.get_bool('TELEGRAM_ENABLED'),
            'REDIS_HOST': self.get_str('REDIS_HOST'),
            'MAX_OPEN_TRADES': self.get_int('MAX_OPEN_TRADES'),
            'GROUP1_ENABLED': self.get_bool('GROUP1_ENABLED'),
            'GROUP2_ENABLED': self.get_bool('GROUP2_ENABLED'),
            'GROUP3_ENABLED': self.get_bool('GROUP3_ENABLED'),
            'GROUP4_ENABLED': self.get_bool('GROUP4_ENABLED'),
            'GROUP5_ENABLED': self.get_bool('GROUP5_ENABLED'),
            'TRADING_MODE1_ENABLED': self.get_bool('TRADING_MODE1_ENABLED'),
            'TRADING_MODE2_ENABLED': self.get_bool('TRADING_MODE2_ENABLED'),
            'DUPLICATE_SIGNAL_BLOCK_TIME': self.get_int('DUPLICATE_SIGNAL_BLOCK_TIME'),
            'DEBUG_ENABLED': self.get_bool('DEBUG_ENABLED'),
        }
        
        for key, value in important_settings.items():
            logger.info(f"📋 {key}: {value}")
        
        # عرض أنواع الإعدادات
        logger.info("\n🔍 أنواع الإعدادات:")
        for key, value in self.config.items():
            if key in important_settings:
                actual_type = type(value).__name__
                converted_type = type(important_settings[key]).__name__
                logger.info(f"   {key}: {actual_type} → {converted_type}")
        
        logger.info("=" * 50)
