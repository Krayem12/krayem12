import re
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from functools import lru_cache
from collections import deque

logger = logging.getLogger(__name__)

class SignalProcessor:
    """🎯 معالج الإشارات مع تحسينات الأداء والتخزين المؤقت"""

    def __init__(self, config, signals, keywords):
        self.config = config
        self.signals = signals
        self.keywords = keywords
        self.signal_index = {}
        self._error_log = deque(maxlen=500)  # 🔧 FIXED: استخدام deque للحد من النمو
        self.setup_signal_index()
        logger.info("🎯 نظام التصنيف الصارم مع التخزين المؤقت مفعل")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error': full_error
        }
        self._error_log.append(error_entry)

    def setup_signal_index(self) -> None:
        """بناء فهرس الإشارات مع تحسين الأداء"""
        logger.debug("🔍 بناء فهرس الإشارات...")
        try:
            index_count = 0
            for category, signal_list in self.signals.items():
                if signal_list:  # 🔧 FIXED: التحقق من وجود قائمة
                    for signal in signal_list:
                        if signal and isinstance(signal, str):  # 🔧 FIXED: التحقق من النوع
                            normalized = signal.lower().strip()
                            if normalized:  # 🔧 FIXED: تجاهل القيم الفارغة
                                self.signal_index[normalized] = category
                                index_count += 1
            
            # 🆕 تسجيل جميع الإشارات المتاحة للتصحيح
            logger.debug(f"📋 فهرس الإشارات المبني: {index_count} إشارة")
            for category, signals in self.signals.items():
                if signals:  # فقط العناوين التي تحتوي على إشارات
                    logger.debug(f"   📁 {category}: {len(signals)} إشارة - {signals[:3]}{'...' if len(signals) > 3 else ''}")
                    
        except Exception as e:
            self._handle_error("❌ خطأ في بناء فهرس الإشارات", e)

    def classify_signal(self, signal_data: Dict) -> str:
        """🎯 تصنيف الإشارة بدون التخزين المؤقت للقاموس"""
        if not signal_data or 'signal_type' not in signal_data:
            logger.warning("❌ بيانات الإشارة غير صالحة للتصنيف")
            return 'unknown'

        signal_type = signal_data['signal_type']
        if not signal_type or not isinstance(signal_type, str) or not signal_type.strip():
            logger.warning("❌ نوع الإشارة فارغ أو غير نصي")
            return 'unknown'
            
        signal_lower = signal_type.lower().strip()
        
        logger.debug(f"🔍 تصنيف الإشارة: '{signal_type}' -> '{signal_lower}'")
        
        # استخدام دالة مساعدة مع التخزين المؤقت للنص فقط
        classification = self._classify_signal_text(signal_lower)
        logger.debug(f"🎯 نتيجة التصنيف: '{signal_type}' -> '{classification}'")
        
        return classification

    @lru_cache(maxsize=1000)
    def _classify_signal_text(self, signal_text: str) -> str:
        """تصنيف نص الإشارة مع التخزين المؤقت وتحسينات"""
        try:
            # تنظيف النص أولاً
            if not signal_text or not isinstance(signal_text, str):
                return 'unknown'
                
            cleaned_signal = signal_text.lower().strip()
            
            logger.debug(f"🔍 تصنيف الإشارة المنظفة: '{cleaned_signal}'")
            
            # البحث في الفهرس أولاً للأداء
            if cleaned_signal in self.signal_index:
                category = self.signal_index[cleaned_signal]
                logger.debug(f"   ✅ تم العثور على الإشارة في الفهرس: {cleaned_signal} -> {category}")
                return category

            # البحث في القوائم المحددة
            for category, signal_list in self.signals.items():
                if not signal_list:
                    continue
                    
                normalized_signals = [s.lower().strip() for s in signal_list if s and isinstance(s, str)]
                if cleaned_signal in normalized_signals:
                    # تحديث الفهرس للاستخدام المستقبلي
                    self.signal_index[cleaned_signal] = category
                    logger.debug(f"   ✅ تم العثور على الإشارة في القوائم: {cleaned_signal} -> {category}")
                    return category

            # 🆕 محاولة البحث الجزئي للإشارات الطويلة
            for category, signal_list in self.signals.items():
                if not signal_list:
                    continue
                    
                for signal in signal_list:
                    if signal and isinstance(signal, str) and cleaned_signal in signal.lower():
                        self.signal_index[cleaned_signal] = category
                        logger.debug(f"   ✅ تم العثور على الإشارة بالبحث الجزئي: {cleaned_signal} -> {category}")
                        return category

            # 🆕 تسجيل تفصيلي للإشارات غير المعروفة
            logger.warning(f"❌ نوع إشارة غير معروف: '{cleaned_signal}'")
            
            # 🆕 تسجيل جميع الإشارات المتاحة للمساعدة في التصحيح
            available_signals = []
            for cat, sig_list in self.signals.items():
                if sig_list:
                    available_signals.extend([f"{sig}->{cat}" for sig in sig_list[:2] if sig and isinstance(sig, str)])
            
            if available_signals:
                logger.debug(f"📋 الإشارات المتاحة: {', '.join(available_signals[:10])}{'...' if len(available_signals) > 10 else ''}")
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"💥 خطأ في التصنيف: {e}")
            return 'unknown'

    def safe_classify_signal(self, signal_data: Dict) -> str:
        """تصنيف آمن مع معالجة الأخطاء"""
        try:
            return self.classify_signal(signal_data)
        except Exception as e:
            self._handle_error("💥 خطأ في التصنيف الآمن", e)
            return 'unknown'

    def extract_signal(self, request) -> str:
        """استخراج الإشارة من الطلب"""
        content_type = (request.headers.get('Content-Type') or '').lower()

        if 'application/json' in content_type:
            data = request.get_json(silent=True) or {}
            ticker = data.get('ticker') or data.get('symbol') or 'UNKNOWN'
            signal_type = data.get('signal') or data.get('action') or 'UNKNOWN'
            
            # 🔧 FIXED: تحسين معالجة القيم الفارغة
            ticker = str(ticker) if ticker else 'UNKNOWN'
            signal_type = str(signal_type) if signal_type else 'UNKNOWN'
            
            logger.debug(f"📥 إشارة مستخرجة من JSON: Ticker={ticker}, Signal={signal_type}")
            return f"Ticker : {ticker} Signal : {signal_type}"

        raw_data = (request.get_data(as_text=True) or "").strip()
        logger.debug(f"📥 إشارة نصية مستخرجة: {raw_data}")
        return raw_data

    def parse_signal(self, raw_signal: str) -> Optional[Dict]:
        """تحليل نص الإشارة"""
        text = (raw_signal or "").strip()
        if not text:
            logger.warning("❌ نص الإشارة فارغ")
            return None

        try:
            logger.debug(f"🔍 تحليل الإشارة النصية: '{text}'")

            # نمط Ticker : SYMBOL Signal : SIGNAL
            match = re.match(r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+)', text, re.IGNORECASE)
            if match:
                ticker, signal_type = match.groups()
                result = {
                    'symbol': str(ticker).strip().upper() if ticker else 'UNKNOWN',
                    'signal_type': str(signal_type).strip() if signal_type else 'UNKNOWN',
                    'original_signal': str(signal_type).strip() if signal_type else 'UNKNOWN'
                }
                logger.debug(f"   ✅ تم التحليل بنمط Ticker/Signal: {result}")
                return result

            # نمط SYMBOL SIGNAL
            match = re.match(r'([A-Za-z0-9]+)\s+(.+)', text)
            if match:
                ticker, signal_type = match.groups()
                result = {
                    'symbol': str(ticker).strip().upper() if ticker else 'UNKNOWN',
                    'signal_type': str(signal_type).strip() if signal_type else 'UNKNOWN',
                    'original_signal': str(signal_type).strip() if signal_type else 'UNKNOWN'
                }
                logger.debug(f"   ✅ تم التحليل بنمط Symbol/Signal: {result}")
                return result

            # نمط الإشارة فقط
            result = {
                'symbol': "UNKNOWN",
                'signal_type': text,
                'original_signal': text
            }
            logger.debug(f"   ⚠️  استخدام النمط الافتراضي: {result}")
            return result

        except Exception as e:
            self._handle_error("💥 Parse error", e)
            return None

    def get_error_log(self) -> List[Dict]:
        """الحصول على سجل الأخطاء"""
        return list(self._error_log)

    def clear_error_log(self) -> None:
        """مسح سجل الأخطاء"""
        self._error_log.clear()

    def get_cache_info(self) -> Dict:
        """الحصول على معلومات التخزين المؤقت"""
        try:
            classify_info = self._classify_signal_text.cache_info()
            return {
                'classify_cache_hits': classify_info.hits,
                'classify_cache_misses': classify_info.misses,
                'classify_cache_size': classify_info.currsize,
                'signal_index_size': len(self.signal_index),
                'error_log_size': len(self._error_log)
            }
        except Exception as e:
            self._handle_error("💥 خطأ في الحصول على معلومات التخزين المؤقت", e)
            return {}

    def clear_cache(self) -> Dict:
        """🧹 مسح التخزين المؤقت للإشارات"""
        try:
            cache_info_before = self.get_cache_info()
            
            self._classify_signal_text.cache_clear()
            self.signal_index.clear()
            
            cache_info_after = self.get_cache_info()
            
            logger.info(f"🧹 تم مسح التخزين المؤقت للإشارات - قبل: {cache_info_before.get('classify_cache_size')}, بعد: {cache_info_after.get('classify_cache_size')}")
            
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
            # تنظيف error_log إذا تجاوز الحد
            error_log_cleaned = 0
            if len(self._error_log) > 500:
                error_log_cleaned = len(self._error_log) - 500
                for _ in range(error_log_cleaned):
                    if self._error_log:
                        self._error_log.popleft()
            
            # تنظيف signal_index القديم (حفظ آخر 1000 إدخال)
            signal_index_cleaned = 0
            if len(self.signal_index) > 1000:
                signal_index_cleaned = len(self.signal_index) - 1000
                # تحويل إلى قائمة وأخذ الأخيرة
                all_keys = list(self.signal_index.keys())
                for key in all_keys[:-1000]:
                    del self.signal_index[key]
            
            # مسح التخزين المؤقت إذا كان كبيراً جداً
            cache_cleared = False
            classify_info = self._classify_signal_text.cache_info()
            if classify_info.currsize > 500:
                self._classify_signal_text.cache_clear()
                cache_cleared = True
            
            logger.info(f"🧹 تنظيف الذاكرة: تم تنظيف {error_log_cleaned} خطأ، {signal_index_cleaned} إدخال مؤشر، تم مسح التخزين المؤقت: {cache_cleared}")
            
            return {
                'error_log_cleaned': error_log_cleaned,
                'signal_index_cleaned': signal_index_cleaned,
                'cache_cleared': cache_cleared,
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
            
            # حساب عدد الإشارات لكل فئة
            signals_by_category = {}
            for category, signal_list in self.signals.items():
                if signal_list:
                    signals_by_category[category] = len(signal_list)
                else:
                    signals_by_category[category] = 0
            
            return {
                'signal_index_size': len(self.signal_index),
                'error_log_size': len(self._error_log),
                'cache_stats': {
                    'hits': classify_info.hits,
                    'misses': classify_info.misses,
                    'size': classify_info.currsize,
                    'maxsize': classify_info.maxsize
                },
                'signals_by_category': signals_by_category,
                'total_signals': sum(signals_by_category.values()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self._handle_error("💥 خطأ في الحصول على إحصائيات النظام", e)
            return {'error': str(e)}