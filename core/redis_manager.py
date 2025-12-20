"""
🔒 Redis Manager - مدير اتصالات Redis الآمن
إصدار مصحح مع تشفير TLS، مصادقة قوية، وإدارة اتصالات آمنة
"""

import os
import logging
import time
import json
import ssl
from typing import Dict, Optional, Any, Set, List
from datetime import datetime, timedelta
from functools import wraps
import hashlib

# 🔒 استيراد آمن مع معالجة الأخطاء
try:
    import redis
    from redis import Redis, ConnectionPool, AuthenticationError, ConnectionError
    from redis.retry import Retry
    from redis.backoff import ExponentialBackoff
    REDIS_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ فشل استيراد مكتبة redis: {e}")
    redis = None
    Redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class RedisManager:
    """🔒 مدير Redis محسّن مع تشفير وأمان متقدم"""
    
    # 🔒 ثوابت الأمان
    DEFAULT_TIMEOUT = 10  # ثانية
    SOCKET_TIMEOUT = 30   # ثانية
    MAX_CONNECTIONS = 20
    CONNECTION_RETRIES = 3
    HEALTH_CHECK_INTERVAL = 30  # ثانية
    ENCRYPTION_PREFIX = "enc:"
    SENSITIVE_KEY_PATTERNS = ['password', 'token', 'secret', 'key', 'auth']
    
    def __init__(self, config: Dict):
        """🔒 تهيئة مدير Redis مع التحقق من الأمان"""
        
        # 🔒 التحقق من توفر المكتبة
        if not REDIS_AVAILABLE:
            logger.error("❌ مكتبة redis غير مثبتة - لا يمكن استخدام Redis")
            self.client = None
            self.is_connected = False
            self.encryption_enabled = False
            return
        
        # 🔒 نسخة آمنة من التكوين للتسجيل
        self.config = self._sanitize_config(config.copy())
        
        # 🔒 حالة النظام
        self.is_connected = False
        self.connection_errors = 0
        self.last_connection_attempt = None
        self.health_status = "unknown"
        self.encryption_enabled = False
        
        # 🔒 إعداد التشفير
        self._setup_encryption()
        
        # 🔒 إنشاء تجمع الاتصالات
        self.pool = None
        self.client = None
        
        # 🔒 محاولة الاتصال
        self._connect()
        
        # 🔒 تسجيل ملخص التهيئة
        self._log_init_summary()
    
    def _sanitize_config(self, config: Dict) -> Dict:
        """🔒 تنظيف التكوين من البيانات الحساسة"""
        safe_config = config.copy()
        
        # 🔒 إخفاء البيانات الحساسة للتسجيل
        sensitive_keys = ['password', 'pass', 'secret', 'key', 'token']
        for key in list(safe_config.keys()):
            if any(sensitive in str(key).lower() for sensitive in sensitive_keys):
                safe_config[key] = '***HIDDEN***'
        
        return safe_config
    
    def _setup_encryption(self):
        """🔒 إعداد نظام التشفير للبيانات الحساسة"""
        try:
            encryption_key = os.getenv('REDIS_ENCRYPTION_KEY')
            
            if not encryption_key:
                logger.warning("⚠️ مفتاح تشفير Redis غير موجود - البيانات ستكون نصاً واضحاً")
                self.encryption_enabled = False
                return
            
            # 🔒 استخدام مكتبة cryptography إذا كانت متاحة
            try:
                from cryptography.fernet import Fernet
                
                # 🔒 التحقق من صحة مفتاح Fernet
                if len(encryption_key) == 44:  # طول مفتاح Fernet الصالح
                    self.cipher_suite = Fernet(encryption_key.encode())
                    self.encryption_enabled = True
                    logger.info("✅ تشفير Redis مفعل (Fernet)")
                else:
                    logger.error(f"❌ مفتاح تشفير غير صالح (الطول: {len(encryption_key)}، المطلوب: 44)")
                    self.encryption_enabled = False
                    
            except ImportError:
                logger.warning("⚠️ مكتبة cryptography غير مثبتة - استخدام تشفير أساسي")
                self.encryption_enabled = False
                self.cipher_suite = None
                
        except Exception as e:
            logger.error(f"❌ فشل إعداد التشفير: {e}")
            self.encryption_enabled = False
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """🔒 إنشاء سياق SSL آمن"""
        try:
            context = ssl.create_default_context()
            
            # 🔒 إعدادات SSL قوية
            context.check_hostname = self.config.get('ssl_check_hostname', True)
            context.verify_mode = ssl.CERT_REQUIRED if self.config.get('ssl', True) else ssl.CERT_NONE
            
            # 🔒 تعطيل بروتوكولات قديمة غير آمنة
            try:
                context.minimum_version = ssl.TLSVersion.TLSv1_2
            except AttributeError:
                # دعم لإصدارات Python القديمة
                context.options |= ssl.OP_NO_TLSv1
                context.options |= ssl.OP_NO_TLSv1_1
            
            # 🔒 تعطيل ضغط SSL
            context.options |= getattr(ssl, 'OP_NO_COMPRESSION', 0)
            
            return context
            
        except Exception as e:
            logger.error(f"❌ فشل إنشاء سياق SSL: {e}")
            return None
    
    def _connect(self):
        """🔒 إنشاء اتصال Redis آمن"""
        self.last_connection_attempt = datetime.now()
        
        try:
            # 🔒 الحصول على الإعدادات من التكوين أو البيئة
            redis_host = self.config.get('host') or os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(self.config.get('port') or os.getenv('REDIS_PORT', 6379))
            
            # 🔒 الحصول على كلمة المرور بشكل آمن
            redis_password = None
            if 'password' in self.config:
                redis_password = self.config['password']
            elif os.getenv('REDIS_PASSWORD'):
                redis_password = os.getenv('REDIS_PASSWORD')
            
            redis_db = int(self.config.get('db') or os.getenv('REDIS_DB', 0))
            
            # 🔒 إعدادات SSL
            use_ssl = self.config.get('ssl', True)
            if 'ssl' not in self.config:
                # 🔒 استخدام SSL افتراضياً إذا لم يتم التحديد
                use_ssl = os.getenv('REDIS_SSL', 'true').lower() == 'true'
            
            ssl_context = self._create_ssl_context() if use_ssl else None
            
            # 🔒 إعداد إعادة المحاولة
            retry = Retry(
                ExponentialBackoff(),
                self.CONNECTION_RETRIES
            ) if hasattr(Retry, '__init__') else None
            
            # 🔒 إنشاء تجمع الاتصالات
            connection_params = {
                'host': redis_host,
                'port': redis_port,
                'password': redis_password,
                'db': redis_db,
                'decode_responses': True,
                'socket_timeout': self.SOCKET_TIMEOUT,
                'socket_connect_timeout': self.DEFAULT_TIMEOUT,
                'max_connections': self.MAX_CONNECTIONS,
                'health_check_interval': self.HEALTH_CHECK_INTERVAL,
                'retry_on_timeout': True,
            }
            
            # 🔒 إضافة إعدادات SSL إذا كانت مفعلة
            if use_ssl and ssl_context:
                connection_params.update({
                    'ssl': True,
                    'ssl_cert_reqs': 'required',
                    'ssl_ca_certs': None,
                    'ssl_context': ssl_context,
                })
            
            # 🔒 إضافة إعادة المحاولة إذا كانت متاحة
            if retry:
                connection_params['retry'] = retry
            
            self.pool = ConnectionPool(**connection_params)
            
            # 🔒 إنشاء العميل
            self.client = Redis(connection_pool=self.pool)
            
            # 🔒 اختبار الاتصال
            self._test_connection()
            
            self.is_connected = True
            self.connection_errors = 0
            self.health_status = "connected"
            
            logger.info(
                f"✅ اتصال Redis آمن ناجح: {redis_host}:{redis_port} "
                f"(SSL: {'✅' if use_ssl else '❌'}, "
                f"التشفير: {'✅' if self.encryption_enabled else '❌'})"
            )
            
        except AuthenticationError as e:
            logger.error(f"❌ مصادقة Redis فشلت - تحقق من كلمة المرور")
            self._log_security_event("authentication_failed", str(e))
            self.is_connected = False
            self.health_status = "authentication_failed"
            raise
            
        except ConnectionError as e:
            logger.error(f"❌ فشل اتصال Redis: {e}")
            self.connection_errors += 1
            self.is_connected = False
            self.health_status = "connection_failed"
            raise
            
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في اتصال Redis: {e}")
            self.connection_errors += 1
            self.is_connected = False
            self.health_status = "initialization_failed"
            raise
    
    def _test_connection(self):
        """🔒 اختبار اتصال Redis مع فحص الأداء"""
        try:
            start_time = time.time()
            
            # 🔒 اختبار Ping
            if not self.client.ping():
                raise ConnectionError("فشل استجابة PING من Redis")
            
            # 🔒 اختبار القراءة/الكتابة
            test_key = f"_connection_test_{int(time.time())}"
            test_value = f"test_{hashlib.md5(test_key.encode()).hexdigest()[:8]}"
            
            # 🔒 الكتابة
            if not self.client.setex(test_key, 10, test_value):
                raise ConnectionError("فشل الكتابة في Redis")
            
            # 🔒 القراءة
            retrieved = self.client.get(test_key)
            if retrieved != test_value:
                raise ConnectionError("فشل القراءة من Redis")
            
            # 🔒 التنظيف
            self.client.delete(test_key)
            
            latency = (time.time() - start_time) * 1000  # ملي ثانية
            
            logger.debug(f"✅ اختبار اتصال Redis ناجح (زمن الاستجابة: {latency:.2f}ms)")
            
        except Exception as e:
            logger.error(f"❌ فشل اختبار اتصال Redis: {e}")
            raise
    
    def _should_encrypt(self, key: str, value: Any) -> bool:
        """🔒 تحديد إذا ما كانت البيانات تحتاج تشفير"""
        if not self.encryption_enabled:
            return False
        
        # 🔒 التحقق من المفاتيح الحساسة
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in self.SENSITIVE_KEY_PATTERNS):
            return True
        
        # 🔒 التحقق من القيم الحساسة
        if isinstance(value, str):
            value_lower = value.lower()
            sensitive_patterns = ['pass=', 'token=', 'secret=', 'key=', 'auth=', 'bearer']
            if any(pattern in value_lower for pattern in sensitive_patterns):
                return True
        
        return False
    
    def _encrypt_value(self, value: str) -> str:
        """🔒 تشفير قيمة نصية"""
        if not self.encryption_enabled or not hasattr(self, 'cipher_suite'):
            return value
        
        try:
            encrypted = self.cipher_suite.encrypt(value.encode())
            return self.ENCRYPTION_PREFIX + encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ فشل تشفير القيمة: {e}")
            return value
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """🔒 فك تشفير قيمة"""
        if not self.encryption_enabled or not hasattr(self, 'cipher_suite'):
            return encrypted_value
        
        if not encrypted_value.startswith(self.ENCRYPTION_PREFIX):
            return encrypted_value
        
        try:
            value = encrypted_value[len(self.ENCRYPTION_PREFIX):]
            decrypted = self.cipher_suite.decrypt(value.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ فشل فك تشفير القيمة: {e}")
            return encrypted_value
    
    def is_enabled(self) -> bool:
        """🔒 التحقق من تفعيل Redis واتصاله"""
        if not self.is_connected or not self.client:
            return False
        
        try:
            # 🔒 فحص سريع للاتصال
            return bool(self.client.ping())
        except Exception:
            self.is_connected = False
            return False
    
    def get_client(self):
        """🔒 الحصول على عميل Redis (للاستخدام المتقدم)"""
        if not self.is_connected:
            self._reconnect()
        
        return self.client
    
    def set_trend(self, symbol: str, trend: str, ttl: int = 3600) -> bool:
        """🔒 تعيين اتجاه للرمز مع وقت انتهاء"""
        if not self.is_enabled():
            logger.warning(f"⚠️ Redis غير متصل - تجاهل حفظ اتجاه {symbol}")
            return False
        
        try:
            # 🔒 تطبيع المدخلات
            safe_symbol = str(symbol).upper().strip()[:20]
            safe_trend = str(trend).upper().strip()[:50]
            
            if not safe_symbol or not safe_trend:
                logger.error(f"❌ بيانات اتجاه غير صالحة: {symbol} -> {trend}")
                return False
            
            # 🔒 تعيين الاتجاه مع وقت انتهاء
            trend_key = f"trend:{safe_symbol}"
            set_result = self.client.setex(trend_key, ttl, safe_trend)
            
            if not set_result:
                logger.error(f"❌ فشل حفظ الاتجاه في Redis: {safe_symbol}")
                return False
            
            # 🔒 إضافة الرمز إلى مجموعة الرموز مع وقت انتهاء
            self.client.sadd("trend:symbols", safe_symbol)
            self.client.expire("trend:symbols", ttl)
            
            # 🔒 تعيين وقت التحديث مع وقت انتهاء
            update_key = f"trend:{safe_symbol}:updated_at"
            current_time = datetime.now().isoformat()
            self.client.setex(update_key, ttl, current_time)
            
            logger.debug(f"💾 حفظ اتجاه في Redis: {safe_symbol} -> {safe_trend} (TTL: {ttl}s)")
            
            # 🔒 تسجيل أمني
            self._log_security_event("trend_saved", safe_symbol, {
                "trend": safe_trend,
                "ttl": ttl
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الاتجاه لـ {symbol}: {e}")
            self._handle_operation_error("set_trend", e)
            return False
    
    def get_trend(self, symbol: str) -> Optional[str]:
        """🔒 الحصول على اتجاه الرمز"""
        if not self.is_enabled():
            logger.debug(f"ℹ️ Redis غير متصل - لا يمكن جلب اتجاه {symbol}")
            return None
        
        try:
            safe_symbol = str(symbol).upper().strip()[:20]
            
            if not safe_symbol:
                logger.warning(f"⚠️ رمز غير صالح: {symbol}")
                return None
            
            trend_key = f"trend:{safe_symbol}"
            trend = self.client.get(trend_key)
            
            if trend:
                return str(trend).upper()
            
            return None
            
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة الاتجاه لـ {symbol}: {e}")
            self._handle_operation_error("get_trend", e)
            return None
    
    def get_all_trends(self) -> Dict[str, str]:
        """🔒 الحصول على جميع الاتجاهات"""
        trends = {}
        
        if not self.is_enabled():
            logger.debug("ℹ️ Redis غير متصل - لا يمكن جلب جميع الاتجاهات")
            return trends
        
        try:
            # 🔒 الحصول على جميع الرموز
            symbols = self.client.smembers("trend:symbols") or set()
            
            if not symbols:
                return trends
            
            # 🔒 استخدام pipeline لتحسين الأداء
            with self.client.pipeline() as pipe:
                for symbol in symbols:
                    safe_symbol = str(symbol).strip()
                    if safe_symbol:
                        pipe.get(f"trend:{safe_symbol}")
                
                results = pipe.execute()
            
            # 🔒 معالجة النتائج
            symbol_list = list(symbols)
            for i, result in enumerate(results):
                if i < len(symbol_list) and result:
                    safe_symbol = str(symbol_list[i]).strip()
                    if safe_symbol:
                        trends[safe_symbol] = str(result).upper()
            
            logger.debug(f"📊 جلب {len(trends)} اتجاه من Redis")
            return trends
            
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة جميع الاتجاهات: {e}")
            self._handle_operation_error("get_all_trends", e)
            return {}
    
    def set_raw(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """🔒 تعيين قيمة نصية مباشرة"""
        if not self.is_enabled():
            return False
        
        try:
            # 🔒 تطبيع المفتاح والقيمة
            safe_key = str(key).strip()[:100]
            safe_value = str(value).strip()[:10000]  # 🔒 تحديد حجم القيمة
            
            if not safe_key:
                logger.warning("⚠️ مفتاح Redis غير صالح")
                return False
            
            # 🔒 تحديد إذا كانت القيمة تحتاج تشفير
            if self._should_encrypt(safe_key, safe_value):
                safe_value = self._encrypt_value(safe_value)
            
            if ex:
                result = self.client.setex(safe_key, ex, safe_value)
            else:
                result = self.client.set(safe_key, safe_value)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"❌ خطأ في تعيين القيمة للمفتاح {key}: {e}")
            self._handle_operation_error("set_raw", e)
            return False
    
    def _get_current_time(self) -> str:
        """🔒 الحصول على الوقت الحالي بتنسيق ISO"""
        return datetime.now().isoformat()
    
    def _reconnect(self, max_attempts: int = 3):
        """🔒 إعادة الاتصال بـ Redis"""
        if self.is_connected:
            return
        
        logger.info(f"🔄 محاولة إعادة الاتصال بـ Redis ({self.connection_errors} أخطاء سابقة)")
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"  ↪ المحاولة {attempt}/{max_attempts}")
                
                # 🔒 إغلاق الاتصال القديم
                if self.pool:
                    try:
                        self.pool.disconnect()
                    except:
                        pass
                
                # 🔒 إعادة الاتصال
                self._connect()
                
                if self.is_connected:
                    logger.info("✅ إعادة الاتصال بـ Redis ناجحة")
                    return
                
            except Exception as e:
                logger.error(f"❌ فشل إعادة الاتصال (المحاولة {attempt}): {e}")
                
                # 🔒 الانتظار قبل المحاولة التالية
                if attempt < max_attempts:
                    wait_time = 2 ** attempt  # تراجع أسي
                    time.sleep(min(wait_time, 10))  # 🔒 حد أقصى 10 ثواني
        
        logger.error(f"❌ فشل جميع محاولات إعادة الاتصال ({max_attempts} محاولات)")
        self.is_connected = False
        self.health_status = "disconnected"
    
    def _handle_operation_error(self, operation: str, error: Exception):
        """🔒 معالجة أخطاء العمليات"""
        self.connection_errors += 1
        
        error_type = type(error).__name__
        error_msg = str(error)
        
        # 🔒 إعادة الاتصال إذا كان الخطأ متعلقاً بالاتصال
        if error_type in ['ConnectionError', 'TimeoutError', 'ConnectionRefusedError']:
            logger.warning(f"⚠️ خطأ اتصال في {operation}، محاولة إعادة الاتصال...")
            self._reconnect()
        
        # 🔒 تسجيل أمني للأخطاء الحرجة
        if any(word in error_msg.lower() for word in ['password', 'auth', 'permission']):
            self._log_security_event("sensitive_operation_error", operation, {
                "error_type": error_type,
                "hint": "تحتوي الرسالة على كلمات حساسة"
            })
        
        logger.error(f"❌ خطأ في {operation}: {error_type}: {error_msg}")
    
    def _log_security_event(self, event_type: str, details: Any, extra: dict = None):
        """🔒 تسجيل حدث أمني (للمراقبة الداخلية)"""
        try:
            event = {
                "time": self._get_current_time(),
                "type": event_type,
                "details": str(details)[:500],
                "source": "redis_manager"
            }
            
            if extra:
                event["extra"] = {k: v for k, v in extra.items() if not any(
                    sensitive in str(k).lower() for sensitive in self.SENSITIVE_KEY_PATTERNS
                )}
            
            # 🔒 يمكن إضافة إرسال إلى نظام مراقبة هنا
            logger.debug(f"🔒 حدث أمني Redis: {event_type} - {details}")
            
        except Exception as e:
            logger.error(f"❌ فشل تسجيل الحدث الأمني: {e}")
    
    def _log_init_summary(self):
        """🔒 تسجيل ملخص التهيئة"""
        summary = {
            "connected": self.is_connected,
            "encryption": self.encryption_enabled,
            "health_status": self.health_status,
            "connection_errors": self.connection_errors,
            "redis_available": REDIS_AVAILABLE
        }
        
        logger.info(f"📊 ملخص تهيئة RedisManager: {json.dumps(summary, ensure_ascii=False)}")
    
    def health_check(self) -> Dict[str, Any]:
        """🔒 فحص صحة اتصال Redis"""
        if not self.is_enabled():
            return {
                "status": "disconnected",
                "timestamp": self._get_current_time(),
                "errors": self.connection_errors,
                "message": "Redis غير متصل أو غير مفعل"
            }
        
        try:
            start_time = time.time()
            
            # 🔒 اختبار بسيط
            test_key = f"_health_check_{int(time.time())}"
            test_value = "health_check"
            
            # 🔒 اختبار الكتابة
            if not self.client.setex(test_key, 10, test_value):
                raise ConnectionError("فشل الكتابة في اختبار الصحة")
            
            # 🔒 اختبار القراءة
            retrieved = self.client.get(test_key)
            if retrieved != test_value:
                raise ConnectionError("فشل القراءة في اختبار الصحة")
            
            # 🔒 التنظيف
            self.client.delete(test_key)
            
            latency = (time.time() - start_time) * 1000  # ملي ثانية
            
            health_data = {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "connection_errors": self.connection_errors,
                "encryption_enabled": self.encryption_enabled,
                "timestamp": self._get_current_time()
            }
            
            self.health_status = "healthy"
            return health_data
            
        except Exception as e:
            logger.error(f"❌ فشل فحص صحة Redis: {e}")
            self.health_status = "unhealthy"
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_errors": self.connection_errors,
                "timestamp": self._get_current_time()
            }
    
    def close(self):
        """🔒 إغلاق اتصالات Redis بشكل آمن"""
        try:
            if self.pool:
                self.pool.disconnect()
                logger.info("✅ تم إغلاق اتصالات Redis")
            
            self.is_connected = False
            self.client = None
            self.pool = None
            self.health_status = "closed"
            
        except Exception as e:
            logger.error(f"❌ خطأ في إغلاق Redis: {e}")
    
    def __del__(self):
        """🔒 تنظيف الموارد عند الحذف"""
        try:
            self.close()
        except:
            pass
