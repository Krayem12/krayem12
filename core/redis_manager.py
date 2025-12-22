# core/redis_manager.py
import os
import logging
from typing import Dict, Optional

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

class RedisManager:
    """مدير Redis محسّن للاتجاهات مع تحويل آمن للأنواع"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = None
        
        if redis is None:
            logger.warning("⚠️ مكتبة redis غير مثبتة - تعطيل Redis")
            return
            
        try:
            # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
            # ✅ تحويل الأنواع الآمن للـ Redis
            # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
            
            redis_host = self._safe_get_str(config, 'REDIS_HOST', 'localhost')
            redis_port = self._safe_get_int(config, 'REDIS_PORT', 6379)
            redis_password = self._safe_get_str(config, 'REDIS_PASSWORD', None)
            redis_db = self._safe_get_int(config, 'REDIS_DB', 0)
            
            logger.info(f"🔧 تهيئة Redis: {redis_host}:{redis_port} (DB: {redis_db})")
            
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True,  # ✅ هذا يحل مشكلة Bytes
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            
            # اختبار الاتصال
            self.client.ping()
            logger.info(f"✅ تم الاتصال بـ Redis بنجاح: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بـ Redis: {e}")
            self.client = None
    
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    # ✅ دوال التحويل الآمن
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    
    def _safe_get_str(self, config: Dict, key: str, default: str = '') -> str:
        """الحصول على قيمة نصية آمنة"""
        try:
            value = config.get(key, default)
            if isinstance(value, str):
                return value.strip()
            elif value is not None:
                return str(value).strip()
            else:
                return default
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى str: {e}")
            return default
    
    def _safe_get_int(self, config: Dict, key: str, default: int = 0) -> int:
        """الحصول على قيمة عددية آمنة"""
        try:
            value = config.get(key, default)
            if isinstance(value, int):
                return value
            elif isinstance(value, str):
                # إزالة أي أحرف غير رقمية
                cleaned = ''.join(filter(str.isdigit, value))
                if cleaned:
                    return int(cleaned)
                else:
                    return default
            elif isinstance(value, bool):
                return 1 if value else 0
            elif isinstance(value, float):
                return int(value)
            else:
                return default
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى int: {e}")
            return default
    
    def is_enabled(self) -> bool:
        """التحقق من تفعيل Redis"""
        return self.client is not None
    
    def get_client(self):
        """الحصول على عميل Redis"""
        return self.client
    
    def set_trend(self, symbol: str, trend: str, ttl_hours: int = 24) -> bool:
        """تعيين اتجاه للرمز مع TTL"""
        try:
            if not self.client:
                return False
                
            key = f"trend:{symbol.upper()}"
            
            # ✅ استخدام setex مع TTL
            success = self.client.setex(key, ttl_hours * 3600, trend.upper())
            
            if success:
                # إضافة الرمز إلى مجموعة الرموز
                self.client.sadd("trend:symbols", symbol.upper())
                
                # تعيين وقت التحديث
                self.client.setex(
                    f"trend:{symbol.upper()}:updated_at",
                    ttl_hours * 3600,
                    self._get_current_time()
                )
                
                logger.debug(f"💾 حفظ الاتجاه في Redis: {symbol} -> {trend} (TTL: {ttl_hours}h)")
                return True
            else:
                logger.error(f"❌ فشل حفظ الاتجاه لـ {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الاتجاه لـ {symbol}: {e}")
            return False
    
    def get_trend(self, symbol: str) -> Optional[str]:
        """✅ المحدث: الحصول على اتجاه الرمز مع decode"""
        try:
            if not self.client:
                return None
                
            key = f"trend:{symbol.upper()}"
            trend = self.client.get(key)
            
            # ✅ decode_responses=True يجعل القيمة نصية تلقائياً
            return trend if trend else None
            
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
            
            logger.debug(f"📊 تم تحميل {len(trends)} اتجاه من Redis")
            
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة جميع الاتجاهات: {e}")
            
        return trends
    
    def _get_current_time(self) -> str:
        """الحصول على الوقت الحالي بتنسيق مناسب"""
        from datetime import datetime
        return datetime.now().isoformat()
