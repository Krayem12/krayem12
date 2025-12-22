"""
📅 أدوات الوقت مع التوقيت السعودي
"""

import pytz
from datetime import datetime
from typing import Optional

class SaudiTime:
    """فئة إدارة الوقت بالتوقيت السعودي"""
    
    _timezone = pytz.timezone('Asia/Riyadh')
    
    @classmethod
    def now(cls) -> datetime:
        """الحصول على الوقت الحالي بالتوقيت السعودي"""
        return datetime.now(cls._timezone)
    
    @classmethod
    def isoformat(cls, dt: Optional[datetime] = None) -> str:
        """تنسيق الوقت بتنسيق ISO"""
        if dt is None:
            dt = cls.now()
        return dt.isoformat()
    
    @classmethod
    def format_time(cls, dt: Optional[datetime] = None, format_str: str = '%Y-%m-%d %I:%M:%S %p') -> str:
        """تنسيق الوقت حسب الشكل المطلوب"""
        if dt is None:
            dt = cls.now()
        return dt.strftime(format_str)
    
    @classmethod
    def utc_to_saudi(cls, utc_dt: datetime) -> datetime:
        """تحويل من UTC إلى التوقيت السعودي"""
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(cls._timezone)

# إنشاء نسخة واحدة للاستخدام
saudi_time = SaudiTime()
