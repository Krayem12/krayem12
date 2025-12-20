import os
import logging
from typing import Dict, Optional
from datetime import datetime

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

class RedisManager:
    """مدير Redis محسّن للاتجاهات"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = None
        
        if redis is None:
            logger.warning("⚠️ مكتبة redis غير مثبتة - تعطيل Redis")
            return
            
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_db = int(os.getenv('REDIS_DB', 0))
            
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # اختبار الاتصال
            self.client.ping()
            logger.info(f"✅ تم الاتصال بـ Redis بنجاح: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بـ Redis: {e}")
            self.client = None
    
    def is_enabled(self) -> bool:
        """التحقق من تفعيل Redis"""
        return self.client is not None
    
    def get_client(self):
        """الحصول على عميل Redis"""
        return self.client
    
    def set_trend(self, symbol: str, trend: str) -> bool:
        """تعيين اتجاه للرمز"""
        try:
            if not self.client:
                return False
                
            key = f"trend:{symbol.upper()}"
            self.client.set(key, trend.upper())
            
            # إضافة الرمز إلى مجموعة الرموز
            self.client.sadd("trend:symbols", symbol.upper())
            
            # تعيين وقت التحديث
            self.client.set(f"trend:{symbol.upper()}:updated_at", self._get_current_time())
            
            logger.debug(f"💾 حفظ الاتجاه في Redis: {symbol} -> {trend}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الاتجاه لـ {symbol}: {e}")
            return False
    
    def get_trend(self, symbol: str) -> Optional[str]:
        """الحصول على اتجاه الرمز"""
        try:
            if not self.client:
                return None
                
            key = f"trend:{symbol.upper()}"
            trend = self.client.get(key)
            return trend
            
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة الاتجاه لـ {symbol}: {e}")
            return None
    
    def get_all_trends(self) -> Dict[str, str]:
        """الحصول على جميع الاتجاهات"""
        trends = {}
        try:
            if not self.client:
                return trends
                
            symbols = self.client.smembers("trend:symbols") or set()
            
            for symbol in symbols:
                trend = self.client.get(f"trend:{symbol}")
                if trend:
                    trends[symbol] = trend
                    
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة جميع الاتجاهات: {e}")
            
        return trends
    
    def _get_current_time(self) -> str:
        """الحصول على الوقت الحالي بتنسيق مناسب"""
        return datetime.now().isoformat()
