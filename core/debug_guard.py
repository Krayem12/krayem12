# core/debug_guard.py
"""
🔒 DebugGuard - حماية واجهات التصحيح
======================================
يمنع الوصول غير المصرح به لواجهات التصحيح في بيئة الإنتاج
"""

import os
import logging
import hashlib
import hmac
from functools import wraps
from typing import Optional, Callable, Set, Dict, Any
from flask import request, jsonify

logger = logging.getLogger(__name__)

class DebugGuard:
    """حارس واجهات التصحيح"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # قراءة الإعدادات
        self.debug_enabled = self._parse_bool(config.get('DEBUG_ENABLED', 'false'))
        self.debug_api_key = config.get('DEBUG_API_KEY', '').strip()
        self.allowed_ips = self._parse_allowed_ips(config.get('DEBUG_ALLOWED_IPS', ''))
        self.log_debug_access = self._parse_bool(config.get('LOG_DEBUG_ACCESS', 'true'))
        self.debug_header_name = config.get('DEBUG_HEADER_NAME', 'X-Debug-Key')
        
        # إعدادات متقدمة
        self.rate_limit_enabled = self._parse_bool(config.get('DEBUG_RATE_LIMIT_ENABLED', 'true'))
        self.rate_limit_requests = int(config.get('DEBUG_RATE_LIMIT_REQUESTS', 60))
        self.rate_limit_period = int(config.get('DEBUG_RATE_LIMIT_PERIOD', 60))
        
        # تتبع الطلبات (للـ rate limiting)
        self.request_tracker: Dict[str, list] = {}
        
        # تسجيل حالة الحماية
        self._log_init_status()
    
    def _parse_bool(self, value: Any) -> bool:
        """تحويل القيمة إلى boolean"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on', 'y')
        return bool(value)
    
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
        """التحقق من rate limiting"""
        if not self.rate_limit_enabled:
            return True
        
        import time
        current_time = time.time()
        
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
    
    def is_access_allowed(self) -> bool:
        """التحقق من السماح بالوصول"""
        
        # إذا كان التصحيح معطلاً تماماً
        if not self.debug_enabled:
            if self.log_debug_access:
                logger.warning("🚫 محاولة وصول لواجهات تصحيح معطلة")
            return False
        
        client_ip = request.remote_addr or '0.0.0.0'
        
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
            api_key = request.headers.get(self.debug_header_name)
            
            # 2. من Query Parameter (للتجارب السريعة - غير آمن للإنتاج)
            if not api_key and request.args.get('debug_key'):
                logger.warning(f"⚠️ استخدام query parameter للـ API Key من IP: {client_ip}")
                api_key = request.args.get('debug_key')
            
            # 3. من Authorization Header
            if not api_key and request.headers.get('Authorization'):
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    api_key = auth_header[7:]
            
            # 4. من Body (لطلبات POST فقط)
            if not api_key and request.is_json:
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
            logger.info(f"✅ وصول مصرح به للتصحيح من IP: {client_ip}, المسار: {request.path}")
        
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
                    "path": request.path,
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
        """الحصول على حالة التصحيح (لأغراض المراقبة فقط)"""
        client_ip = request.remote_addr if request else None
        
        return {
            "debug_enabled": self.debug_enabled,
            "has_api_key": bool(self.debug_api_key),
            "allowed_ips_count": len(self.allowed_ips),
            "rate_limit_enabled": self.rate_limit_enabled,
            "current_ip": client_ip,
            "is_ip_allowed": client_ip in self.allowed_ips if self.allowed_ips else True,
            "log_debug_access": self.log_debug_access,
            "timestamp": self._get_timestamp()
        }
    
    def cleanup_old_requests(self):
        """تنظيف طلبات rate limiting القديمة"""
        import time
        current_time = time.time()
        cleaned_count = 0
        
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
