import re
import hashlib
from datetime import datetime

class Helpers:
    """فئة الأدوات المساعدة"""
    
    @staticmethod
    def generate_trade_id():
        """إنشاء معرف فريد للصفقة"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_signal_hash(signal_text):
        """إنشاء hash للإشارة لمنع التكرار"""
        return hashlib.md5(signal_text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def format_timestamp(dt=None):
        """تنسيق الطابع الزمني"""
        if dt is None:
            dt = datetime.now()
        return dt.strftime('%Y-%m-%d %I:%M:%S %p')
    
    @staticmethod
    def safe_int_convert(value, default=0):
        """تحويل آمن لرقم صحيح"""
        try:
            if value is None:
                return default
            cleaned_value = str(value).strip()
            if not cleaned_value:
                return default
            return int(cleaned_value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def validate_symbol(symbol):
        """التحقق من صحة الرمز"""
        if not symbol or symbol == 'UNKNOWN':
            return False
        # يمكن إضافة المزيد من الشروط
        return bool(re.match(r'^[A-Z0-9]+$', symbol))
    
    @staticmethod
    def calculate_timeout(group_type, config):
        """حساب وقت انتهاء المجموعة"""
        if group_type == 'group1':
            return config.get('CONFIRMATION_TIMEOUT', 1200)
        elif group_type in ['group2', 'group3']:
            return config.get('DUAL_CONFIRMATION_TIMEOUT', 1800)
        else:
            return 1800  # Default