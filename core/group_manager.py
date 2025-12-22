# core/group_manager.py
import logging
from datetime import datetime, timedelta
import hashlib
from typing import Dict, List, Optional, Tuple
import threading
from collections import defaultdict, deque
from functools import lru_cache

# ✅ استيراد موحد
from utils.time_utils import saudi_time
from .group_mapper import GroupMapper

logger = logging.getLogger(__name__)

class GroupManager:
    """🎯 نظام إدارة المجموعات بالتوقيت السعودي"""

    def __init__(self, config, trade_manager):
        self.config = config
        self.trade_manager = trade_manager
        
        # ✅ إضافة GroupMapper
        self.group_mapper = GroupMapper()
        
        # تخزين الإشارات المؤقتة
        self.pending_signals = defaultdict(lambda: defaultdict(lambda: deque(maxlen=200)))
        
        # إحصائيات النظام
        self.error_log = deque(maxlen=1000)
        self.mode_performance = {}
        
        # قفل لإدارة التزامن
        self.signal_lock = threading.RLock()
        
        # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
        # ✅ المحدث: استخدام الدوال الجديدة لتحويل الأنواع
        # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
        
        # 🎯 FIXED: استخدام إعدادات منع التكرار مع تحويل أنواع آمن
        self.duplicate_block_time = self._get_int('DUPLICATE_SIGNAL_BLOCK_TIME', 15)
        self.duplicate_cleanup_interval = self._get_int('DUPLICATE_CLEANUP_INTERVAL', 30)
        
        # 🔥 NEW: جميع العوامل الزمنية مع تحويل أنواع آمن
        self.cleanup_factor = self._get_float('CLEANUP_FACTOR', 1.5)
        self.signal_retention_factor = self._get_float('SIGNAL_RETENTION_FACTOR', 2.0)
        self.trade_cooldown_factor = self._get_float('TRADE_COOLDOWN_FACTOR', 1.2)
        self.signal_ttl_minutes = self._get_int('SIGNAL_TTL_MINUTES', 10)
        self.signal_cleanup_threshold = self._get_int('SIGNAL_CLEANUP_THRESHOLD_SECONDS', 60)
        
        # تحسين الأداء
        self.signal_hashes = {}
        self.last_hash_cleanup = saudi_time.now()
        
        # 🎯 NEW: تتبع الإشارات المستخدمة في الصفقات المفتوحة
        self.used_signals_for_trades = defaultdict(set)
        
        # 🎯 FIXED: إضافة متغيرات المراقبة
        self.memory_usage_log = deque(maxlen=100)
        self.last_cleanup_time = saudi_time.now()
        
        logger.info(f"🎯 نظام المجموعات المصحح جاهز - جميع الإعدادات محولة بشكل آمن 🇸🇦")
        logger.info(f"⏰ إعدادات التوقيت: Block={self.duplicate_block_time}s, Cleanup={self.duplicate_cleanup_interval}s")
        logger.info(f"🔧 العوامل: Cleanup={self.cleanup_factor}, Retention={self.signal_retention_factor}")
        
        # ✅ تسجيل إحصائيات المجموعات
        self._log_group_statistics()
        
        # ✅ التحقق من صحة التحويلات
        self._validate_type_conversions()

    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    # ✅ دوال التحويل الآمن الجديدة
    # 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥 🔥
    
    def _get_int(self, key: str, default: int = 0) -> int:
        """الحصول على قيمة عددية آمنة"""
        try:
            if hasattr(self.config, 'get_int'):
                return self.config.get_int(key, default)
            else:
                # fallback للتوافق
                value = self.config.get(key, default)
                if isinstance(value, int):
                    return value
                elif isinstance(value, str):
                    try:
                        return int(value)
                    except ValueError:
                        return default
                elif isinstance(value, bool):
                    return 1 if value else 0
                else:
                    return default
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى int: {e}, استخدام الافتراضي: {default}")
            return default
    
    def _get_float(self, key: str, default: float = 0.0) -> float:
        """الحصول على قيمة عشرية آمنة"""
        try:
            if hasattr(self.config, 'get_float'):
                return self.config.get_float(key, default)
            else:
                # fallback للتوافق
                value = self.config.get(key, default)
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    try:
                        return float(value)
                    except ValueError:
                        return default
                else:
                    return default
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى float: {e}, استخدام الافتراضي: {default}")
            return default
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """الحصول على قيمة منطقية آمنة"""
        try:
            if hasattr(self.config, 'get_bool'):
                return self.config.get_bool(key, default)
            else:
                # fallback للتوافق
                value = self.config.get(key, default)
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
    
    def _get_str(self, key: str, default: str = '') -> str:
        """الحصول على قيمة نصية آمنة"""
        try:
            if hasattr(self.config, 'get_str'):
                return self.config.get_str(key, default)
            else:
                value = self.config.get(key, default)
                if isinstance(value, str):
                    return value.strip()
                else:
                    return str(value).strip() if value is not None else default
        except Exception as e:
            logger.warning(f"⚠️ فشل تحويل {key} إلى str: {e}, استخدام الافتراضي: '{default}'")
            return default
    
    def _validate_type_conversions(self):
        """التحقق من صحة تحويلات الأنواع"""
        logger.info("🔍 التحقق من تحويلات الأنواع...")
        
        test_keys = [
            ('DUPLICATE_SIGNAL_BLOCK_TIME', 'int', self.duplicate_block_time),
            ('CLEANUP_FACTOR', 'float', self.cleanup_factor),
            ('GROUP1_ENABLED', 'bool', self._get_bool('GROUP1_ENABLED')),
            ('SIGNAL_TTL_MINUTES', 'int', self.signal_ttl_minutes),
        ]
        
        for key, expected_type, value in test_keys:
            actual_type = type(value).__name__
            logger.info(f"   📋 {key}: {actual_type} (متوقع: {expected_type}) = {value}")
            
            # التحقق من النوع
            if expected_type == 'int' and not isinstance(value, int):
                logger.error(f"❌ خطأ في تحويل النوع: {key} ليس int!")
            elif expected_type == 'float' and not isinstance(value, (int, float)):
                logger.error(f"❌ خطأ في تحويل النوع: {key} ليس float!")
            elif expected_type == 'bool' and not isinstance(value, bool):
                logger.error(f"❌ خطأ في تحويل النوع: {key} ليس bool!")
    
    # ... (بقية الكود كما هو مع استبدال config.get بـ _get_* في الأماكن الحرجة)
    # سأستبدل فقط الأماكن الحرجة في هذا المثال
    
    def _is_group_enabled(self, group_type: str) -> bool:
        """✅ المحدث: التحقق من تفعيل المجموعة مع تحويل آمن"""
        try:
            # استخدام GroupMapper للتحقق
            return self.group_mapper.is_group_enabled(group_type, self.config)
            
        except Exception as e:
            self._handle_error("💥 خطأ في التحقق من تفعيل المجموعة", e)
            return False
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """🔒 التحقق من معدل الطلبات مع تحويل آمن"""
        try:
            # 🔥 استخدام الدوال الجديدة لتحويل الأنواع
            rate_limit_requests = self._get_int('RATE_LIMIT_REQUESTS', 60)
            rate_limit_period = self._get_int('RATE_LIMIT_PERIOD', 60)
            
            current_time = saudi_time.now()
            
            if client_ip in self.request_counts:
                self.request_counts[client_ip] = [
                    req_time for req_time in self.request_counts[client_ip]
                    if (current_time - req_time).total_seconds() < rate_limit_period
                ]
            
            if client_ip not in self.request_counts:
                self.request_counts[client_ip] = []
            
            if len(self.request_counts[client_ip]) >= rate_limit_requests:
                logger.warning(f"🚫 تجاوز معدل الطلبات للعميل: {client_ip}")
                return False
            
            self.request_counts[client_ip].append(current_time)
            return True
            
        except Exception as e:
            self._handle_error("💥 خطأ في rate limiting", e)
            return True
    
    def _cleanup_old_hashes(self):
        """🎯 FIXED: تنظيف التجزئات القديمة مع تحويل آمن"""
        try:
            current_time = saudi_time.now()
            with self.signal_lock:
            
                if (current_time - self.last_hash_cleanup).total_seconds() > self.duplicate_cleanup_interval:
                    initial_count = len(self.signal_hashes)
                
                    # 🔥 التعديل: استخدام عامل التنظيف مع تحويل آمن
                    max_age = self.duplicate_block_time * self.cleanup_factor
                
                    expired_hashes = [
                        hash_key for hash_key, timestamp in self.signal_hashes.items()
                        if (current_time - timestamp).total_seconds() > max_age
                    ]
                
                    for hash_key in expired_hashes:
                        del self.signal_hashes[hash_key]
                
                    cleaned_count = len(expired_hashes)
                    if cleaned_count > 0:
                        logger.info(f"🧹 تم تنظيف {cleaned_count} تجزئة قديمة من أصل {initial_count} - التوقيت السعودي 🇸🇦")
                
                    self.last_hash_cleanup = current_time
                
        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف التجزئات", e)
    
    def _can_open_trade(self, symbol: str, mode_key: str) -> bool:
        """✅ المحدث: التحقق من إمكانية فتح صفقة مع تحويل آمن"""
        try:
            # 🔧 FIXED: التحقق من وجود trade_manager
            if not hasattr(self, 'trade_manager') or self.trade_manager is None:
                logger.error("❌ trade_manager غير متوفر للتحقق من إمكانية فتح الصفقة")
                return False
            
            # 🔧 FIXED: دعم نسخ TradeManager المختلفة
            get_count = getattr(self.trade_manager, 'get_active_trades_count', None)
            active_trades = getattr(self.trade_manager, 'active_trades', {}) or {}

            if callable(get_count):
                current_count = int(get_count(symbol))
                total_trades = int(get_count())
            else:
                # ✅ fallback
                current_count = sum(1 for t in active_trades.values() if t.get('symbol') == symbol)
                total_trades = len(active_trades)

            # 🔥 استخدام الدوال الجديدة لتحويل الأنواع
            max_per_symbol = self._get_int('MAX_TRADES_PER_SYMBOL', 20)
            if current_count >= max_per_symbol:
                logger.warning(f"🚫 وصل الحد الأقصى للصفقات للرمز {symbol}: {current_count}/{max_per_symbol}")
                return False

            max_open_trades = self._get_int('MAX_OPEN_TRADES', 20)
            if total_trades >= max_open_trades:
                logger.warning(f"🚫 وصل الحد الأقصى الإجمالي للصفقات: {total_trades}/{max_open_trades}")
                return False
            
            # 🔥 استخدام الدوال الجديدة لتحويل الأنواع
            mode_limits = {
                'TRADING_MODE': self._get_int('MAX_TRADES_MODE_MAIN', 20),
                'TRADING_MODE1': self._get_int('MAX_TRADES_MODE1', 5),
                'TRADING_MODE2': self._get_int('MAX_TRADES_MODE2', 5)
            }
            
            current_mode_trades = self.trade_manager.count_trades_by_mode(symbol, mode_key)
            mode_limit = mode_limits.get(mode_key, 2)
            
            if current_mode_trades >= mode_limit:
                logger.warning(f"🚫 وصل الحد الأقصى للنمط {mode_key}: {current_mode_trades}/{mode_limit}")
                return False
            
            return True
            
        except Exception as e:
            self._handle_error(f"💥 خطأ في التحقق من إمكانية فتح الصفقة", e)
            return False
