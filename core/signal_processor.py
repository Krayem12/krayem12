"""
🔍 Signal Processor - معالج الإشارات الآمن
إصدار مصحح مع تحقق من المدخلات، تحليل نصي آمن، ومعالجة موثوقة
"""

import re
import hashlib
import logging
import html
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any, Set
from functools import lru_cache
from collections import deque, defaultdict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SignalProcessor:
    """🔍 معالج الإشارات مع أمان متقدم وتخزين مؤقت ذكي"""

    # 🔒 ثوابت الأمان
    MAX_TEXT_LENGTH = 10000
    MAX_CACHE_SIZE = 2000
    MAX_SIGNAL_INDEX_SIZE = 5000
    MAX_ERROR_LOG_SIZE = 1000
    SIGNAL_TIMEOUT_SECONDS = 300
    DUPLICATE_WINDOW_SECONDS = 60
    CONFIDENCE_THRESHOLD = 0.6
    
    # 🔒 قوائم سوداء للأنماط الخطرة
    BLACKLIST_PATTERNS = [
        r'\b(admin|root|system)\b',
        r'\b(password|token|secret|key)\s*=\s*\S+',
        r'<script>',
        r'onerror\s*=',
        r'javascript:',
        r'SELECT.*FROM',
        r'INSERT INTO',
        r'DROP TABLE',
        r'UNION SELECT',
    ]
    
    # 🔒 مصادر موثوقة
    TRUSTED_SOURCES = {
        'trading_bot', 'technical_analysis', 'news_api', 
        'social_api', 'webhook_verified'
    }

    def __init__(self, config: Dict, signals: Dict, keywords: Dict):
        """🔒 تهيئة معالج الإشارات مع التحقق من الأمان"""
        
        # 🔒 التحقق من المدخلات
        if not config or not isinstance(config, dict):
            raise ValueError("❌ التكوين الرئيسي مطلوب ويجب أن يكون قاموساً")
        
        if not signals or not isinstance(signals, dict):
            raise ValueError("❌ إعدادات الإشارات مطلوبة ويجب أن تكون قاموساً")
        
        # 🔒 نسخ عميقة لتجنب التعديل المباشر
        self.config = config.copy()
        self.signals = self._sanitize_signals_dict(signals.copy())
        self.keywords = keywords.copy() if keywords else {}
        
        # 🔒 أقفال للخيوط المتوازية
        self._lock = threading.RLock() if 'threading' in globals() else None
        
        # 🔒 التخزين المؤقت والمراقبة
        self.signal_index = {}
        self._error_log = deque(maxlen=self.MAX_ERROR_LOG_SIZE)
        self.signal_cache = {}
        self.signal_history = deque(maxlen=500)
        self.source_stats = defaultdict(int)
        self.rejected_signals = deque(maxlen=200)
        
        # 🔒 المقاييس
        self.metrics = {
            "signals_processed": 0,
            "signals_accepted": 0,
            "signals_rejected": 0,
            "duplicates_detected": 0,
            "security_blocks": 0,
            "processing_errors": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 🔒 إعداد الأمان
        self._setup_security()
        self.setup_signal_index()
        
        # 🔒 تسجيل التهيئة
        self._log_init_summary()
        
        logger.info("🔍 نظام معالجة الإشارات الآمن مفعل")

    def _sanitize_signals_dict(self, signals_dict: Dict) -> Dict:
        """🔒 تنظيف قاموس الإشارات من البيانات الخطرة"""
        sanitized = {}
        
        try:
            for category, signal_list in signals_dict.items():
                if not isinstance(signal_list, list):
                    logger.warning(f"⚠️ قائمة إشارات غير صالحة للفئة {category}")
                    continue
                
                safe_list = []
                for signal in signal_list:
                    if signal and isinstance(signal, str):
                        safe_signal = self._sanitize_text(signal)
                        if safe_signal:
                            safe_list.append(safe_signal)
                
                if safe_list:
                    sanitized[category] = safe_list
        
        except Exception as e:
            logger.error(f"❌ فشل تنظيف قاموس الإشارات: {e}")
        
        return sanitized

    def _setup_security(self):
        """🔒 إعداد أنظمة الأمان"""
        try:
            # 🔒 تجميع الأنماط المرفوضة
            self.blacklist_regex = re.compile(
                '|'.join(self.BLACKLIST_PATTERNS),
                re.IGNORECASE
            )
            
            # 🔒 إعدادات من التكوين
            self.max_text_length = int(self.config.get(
                'max_signal_length', self.MAX_TEXT_LENGTH
            ))
            
            self.confidence_threshold = float(self.config.get(
                'confidence_threshold', self.CONFIDENCE_THRESHOLD
            ))
            
            # 🔒 التحقق من القيم
            if self.confidence_threshold < 0 or self.confidence_threshold > 1:
                logger.warning(f"⚠️ عتبة الثقة غير صالحة: {self.confidence_threshold}")
                self.confidence_threshold = self.CONFIDENCE_THRESHOLD
            
            logger.debug("✅ إعدادات الأمان جاهزة")
            
        except Exception as e:
            logger.error(f"❌ فشل إعداد الأمان: {e}")
            raise

    def _sanitize_text(self, text: str) -> str:
        """🔒 تنظيف وتعقيم النص ضد الحقن والهجمات"""
        if not text:
            return ""
        
        try:
            # 🔒 التحقق من النوع
            if not isinstance(text, str):
                text = str(text)
            
            # 🔒 تحديد الطول
            if len(text) > self.max_text_length:
                text = text[:self.max_text_length]
                logger.debug(f"ℹ️ النص طويل جداً، تم تقطيعه إلى {self.max_text_length} حرف")
            
            # 🔒 إزالة الأحرف الخطرة
            text = html.escape(text)  # منع حقن HTML
            
            # 🔒 إزالة أنماط مرفوضة
            text = self.blacklist_regex.sub('[REMOVED]', text)
            
            # 🔒 إزالة أحرف التحكم
            text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
            
            # 🔒 إزالة مسافات زائدة
            text = ' '.join(text.split())
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ فشل تعقيم النص: {e}")
            return ""

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None, 
                     context: Dict = None) -> None:
        """🔒 معالجة موحدة وآمنة للأخطاء"""
        try:
            # 🔒 إنشاء رسالة خطأ آمنة
            error_details = str(exception) if exception else ""
            
            # 🔒 إزالة البيانات الحساسة من رسالة الخطأ
            sensitive_patterns = ['password', 'token', 'secret', 'key', 'auth']
            for pattern in sensitive_patterns:
                if pattern in error_details.lower():
                    error_details = error_details.replace(pattern, "***")
            
            full_error = f"{error_msg}: {error_details}" if error_details else error_msg
            
            # 🔒 تسجيل الخطأ
            logger.error(full_error)
            
            # 🔒 تخزين في سجل الأخطاء (بدون بيانات حساسة)
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'details': error_details[:200],
                'context': self._sanitize_context(context) if context else None
            }
            
            self._error_log.append(error_entry)
            self.metrics["processing_errors"] += 1
            
        except Exception as e:
            logger.error(f"❌ فشل معالجة الخطأ: {e}")

    def _sanitize_context(self, context: Dict) -> Dict:
        """🔒 تنظيف سياق الخطأ من البيانات الحساسة"""
        if not context:
            return {}
        
        safe_context = {}
        try:
            for key, value in context.items():
                if isinstance(value, str):
                    # 🔒 إزالة البيانات الحساسة
                    if any(sensitive in key.lower() for sensitive in 
                          ['password', 'token', 'secret', 'key']):
                        safe_context[key] = '***HIDDEN***'
                    else:
                        safe_context[key] = self._sanitize_text(str(value))[:100]
                else:
                    safe_context[key] = str(value)[:100]
        
        except Exception as e:
            logger.error(f"❌ فشل تنظيف السياق: {e}")
        
        return safe_context

    def setup_signal_index(self) -> None:
        """🔒 بناء فهرس الإشارات مع تحسين الأداء والأمان"""
        logger.debug("🔍 بناء فهرس الإشارات الآمن...")
        
        try:
            index_count = 0
            duplicate_count = 0
            
            for category, signal_list in self.signals.items():
                if not signal_list or not isinstance(signal_list, list):
                    logger.warning(f"⚠️ قائمة إشارات فارغة أو غير صالحة للفئة: {category}")
                    continue
                
                for signal in signal_list:
                    if not signal or not isinstance(signal, str):
                        continue
                    
                    # 🔒 تنظيف وتطبيع الإشارة
                    normalized = self._sanitize_text(signal).lower().strip()
                    
                    if not normalized:
                        continue
                    
                    # 🔒 التحقق من التكرار
                    if normalized in self.signal_index:
                        duplicate_count += 1
                        logger.debug(f"⚠️ إشارة مكررة: {normalized}")
                        continue
                    
                    # 🔒 التحقق من الطول المعقول
                    if len(normalized) > 200:
                        logger.warning(f"⚠️ إشارة طويلة جداً، تم تقصيرها: {normalized[:50]}...")
                        normalized = normalized[:200]
                    
                    self.signal_index[normalized] = category
                    index_count += 1
            
            logger.info(f"📋 فهرس الإشارات المبني: {index_count} إشارة فريدة، {duplicate_count} تكرار")
            
            # 🔒 تسجيل إحصاءات الفئات
            category_stats = {}
            for signal, category in self.signal_index.items():
                category_stats[category] = category_stats.get(category, 0) + 1
            
            for category, count in category_stats.items():
                logger.debug(f"   📁 {category}: {count} إشارة")
            
            # 🔒 التحقق من حجم الفهرس
            if len(self.signal_index) > self.MAX_SIGNAL_INDEX_SIZE:
                logger.warning(f"⚠️ فهرس الإشارات كبير جداً: {len(self.signal_index)} إدخالات")
                
        except Exception as e:
            self._handle_error("❌ خطأ في بناء فهرس الإشارات", e)

    def _generate_signal_hash(self, signal_data: Dict) -> str:
        """🔒 إنشاء هاش فريد للإشارة للكشف عن التكرار"""
        try:
            # 🔒 إنشاء سلسلة موحدة للإشارة
            signal_str = json.dumps({
                'symbol': str(signal_data.get('symbol', '')).upper().strip(),
                'type': str(signal_data.get('signal_type', '')).lower().strip(),
                'text_hash': hashlib.sha256(
                    str(signal_data.get('text', '')).encode('utf-8')
                ).hexdigest()[:16],
                'source': str(signal_data.get('source', '')).lower().strip(),
                'timestamp': int(time.time() / 60)  # دقيقة واحدة دقة
            }, sort_keys=True)
            
            # 🔒 إنشاء الهاش
            signal_hash = hashlib.sha256(signal_str.encode('utf-8')).hexdigest()[:32]
            
            return signal_hash
            
        except Exception as e:
            logger.error(f"❌ فشل إنشاء هاش الإشارة: {e}")
            return f"error_hash_{int(time.time())}"

    def _is_duplicate_signal(self, signal_hash: str) -> bool:
        """🔒 التحقق إذا كانت الإشارة مكررة"""
        try:
            current_time = time.time()
            
            # 🔒 تنظيف الإشارات القديمة من التخزين المؤقت
            expired_hashes = [
                h for h, t in self.signal_cache.items()
                if current_time - t > self.DUPLICATE_WINDOW_SECONDS
            ]
            
            for h in expired_hashes:
                self.signal_cache.pop(h, None)
            
            # 🔒 التحقق من التكرار
            if signal_hash in self.signal_cache:
                self.metrics["duplicates_detected"] += 1
                logger.debug(f"⚠️ إشارة مكررة تم اكتشافها: {signal_hash[:16]}...")
                return True
            
            # 🔒 تخزين الإشارة الجديدة
            self.signal_cache[signal_hash] = current_time
            return False
            
        except Exception as e:
            logger.error(f"❌ فشل التحقق من تكرار الإشارة: {e}")
            return False

    def classify_signal(self, signal_data: Dict) -> str:
        """🎯 تصنيف الإشارة مع التحقق الأمني"""
        
        # 🔒 التحقق من المدخلات
        if not signal_data or not isinstance(signal_data, dict):
            logger.warning("❌ بيانات الإشارة غير صالحة للتصنيف")
            return 'unknown'

        signal_type = signal_data.get('signal_type')
        
        if not signal_type or not isinstance(signal_type, str):
            logger.warning("❌ نوع الإشارة فارغ أو غير نصي")
            return 'unknown'
        
        # 🔒 تنظيف النص
        signal_clean = self._sanitize_text(signal_type)
        if not signal_clean:
            logger.warning("❌ نص الإشارة فارغ بعد التنظيف")
            return 'unknown'
            
        signal_lower = signal_clean.lower().strip()
        
        # 🔒 التحقق من وجود هجمات نصية
        if self._contains_malicious_patterns(signal_lower):
            logger.warning(f"⚠️ إشارة تحتوي على أنماط خبيثة: {signal_lower[:50]}...")
            self.metrics["security_blocks"] += 1
            return 'malicious'
        
        logger.debug(f"🔍 تصنيف الإشارة: '{signal_type}' -> '{signal_lower}'")
        
        # 🔒 استخدام التخزين المؤقت الآمن
        classification = self._classify_signal_text(signal_lower)
        
        logger.debug(f"🎯 نتيجة التصنيف: '{signal_type}' -> '{classification}'")
        
        return classification

    def _contains_malicious_patterns(self, text: str) -> bool:
        """🔒 التحقق من وجود أنماط خبيثة في النص"""
        try:
            return bool(self.blacklist_regex.search(text))
        except Exception as e:
            logger.error(f"❌ فشل التحقق من الأنماط الخبيثة: {e}")
            return False

    @lru_cache(maxsize=1000)
    def _classify_signal_text(self, signal_text: str) -> str:
        """🔒 تصنيف نص الإشارة مع التخزين المؤقت وتحسينات"""
        try:
            # 🔒 التحقق الأساسي
            if not signal_text or not isinstance(signal_text, str):
                return 'unknown'
            
            # 🔒 تطبيع النص
            cleaned_signal = signal_text.lower().strip()
            
            if not cleaned_signal:
                return 'unknown'
            
            # 🔒 التحقق من الطول
            if len(cleaned_signal) > 500:
                logger.warning(f"⚠️ نص إشارة طويل جداً: {len(cleaned_signal)} حرف")
                cleaned_signal = cleaned_signal[:500]
            
            logger.debug(f"🔍 تصنيف الإشارة المنظفة: '{cleaned_signal}'")
            
            # 🔒 البحث في الفهرس أولاً للأداء
            if cleaned_signal in self.signal_index:
                category = self.signal_index[cleaned_signal]
                logger.debug(f"   ✅ تم العثور على الإشارة في الفهرس: {cleaned_signal} -> {category}")
                self.metrics["cache_hits"] += 1
                return category

            # 🔒 البحث في القوائم المحددة
            for category, signal_list in self.signals.items():
                if not signal_list:
                    continue
                    
                # 🔒 البحث الدقيق
                normalized_signals = [
                    self._sanitize_text(s).lower().strip() 
                    for s in signal_list if s and isinstance(s, str)
                ]
                
                if cleaned_signal in normalized_signals:
                    # 🔒 تحديث الفهرس للاستخدام المستقبلي
                    self.signal_index[cleaned_signal] = category
                    logger.debug(f"   ✅ تم العثور على الإشارة في القوائم: {cleaned_signal} -> {category}")
                    self.metrics["cache_misses"] += 1
                    return category

            # 🔒 البحث الجزئي للإشارات الطويلة
            for category, signal_list in self.signals.items():
                if not signal_list:
                    continue
                    
                for signal in signal_list:
                    if not signal or not isinstance(signal, str):
                        continue
                    
                    clean_signal = self._sanitize_text(signal).lower().strip()
                    if cleaned_signal in clean_signal:
                        self.signal_index[cleaned_signal] = category
                        logger.debug(f"   ✅ تم العثور على الإشارة بالبحث الجزئي: {cleaned_signal} -> {category}")
                        self.metrics["cache_misses"] += 1
                        return category

            # 🔒 تسجيل الإشارات غير المعروفة
            logger.debug(f"❌ نوع إشارة غير معروف: '{cleaned_signal}'")
            self.metrics["cache_misses"] += 1
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"💥 خطأ في التصنيف: {e}")
            return 'unknown'

    def safe_classify_signal(self, signal_data: Dict) -> str:
        """🔒 تصنيف آمن مع معالجة الأخطاء"""
        try:
            return self.classify_signal(signal_data)
        except Exception as e:
            self._handle_error("💥 خطأ في التصنيف الآمن", e, {'signal_data': signal_data})
            return 'unknown'

    def extract_signal(self, request) -> str:
        """🔒 استخراج الإشارة من الطلب مع التحقق الأمني"""
        if not request:
            logger.warning("❌ طلب فارغ لاستخراج الإشارة")
            return ""
        
        try:
            content_type = (request.headers.get('Content-Type') or '').lower()

            if 'application/json' in content_type:
                # 🔒 التحقق من حجم الطلب
                content_length = request.headers.get('Content-Length')
                if content_length and int(content_length) > self.max_text_length:
                    logger.warning(f"⚠️ حجم طلب JSON كبير جداً: {content_length}")
                    return "REQUEST_TOO_LARGE"
                
                data = request.get_json(silent=True) or {}
                
                # 🔒 تنظيف البيانات
                ticker = self._sanitize_text(str(data.get('ticker') or data.get('symbol') or 'UNKNOWN'))
                signal_type = self._sanitize_text(str(data.get('signal') or data.get('action') or 'UNKNOWN'))
                
                # 🔒 التحقق من القيم الفارغة
                if not ticker or ticker == 'UNKNOWN':
                    ticker = 'UNKNOWN_TICKER'
                
                if not signal_type or signal_type == 'UNKNOWN':
                    signal_type = 'UNKNOWN_SIGNAL'
                
                logger.debug(f"📥 إشارة مستخرجة من JSON: Ticker={ticker}, Signal={signal_type}")
                return f"Ticker : {ticker} Signal : {signal_type}"

            # 🔒 معالجة البيانات الخام
            raw_data = (request.get_data(as_text=True) or "").strip()
            
            # 🔒 التحقق من الحجم
            if len(raw_data) > self.max_text_length:
                logger.warning(f"⚠️ بيانات خام كبيرة جداً: {len(raw_data)} حرف")
                raw_data = raw_data[:self.max_text_length]
            
            # 🔒 تنظيف البيانات
            sanitized_data = self._sanitize_text(raw_data)
            
            logger.debug(f"📥 إشارة نصية مستخرجة: {sanitized_data[:100]}...")
            return sanitized_data
            
        except Exception as e:
            self._handle_error("💥 خطأ في استخراج الإشارة", e)
            return "EXTRACTION_ERROR"

    def parse_signal(self, raw_signal: str) -> Optional[Dict]:
        """🔒 تحليل نص الإشارة مع التحقق الأمني"""
        if not raw_signal:
            logger.warning("❌ نص الإشارة فارغ")
            return None

        try:
            # 🔒 تنظيف النص أولاً
            text = self._sanitize_text(raw_signal.strip())
            
            if not text:
                logger.warning("❌ نص الإشارة فارغ بعد التنظيف")
                return None

            logger.debug(f"🔍 تحليل الإشارة النصية: '{text}'")

            # 🔒 نمط Ticker : SYMBOL Signal : SIGNAL
            match = re.match(r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+)', text, re.IGNORECASE)
            if match:
                ticker_raw, signal_raw = match.groups()
                
                # 🔒 تنظيف وتطبيع
                ticker = self._sanitize_text(ticker_raw).strip().upper()[:20]
                signal_type = self._sanitize_text(signal_raw).strip()
                
                if not ticker or ticker == 'UNKNOWN':
                    ticker = 'UNKNOWN_SYMBOL'
                
                if not signal_type:
                    signal_type = 'UNKNOWN_SIGNAL'
                
                result = {
                    'symbol': ticker,
                    'signal_type': signal_type,
                    'original_signal': signal_type,
                    'parsed_at': datetime.now().isoformat(),
                    'parsed_with': 'ticker_signal_pattern'
                }
                
                logger.debug(f"   ✅ تم التحليل بنمط Ticker/Signal: {result}")
                return result

            # 🔒 نمط SYMBOL SIGNAL
            match = re.match(r'([A-Za-z0-9]{1,20})\s+(.+)', text)
            if match:
                ticker_raw, signal_raw = match.groups()
                
                ticker = self._sanitize_text(ticker_raw).strip().upper()
                signal_type = self._sanitize_text(signal_raw).strip()
                
                result = {
                    'symbol': ticker if ticker else 'UNKNOWN_SYMBOL',
                    'signal_type': signal_type if signal_type else 'UNKNOWN_SIGNAL',
                    'original_signal': signal_type if signal_type else 'UNKNOWN_SIGNAL',
                    'parsed_at': datetime.now().isoformat(),
                    'parsed_with': 'symbol_signal_pattern'
                }
                
                logger.debug(f"   ✅ تم التحليل بنمط Symbol/Signal: {result}")
                return result

            # 🔒 النمط الافتراضي - النص كله إشارة
            sanitized_text = self._sanitize_text(text)
            
            result = {
                'symbol': "UNKNOWN_SYMBOL",
                'signal_type': sanitized_text,
                'original_signal': sanitized_text,
                'parsed_at': datetime.now().isoformat(),
                'parsed_with': 'default_text'
            }
            
            logger.debug(f"   ⚠️  استخدام النمط الافتراضي: {result}")
            return result

        except Exception as e:
            self._handle_error("💥 خطأ في تحليل الإشارة", e, {'raw_signal': raw_signal[:100]})
            return None

    def process_signal_with_validation(self, signal_data: Dict) -> Dict[str, Any]:
        """🔒 معالجة إشارة مع التحقق الأمني الكامل"""
        start_time = time.time()
        self.metrics["signals_processed"] += 1
        
        try:
            # 🔒 1. التحقق من صحة المدخلات
            if not signal_data or not isinstance(signal_data, dict):
                self.metrics["signals_rejected"] += 1
                return {
                    'success': False,
                    'error': "بيانات الإشارة غير صالحة",
                    'accepted': False
                }
            
            # 🔒 2. التحقق من التكرار
            signal_hash = self._generate_signal_hash(signal_data)
            if self._is_duplicate_signal(signal_hash):
                self.metrics["duplicates_detected"] += 1
                return {
                    'success': False,
                    'error': "إشارة مكررة",
                    'accepted': False,
                    'duplicate': True
                }
            
            # 🔒 3. تصنيف الإشارة
            classification = self.classify_signal(signal_data)
            
            # 🔒 4. حساب الثقة (مثال مبسط)
            confidence = self._calculate_confidence(signal_data, classification)
            
            # 🔒 5. التحقق من عتبة الثقة
            if confidence < self.confidence_threshold:
                self.metrics["signals_rejected"] += 1
                return {
                    'success': False,
                    'error': f"ثقة غير كافية: {confidence:.2f}",
                    'confidence': confidence,
                    'accepted': False
                }
            
            # 🔒 6. إعداد النتيجة
            processing_time = time.time() - start_time
            
            result = {
                'success': True,
                'accepted': True,
                'classification': classification,
                'confidence': round(confidence, 3),
                'symbol': signal_data.get('symbol', 'UNKNOWN').upper(),
                'source': signal_data.get('source', 'unknown'),
                'processing_time_ms': round(processing_time * 1000, 2),
                'signal_hash': signal_hash,
                'timestamp': datetime.now().isoformat()
            }
            
            # 🔒 7. تحديث المقاييس
            self.metrics["signals_accepted"] += 1
            self.signal_history.append(result.copy())
            
            logger.info(
                f"✅ إشارة معالجة: {result['symbol']} - "
                f"{classification} (ثقة: {confidence:.2f})"
            )
            
            return result
            
        except Exception as e:
            self.metrics["processing_errors"] += 1
            self._handle_error("❌ خطأ في معالجة الإشارة", e, {'signal_data': signal_data})
            
            return {
                'success': False,
                'error': f"خطأ في المعالجة: {str(e)}",
                'accepted': False
            }
    
    def _calculate_confidence(self, signal_data: Dict, classification: str) -> float:
        """🔒 حساب درجة الثقة في الإشارة"""
        try:
            base_confidence = 0.5
            
            # 🔒 تعديل بناءً على المصدر
            source = signal_data.get('source', '').lower()
            if source in self.TRUSTED_SOURCES:
                base_confidence += 0.3
            
            # 🔒 تعديل بناءً على التصنيف
            if classification != 'unknown':
                base_confidence += 0.2
            
            # 🔒 تعديل بناءً على طول النص
            text = signal_data.get('text', '')
            if text and len(text) > 10:
                base_confidence += 0.1
            
            # 🔒 تأكد من أن الثقة بين 0 و1
            return max(0.0, min(1.0, base_confidence))
            
        except Exception as e:
            logger.error(f"❌ فشل حساب الثقة: {e}")
            return 0.5

    def get_error_log(self) -> List[Dict]:
        """🔒 الحصول على سجل الأخطاء (آمن)"""
        try:
            # 🔒 إرجاع نسخة آمنة من سجل الأخطاء
            return [self._sanitize_error_entry(entry) for entry in list(self._error_log)]
        except Exception as e:
            logger.error(f"❌ فشل الحصول على سجل الأخطاء: {e}")
            return []

    def _sanitize_error_entry(self, entry: Dict) -> Dict:
        """🔒 تنظيف مدخل خطأ من البيانات الحساسة"""
        try:
            safe_entry = entry.copy()
            
            # 🔒 إزالة البيانات الحساسة من التفاصيل
            if 'details' in safe_entry and safe_entry['details']:
                details = safe_entry['details']
                if isinstance(details, str):
                    # 🔒 إزالة البيانات الحساسة
                    for pattern in ['password', 'token', 'secret', 'key']:
                        if pattern in details.lower():
                            details = details.replace(pattern, "***")
                    safe_entry['details'] = details[:200]
            
            # 🔒 تنظيف السياق
            if 'context' in safe_entry and safe_entry['context']:
                safe_entry['context'] = self._sanitize_context(safe_entry['context'])
            
            return safe_entry
            
        except Exception as e:
            logger.error(f"❌ فشل تنظيف مدخل الخطأ: {e}")
            return {'error': 'sanitization_failed', 'timestamp': datetime.now().isoformat()}

    def clear_error_log(self) -> None:
        """🔒 مسح سجل الأخطاء"""
        try:
            self._error_log.clear()
            logger.info("🧹 تم مسح سجل الأخطاء")
        except Exception as e:
            logger.error(f"❌ فشل مسح سجل الأخطاء: {e}")

    def get_cache_info(self) -> Dict:
        """🔒 الحصول على معلومات التخزين المؤقت"""
        try:
            classify_info = self._classify_signal_text.cache_info()
            return {
                'classify_cache_hits': classify_info.hits,
                'classify_cache_misses': classify_info.misses,
                'classify_cache_size': classify_info.currsize,
                'signal_cache_size': len(self.signal_cache),
                'signal_index_size': len(self.signal_index),
                'error_log_size': len(self._error_log),
                'signal_history_size': len(self.signal_history)
            }
        except Exception as e:
            self._handle_error("💥 خطأ في الحصول على معلومات التخزين المؤقت", e)
            return {}

    def clear_cache(self) -> Dict:
        """🧹 مسح التخزين المؤقت للإشارات"""
        try:
            cache_info_before = self.get_cache_info()
            
            # 🔒 مسح مختلف أنواع التخزين المؤقت
            self._classify_signal_text.cache_clear()
            self.signal_index.clear()
            self.signal_cache.clear()
            
            cache_info_after = self.get_cache_info()
            
            logger.info(f"🧹 تم مسح التخزين المؤقت للإشارات")
            
            return {
                'status': 'success',
                'cache_cleared': True,
                'before': cache_info_before,
                'after': cache_info_after,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self._handle_error("❌ خطأ في مسح التخزين المؤقت", e)
            return {'status': 'error', 'error': str(e)}

    def cleanup_memory(self) -> Dict:
        """🧹 تنظيف الذاكرة وإدارة التخزين"""
        try:
            cleaned_info = {
                'error_log_cleaned': 0,
                'signal_index_cleaned': 0,
                'signal_cache_cleaned': 0,
                'cache_cleared': False
            }
            
            # 🔒 تنظيف error_log إذا تجاوز الحد
            if len(self._error_log) > self.MAX_ERROR_LOG_SIZE:
                items_to_remove = len(self._error_log) - self.MAX_ERROR_LOG_SIZE
                for _ in range(items_to_remove):
                    if self._error_log:
                        self._error_log.popleft()
                cleaned_info['error_log_cleaned'] = items_to_remove
            
            # 🔒 تنظيف signal_index القديم
            if len(self.signal_index) > self.MAX_SIGNAL_INDEX_SIZE:
                items_to_remove = len(self.signal_index) - self.MAX_SIGNAL_INDEX_SIZE
                
                # 🔒 حفظ أحدث الإدخالات
                all_items = list(self.signal_index.items())
                self.signal_index.clear()
                
                for key, value in all_items[-self.MAX_SIGNAL_INDEX_SIZE:]:
                    self.signal_index[key] = value
                
                cleaned_info['signal_index_cleaned'] = items_to_remove
            
            # 🔒 تنظيف signal_cache القديم
            current_time = time.time()
            expired_hashes = [
                h for h, t in self.signal_cache.items()
                if current_time - t > self.SIGNAL_TIMEOUT_SECONDS
            ]
            
            for h in expired_hashes:
                self.signal_cache.pop(h, None)
            
            cleaned_info['signal_cache_cleaned'] = len(expired_hashes)
            
            # 🔒 مسح التخزين المؤقت إذا كان كبيراً جداً
            classify_info = self._classify_signal_text.cache_info()
            if classify_info.currsize > self.MAX_CACHE_SIZE:
                self._classify_signal_text.cache_clear()
                cleaned_info['cache_cleared'] = True
            
            logger.info(f"🧹 تنظيف الذاكرة: {cleaned_info}")
            
            return {
                **cleaned_info,
                'current_cache_size': classify_info.currsize,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف الذاكرة", e)
            return {'error': str(e)}

    def get_system_stats(self) -> Dict:
        """📊 الحصول على إحصائيات النظام"""
        try:
            classify_info = self._classify_signal_text.cache_info()
            
            # 🔒 حساب عدد الإشارات لكل فئة
            signals_by_category = {}
            for category, signal_list in self.signals.items():
                if signal_list and isinstance(signal_list, list):
                    signals_by_category[category] = len(signal_list)
                else:
                    signals_by_category[category] = 0
            
            # 🔒 إحصائيات الفهرس
            index_by_category = defaultdict(int)
            for signal, category in self.signal_index.items():
                index_by_category[category] += 1
            
            return {
                **self.metrics,
                'signal_index_size': len(self.signal_index),
                'error_log_size': len(self._error_log),
                'signal_cache_size': len(self.signal_cache),
                'signal_history_size': len(self.signal_history),
                'cache_stats': {
                    'hits': classify_info.hits,
                    'misses': classify_info.misses,
                    'size': classify_info.currsize,
                    'maxsize': classify_info.maxsize
                },
                'signals_by_category': dict(signals_by_category),
                'index_by_category': dict(index_by_category),
                'total_signals': sum(signals_by_category.values()),
                'confidence_threshold': self.confidence_threshold,
                'max_text_length': self.max_text_length,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self._handle_error("💥 خطأ في الحصول على إحصائيات النظام", e)
            return {'error': str(e)}
    
    def _log_init_summary(self):
        """🔒 تسجيل ملخص التهيئة"""
        summary = {
            'signals_categories': len(self.signals),
            'total_signals_configured': sum(len(v) for v in self.signals.values() if isinstance(v, list)),
            'confidence_threshold': self.confidence_threshold,
            'max_text_length': self.max_text_length,
            'max_cache_size': self.MAX_CACHE_SIZE,
            'max_signal_index_size': self.MAX_SIGNAL_INDEX_SIZE
        }
        
        logger.info(f"📊 ملخص تهيئة SignalProcessor: {json.dumps(summary, ensure_ascii=False)}")
