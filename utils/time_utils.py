import pytz
from datetime import datetime

class SaudiTime:
    """أدوات الوقت بالتوقيت السعودي"""
    
    def __init__(self):
        self.timezone = pytz.timezone('Asia/Riyadh')
    
    def now(self):
        """الحصول على التوقيت السعودي الحالي"""
        return datetime.now(self.timezone)
    
    def from_utc(self, utc_dt):
        """تحويل من UTC إلى التوقيت السعودي"""
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(self.timezone)
    
    def format_time(self, dt=None):
        """تنسيق الوقت بشكل جميل"""
        if dt is None:
            dt = self.now()
        return dt.strftime('%Y-%m-%d %I:%M:%S %p')
    
    def format_time_24h(self, dt=None):
        """تنسيق الوقت بنظام 24 ساعة"""
        if dt is None:
            dt = self.now()
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    def get_timezone_info(self):
        """الحصول على معلومات النطاق الزمني"""
        current_time = self.now()
        return {
            'timezone': 'Asia/Riyadh',
            'offset': current_time.strftime('%z'),
            'name': current_time.strftime('%Z'),
            'current_time': self.format_time(),
            'current_time_24h': self.format_time_24h()
        }

# إنشاء نسخة عامة للاستخدام
saudi_time = SaudiTime()