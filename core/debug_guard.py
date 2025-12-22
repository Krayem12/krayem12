# core/debug_guard.py
"""
🔒 DebugGuard - حماية واجهات التصحيح
======================================
"""

import os
import logging
import hashlib
import hmac
from functools import wraps
from typing import Optional, Callable, Set, Dict, Any
from flask import request, jsonify, has_request_context
import threading

logger = logging.getLogger(__name__)

class DebugGuard:
    """حارس واجهات التصحيح مع إدارة آمنة للـ Request Context"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # 🔥 استخدام دوال التحويل الآمن
        self.debug_enabled = self._safe_get_bool(config, 'DEBUG_ENABLED', False)
        self.debug_api_key = self._safe_get_str(config, 'DEBUG_API_KEY', '').strip()
        self.allowed_ips = self._parse_allowed_ips(self._safe_get_str(config, 'DEBUG_ALLOWED_IPS', ''))
        self.log_debug_access = self._safe_get_bool(config, 'LOG_DEBUG_ACCESS', True)
        self.debug_header_name = self._safe_get_str(config, 'DEBUG_HEADER_NAME', 'X-Debug-Key')
        
        # إعدادات متقدمة مع تحويل آمن
        self.rate_limit_enabled = self._safe_get_bool(config, 'DEBUG_RATE_LIMIT_ENABLED', True)
        self.rate_limit_requests = self._safe_get_int(config, 'DEBUG_RATE_LIMIT_REQUESTS', 60)
        self.rate_limit_period = self._safe_get_int(config, 'DEBUG_RATE_LIMIT_PERIOD', 60)
        
        # تتبع الطلبات مع Lock للـ Thread Safety
        self.request_tracker: Dict[str, list] = {}
        self.tracker_lock = threading.Lock()
        
        # تسجيل حالة الحماية
        self._log_init_status()
    
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    # ✅ دوال التحويل الآمن
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    
    def _safe_get_bool(self, config: dict, key: str, default: bool = False) -> bool:
        """الحصول على قيمة منطقية آمنة"""
        try:
            value = config.get(key, default)
            
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                val_lower = value.lower().strip()
                if val_lower in ('true', '1', 'yes', 'on', 'y', 't'):
                    return True
                elif val_lower in ('false', '0', 'no', 'off', 'n', 'f'):
                    return False
                else:
                    return default
            elif isinstance(value, (int, float)):
                return bool(value)
            else:
                return default
                
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى bool: {e}, استخدام الافتراضي: {default}")
            return default
    
    def _safe_get_int(self, config: dict, key: str, default: int = 0) -> int:
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
            logger.warning(f"⚠️ فشل تحويل {key} إلى int: {e}, استخدام الافتراضي: {default}")
            return default
    
    def _safe_get_str(self, config: dict, key: str, default: str = '') -> str:
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
            logger.warning(f"⚠️ فشل تحويل {key} إلى str: {e}, استخدام الافتراضي: '{default}'")
            return default
    
    def _parse_allowed_ips(self, ip_string: str) -> Set[str]:
        """تحليل قائمة IPs المسموح بها"""
        if not ip_string:
            return set()
        
        ips = set()
        for ip in ip_string.split(','):
            ip = ip.strip()
            if ip:
                ips.add(ip)
        
        return ips
    
    def _log_init_status(self):
        """تسجيل حالة التهيئة"""
        if self.debug_enabled:
            if self.debug_api_key:
                masked_key = self.debug_api_key[:4] + "..." + self.debug_api_key[-4:] if len(self.debug_api_key) > 8 else "***"
                logger.warning(f"🔐 واجهات التصحيح مفعلة مع API Key: {masked_key}")
            else:
                logger.error("⚠️ DEBUG_ENABLED=True لكن DEBUG_API_KEY فارغ! - جميع الطلبات ستُرفض")
            
            if self.allowed_ips:
                logger.info(f"📡 IPs المسموح بها: {', '.join(self.allowed_ips)}")
            else:
                logger.warning("🌍 لا توجد قيود على IPs - جميع IPs مسموح بها")
        else:
            logger.info("🔒 واجهات التصحيح معطلة تماماً")
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """🔒 التحقق من rate limiting مع Thread Safety"""
        if not self.rate_limit_enabled:
            return True
        
        import time
        current_time = time.time()
        
        with self.tracker_lock:
            # تنظيف الطلبات القديمة
            if client_ip in self.request_tracker:
                self.request_tracker[client_ip] = [
                    req_time for req_time in self.request_tracker[client_ip]
                    if current_time - req_time < self.rate_limit_period
                ]
            
            # التحقق من الحد
            request_count = len(self.request_tracker.get(client_ip, []))
            if request_count >= self.rate_limit_requests:
                logger.warning(f"🚫 تجاوز معدل الطلبات للـ IP: {client_ip} ({request_count}/{self.rate_limit_requests})")
                return False
            
            # تسجيل الطلب
            if client_ip not in self.request_tracker:
                self.request_tracker[client_ip] = []
            self.request_tracker[client_ip].append(current_time)
            
            # الحفاظ على حجم الذاكرة
            if len(self.request_tracker[client_ip]) > self.rate_limit_requests * 2:
                self.request_tracker[client_ip] = self.request_tracker[client_ip][-self.rate_limit_requests:]
            
            return True
    
    def _safe_compare(self, a: str, b: str) -> bool:
        """مقارنة آمنة للسلسلات (لمنع timing attacks)"""
        try:
            # استخدام hmac لمقارنة آمنة زمنياً
            return hmac.compare_digest(
                hashlib.sha256(a.encode()).hexdigest(),
                hashlib.sha256(b.encode()).hexdigest()
            )
        except Exception:
            # fallback آمن نسبياً
            if len(a) != len(b):
                return False
            result = 0
            for x, y in zip(a, b):
                result |= ord(x) ^ ord(y)
            return result == 0
    
    def _get_client_ip(self) -> str:
        """🔧 الحصول على IP العميل مع دعم Proxy"""
        if not has_request_context():
            return "SYSTEM"
        
        try:
            # دعم Proxy (Cloud Run, Render, etc.)
            if request.headers.get('X-Forwarded-For'):
                # أخذ أول IP في القائمة
                forwarded_ips = request.headers.get('X-Forwarded-For', '').split(',')
                client_ip = forwarded_ips[0].strip()
                if client_ip:
                    return client_ip
            
            # استخدام remote_addr كحل بديل
            return request.remote_addr or '0.0.0.0'
            
        except Exception as e:
            logger.warning(f"⚠️ خطأ في الحصول على IP العميل: {e}")
            return '0.0.0.0'
    
    def is_access_allowed(self) -> bool:
        """✅ المحدث: التحقق من السماح بالوصول مع Request Context"""
        
        # إذا كان التصحيح معطلاً تماماً
        if not self.debug_enabled:
            if self.log_debug_access:
                logger.warning("🚫 محاولة وصول لواجهات تصحيح معطلة")
            return False
        
        client_ip = self._get_client_ip()
        
        # التحقق من IP إذا كان محدداً
        if self.allowed_ips and client_ip not in self.allowed_ips:
            if self.log_debug_access:
                logger.warning(f"🚫 IP غير مسموح: {client_ip} (المسموح: {self.allowed_ips})")
            return False
        
        # التحقق من rate limiting
        if not self._check_rate_limit(client_ip):
            return False
        
        # التحقق من API Key
        if self.debug_api_key:
            api_key = None
            
            # 1. من Header (المفضل)
            if has_request_context():
                api_key = request.headers.get(self.debug_header_name)
            
            # 2. من Query Parameter (للتجارب السريعة)
            if not api_key and has_request_context() and request.args.get('debug_key'):
                logger.warning(f"⚠️ استخدام query parameter للـ API Key من IP: {client_ip}")
                api_key = request.args.get('debug_key')
            
            # 3. من Authorization Header
            if not api_key and has_request_context() and request.headers.get('Authorization'):
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    api_key = auth_header[7:]
            
            # 4. من Body (لطلبات POST فقط)
            if not api_key and has_request_context() and request.is_json:
                data = request.get_json(silent=True) or {}
                api_key = data.get('debug_key')
            
            # التحقق من المطابقة
            if not api_key:
                if self.log_debug_access:
                    logger.warning(f"🚫 طلب بدون API Key من IP: {client_ip}")
                return False
            
            if not self._safe_compare(api_key, self.debug_api_key):
                if self.log_debug_access:
                    logger.warning(f"🚫 API Key غير صحيح من IP: {client_ip}")
                return False
        
        # تسجيل الوصول الناجح
        if self.log_debug_access:
            logger.info(f"✅ وصول مصرح به للتصحيح من IP: {client_ip}")
        
        return True
    
    def require_debug_auth(self, func: Callable):
        """
        Decorator لحماية واجهات التصحيح
        """
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not self.is_access_allowed():
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Debug APIs are disabled or require authentication",
                    "timestamp": self._get_timestamp(),
                    "status": 403
                }), 403
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"💥 خطأ في معالجة طلب التصحيح: {e}")
                return jsonify({
                    "error": "Internal Server Error",
                    "message": str(e),
                    "timestamp": self._get_timestamp()
                }), 500
        
        return decorated_function
    
    def _get_timestamp(self) -> str:
        """الحصول على الطابع الزمني"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_debug_status(self) -> dict:
        """✅ المحدث: الحصول على حالة التصحيح مع Request Context"""
        try:
            client_ip = self._get_client_ip()
            
            return {
                "debug_enabled": self.debug_enabled,
                "has_api_key": bool(self.debug_api_key),
                "allowed_ips_count": len(self.allowed_ips),
                "rate_limit_enabled": self.rate_limit_enabled,
                "current_ip": client_ip,
                "is_ip_allowed": client_ip in self.allowed_ips if self.allowed_ips else True,
                "log_debug_access": self.log_debug_access,
                "has_request_context": has_request_context(),
                "timestamp": self._get_timestamp()
            }
        except Exception as e:
            logger.error(f"💥 خطأ في الحصول على حالة التصحيح: {e}")
            return {
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    def cleanup_old_requests(self):
        """تنظيف طلبات rate limiting القديمة"""
        import time
        current_time = time.time()
        cleaned_count = 0
        
        with self.tracker_lock:
            for ip in list(self.request_tracker.keys()):
                initial_count = len(self.request_tracker[ip])
                self.request_tracker[ip] = [
                    req_time for req_time in self.request_tracker[ip]
                    if current_time - req_time < self.rate_limit_period * 2
                ]
                
                cleaned = initial_count - len(self.request_tracker[ip])
                cleaned_count += cleaned
                
                # حذف IPs بدون طلبات
                if not self.request_tracker[ip]:
                    del self.request_tracker[ip]
        
        if cleaned_count > 0:
            logger.debug(f"🧹 تم تنظيف {cleaned_count} طلب قديم من tracker")
        
        return cleaned_count
