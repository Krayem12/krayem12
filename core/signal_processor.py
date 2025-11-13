# core/signal_processor.py
import re
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from functools import lru_cache

logger = logging.getLogger(__name__)

class SignalProcessor:
    """🎯 معالج الإشارات مع تحسينات الأداء والتخزين المؤقت"""

    def __init__(self, config, signals, keywords):
        self.config = config
        self.signals = signals
        self.keywords = keywords
        self.signal_index = {}
        self._error_log = []
        self.setup_signal_index()
        logger.info("🎯 نظام التصنيف الصارم مع التخزين المؤقت مفعل")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append(full_error)

    def setup_signal_index(self) -> None:
        """بناء فهرس الإشارات مع تحسين الأداء"""
        logger.debug("🔍 بناء فهرس الإشارات...")
        try:
            index_count = 0
            for category, signal_list in self.signals.items():
                for signal in signal_list:
                    normalized = signal.lower().strip()
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
        if not signal_type or not signal_type.strip():
            logger.warning("❌ نوع الإشارة فارغ")
            return 'unknown'
            
        signal_lower = signal_type.lower().strip()
        
        logger.debug(f"🔍 تصنيف الإشارة: '{signal_type}' -> '{signal_lower}'")
        
        # استخدام دالة مساعدة مع التخزين المؤقت للنص فقط
        classification = self._classify_signal_text(signal_lower)
        logger.debug(f"🎯 نتيجة التصنيف: '{signal_type}' -> '{classification}'")
        
        return classification

    @lru_cache(maxsize=1000)
    def _classify_signal_text(self, signal_text: str) -> str:
        """تصنيف نص الإشارة مع التخزين المؤقت"""
        # البحث في الفهرس أولاً للأداء
        if signal_text in self.signal_index:
            category = self.signal_index[signal_text]
            logger.debug(f"   ✅ تم العثور على الإشارة في الفهرس: {signal_text} -> {category}")
            return category

        # البحث في القوائم المحددة
        for category, signal_list in self.signals.items():
            normalized_signals = [s.lower().strip() for s in signal_list]
            if signal_text in normalized_signals:
                # تحديث الفهرس للاستخدام المستقبلي
                self.signal_index[signal_text] = category
                logger.debug(f"   ✅ تم العثور على الإشارة في القوائم: {signal_text} -> {category}")
                return category

        # 🆕 تسجيل تفصيلي للإشارات غير المعروفة
        logger.warning(f"❌ نوع إشارة غير معروف: '{signal_text}'")
        
        # 🆕 تسجيل جميع الإشارات المتاحة للمساعدة في التصحيح
        available_signals = []
        for cat, sig_list in self.signals.items():
            if sig_list:
                available_signals.extend([f"{sig}->{cat}" for sig in sig_list[:2]])  # أول إشارتين من كل فئة
        
        logger.debug(f"📋 الإشارات المتاحة: {', '.join(available_signals[:10])}{'...' if len(available_signals) > 10 else ''}")
        
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
                    'symbol': ticker.strip().upper(),
                    'signal_type': signal_type.strip(),
                    'original_signal': signal_type.strip()
                }
                logger.debug(f"   ✅ تم التحليل بنمط Ticker/Signal: {result}")
                return result

            # نمط SYMBOL SIGNAL
            match = re.match(r'([A-Za-z0-9]+)\s+(.+)', text)
            if match:
                ticker, signal_type = match.groups()
                result = {
                    'symbol': ticker.strip().upper(),
                    'signal_type': signal_type.strip(),
                    'original_signal': signal_type.strip()
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

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()

    def clear_error_log(self) -> None:
        """مسح سجل الأخطاء"""
        self._error_log.clear()

    def get_cache_info(self) -> Dict:
        """الحصول على معلومات التخزين المؤقت"""
        classify_info = self._classify_signal_text.cache_info()
        return {
            'classify_cache_hits': classify_info.hits,
            'classify_cache_misses': classify_info.misses,
            'classify_cache_size': classify_info.currsize,
            'signal_index_size': len(self.signal_index)
        }