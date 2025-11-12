# core/signal_processor.py
import re
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SignalProcessor:
    """Process and classify trading signals with 100% STRICT EXACT MATCH only"""

    def __init__(self, config, signals, keywords):
        self.config = config
        self.signals = signals
        self.keywords = keywords  # 🚨 نحتفظ بها ولكن لا نستخدمها
        self.signal_index = {}
        self.setup_signal_index()
        logger.info("🎯 نظام التصنيف الصارم مفعل - التطابق التام 100% فقط")

    def setup_signal_index(self):
        """Optimized signal lookup index for better performance"""
        logger.debug("🔍 بناء فهرس الإشارات...")
        for category, signal_list in self.signals.items():
            for signal in signal_list:
                normalized = signal.lower().strip()
                self.signal_index[normalized] = category
                logger.debug(f"   📝 مسجل: '{signal}' → {category}")

    def extract_signal(self, request):
        """Extract signal from request"""
        content_type = (request.headers.get('Content-Type') or '').lower()

        if 'application/json' in content_type:
            data = request.get_json(silent=True) or {}
            ticker = data.get('ticker') or data.get('symbol') or 'UNKNOWN'
            signal_type = data.get('signal') or data.get('action') or 'UNKNOWN'
            return f"Ticker : {ticker} Signal : {signal_type}"

        return (request.get_data(as_text=True) or "").strip()

    def parse_signal(self, raw_signal):
        """Parse signal text"""
        text = (raw_signal or "").strip()
        if not text:
            return None

        try:
            match = re.match(r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+)', text)
            if match:
                ticker, signal_type = match.groups()
                return {
                    'symbol': ticker.strip().upper(),
                    'signal_type': signal_type.strip(),
                    'original_signal': signal_type.strip()
                }

            match = re.match(r'([A-Za-z0-9]+)\s+(.+)', text)
            if match:
                ticker, signal_type = match.groups()
                return {
                    'symbol': ticker.strip().upper(),
                    'signal_type': signal_type.strip(),
                    'original_signal': signal_type.strip()
                }

            return {
                'symbol': "UNKNOWN",
                'signal_type': text,
                'original_signal': text
            }

        except Exception as e:
            logger.error(f"💥 Parse error: {e}")
            return None

    def safe_classify_signal(self, signal_data):
        """🆕 تصنيف آمن مع معالجة الأخطاء المحسنة"""
        try:
            if not signal_data:
                logger.error("❌ بيانات الإشارة فارغة")
                return 'unknown'
                
            if 'signal_type' not in signal_data:
                logger.error("❌ نوع الإشارة مفقود في البيانات")
                return 'unknown'
                
            signal_type = signal_data.get('signal_type', '').strip()
            if not signal_type:
                logger.error("❌ نوع الإشارة فارغ")
                return 'unknown'
                
            return self.classify_signal(signal_data)
            
        except Exception as e:
            logger.error(f"💥 خطأ في التصنيف الآمن: {e}")
            return 'unknown'

    def classify_signal(self, signal_data):
        """🎯 100% STRICT EXACT MATCH CLASSIFICATION - مع تفاصيل تصحيح محسنة"""
        logger.debug(f"🔍 بدء تصنيف الإشارة: {signal_data}")
        
        if not signal_data or 'signal_type' not in signal_data:
            logger.error("❌ لا توجد بيانات إشارة أو نوع إشارة")
            return 'unknown'

        signal_type = signal_data['signal_type']
        if not signal_type or not signal_type.strip():
            logger.error("❌ نوع الإشارة فارغ")
            return 'unknown'
            
        signal_lower = signal_type.lower().strip()
        
        logger.debug(f"🔍 تحليل الإشارة: '{signal_type}' (بعد التطبيع: '{signal_lower}')")
        
        # 🛠️ الإصلاح: معالجة خاصة لإشارات GROUP3
        # إزالة البوادئ bullish_ و bearish_ للتحقق من GROUP3
        group3_signal_clean = signal_lower
        if signal_lower.startswith('bullish_'):
            group3_signal_clean = signal_lower.replace('bullish_', '')
            logger.debug(f"🔍 تنظيف إشارة GROUP3: '{signal_lower}' -> '{group3_signal_clean}'")
        elif signal_lower.startswith('bearish_'):
            group3_signal_clean = signal_lower.replace('bearish_', '')
            logger.debug(f"🔍 تنظيف إشارة GROUP3: '{signal_lower}' -> '{group3_signal_clean}'")
        
        # 🎯 100% STRICT EXACT MATCH: Convert all signals to lowercase for exact comparison
        trend_signals = [s.lower().strip() for s in self.signals.get('trend', [])]
        trend_confirm_signals = [s.lower().strip() for s in self.signals.get('trend_confirm', [])]
        exit_signals = [s.lower().strip() for s in self.signals.get('exit', [])]
        group1_bullish_signals = [s.lower().strip() for s in self.signals.get('entry_bullish', [])]
        group1_bearish_signals = [s.lower().strip() for s in self.signals.get('entry_bearish', [])]
        group2_bullish_signals = [s.lower().strip() for s in self.signals.get('entry_bullish1', [])]
        group2_bearish_signals = [s.lower().strip() for s in self.signals.get('entry_bearish1', [])]
        
        # 🆕 GROUP3: قوائم منفصلة للإشارات الصاعدة والهابطة
        group3_bullish_signals = [s.lower().strip() for s in self.signals.get('group3_bullish', [])]
        group3_bearish_signals = [s.lower().strip() for s in self.signals.get('group3_bearish', [])]

        logger.debug(f"🔍 البحث في {len(trend_signals)} إشارة اتجاه")
        # 🎯 HIGHEST PRIORITY: Check for trend signals - 100% EXACT MATCH ONLY
        for trend_signal in trend_signals:
            if trend_signal == signal_lower:
                logger.debug(f"🎯 تم التطابق مع إشارة اتجاه: '{signal_type}' == '{trend_signal}'")
                logger.debug(f"🎯 تم التصنيف كإشارة اتجاه (تطابق تام 100%): '{signal_type}' → 'trend'")
                return 'trend'
        
        logger.debug(f"🔍 البحث في {len(trend_confirm_signals)} إشارة تأكيد اتجاه")
        # 🎯 Check for trend confirmation signals - 100% EXACT MATCH ONLY
        for trend_confirm_signal in trend_confirm_signals:
            if trend_confirm_signal == signal_lower:
                logger.debug(f"🎯 تم التطابق مع تأكيد اتجاه: '{signal_type}' == '{trend_confirm_signal}'")
                logger.debug(f"🎯 تم التصنيف كتأكيد اتجاه (تطابق تام 100%): '{signal_type}' → 'trend_confirm'")
                return 'trend_confirm'

        logger.debug(f"🔍 البحث في {len(exit_signals)} إشارة خروج")
        # 🎯 Check for exit signals - 100% EXACT MATCH ONLY
        for exit_signal in exit_signals:
            if exit_signal == signal_lower:
                logger.debug(f"🎯 تم التطابق مع إشارة خروج: '{signal_type}' == '{exit_signal}'")
                logger.debug(f"🎯 تم التصنيف كإشارة خروج (تطابق تام 100%): '{signal_type}' → 'exit'")
                return 'exit'

        logger.debug(f"🔍 البحث في {len(group1_bullish_signals)} إشارة مجموعة1 صاعدة")
        # 🎯 Check group1 signals - 100% EXACT MATCH ONLY
        for signal in group1_bullish_signals:
            if signal == signal_lower:
                logger.debug(f"🎯 تم التطابق مع مجموعة1 صاعدة: '{signal_type}' == '{signal}'")
                logger.debug(f"🎯 تم التصنيف كدخول صاعد (مجموعة1 - تطابق تام 100%): '{signal_type}' → 'entry_bullish'")
                return 'entry_bullish'
                
        logger.debug(f"🔍 البحث في {len(group1_bearish_signals)} إشارة مجموعة1 هابطة")        
        for signal in group1_bearish_signals:
            if signal == signal_lower:
                logger.debug(f"🎯 تم التطابق مع مجموعة1 هابطة: '{signal_type}' == '{signal}'")
                logger.debug(f"🎯 تم التصنيف كدخول هابط (مجموعة1 - تطابق تام 100%): '{signal_type}' → 'entry_bearish'")
                return 'entry_bearish'

        logger.debug(f"🔍 البحث في {len(group2_bullish_signals)} إشارة مجموعة2 صاعدة")
        # 🎯 Check group2 signals - 100% EXACT MATCH ONLY
        for signal in group2_bullish_signals:
            if signal == signal_lower:
                logger.debug(f"🎯 تم التطابق مع مجموعة2 صاعدة: '{signal_type}' == '{signal}'")
                logger.debug(f"🎯 تم التصنيف كدخول صاعد (مجموعة2 - تطابق تام 100%): '{signal_type}' → 'entry_bullish1'")
                return 'entry_bullish1'
                
        logger.debug(f"🔍 البحث في {len(group2_bearish_signals)} إشارة مجموعة2 هابطة")
        for signal in group2_bearish_signals:
            if signal == signal_lower:
                logger.debug(f"🎯 تم التطابق مع مجموعة2 هابطة: '{signal_type}' == '{signal}'")
                logger.debug(f"🎯 تم التصنيف كدخول هابط (مجموعة2 - تطابق تام 100%): '{signal_type}' → 'entry_bearish1'")
                return 'entry_bearish1'

        logger.debug(f"🔍 البحث في {len(group3_bullish_signals)} إشارة مجموعة3 صاعدة")
        # 🎯 Check group3 signals - 100% EXACT MATCH ONLY WITH SEPARATE LISTS + CLEANED SIGNALS
        for signal in group3_bullish_signals:
            if signal == signal_lower or signal == group3_signal_clean:
                logger.debug(f"🎯 تم التطابق مع مجموعة3 صاعدة: '{signal_type}' == '{signal}'")
                logger.debug(f"🎯 تم التصنيف كمجموعة ثالثة صاعدة (تطابق تام 100%): '{signal_type}' → 'group3'")
                return 'group3'
                
        logger.debug(f"🔍 البحث في {len(group3_bearish_signals)} إشارة مجموعة3 هابطة")
        for signal in group3_bearish_signals:
            if signal == signal_lower or signal == group3_signal_clean:
                logger.debug(f"🎯 تم التطابق مع مجموعة3 هابطة: '{signal_type}' == '{signal}'")
                logger.debug(f"🎯 تم التصنيف كمجموعة ثالثة هابطة (تطابق تام 100%): '{signal_type}' → 'group3'")
                return 'group3'

        # 🚫 NO FALLBACK - NO KEYWORD MATCHING - NO PARTIAL MATCHING
        logger.warning(f"❌ نوع إشارة غير معروف (لا يوجد تطابق تام 100%): '{signal_type}'")
        logger.debug(f"📋 الإشارات المعروفة في المجموعات:")
        logger.debug(f"   🔴 مجموعة1 صاعد: {group1_bullish_signals}")
        logger.debug(f"   🔴 مجموعة1 هابط: {group1_bearish_signals}")
        logger.debug(f"   🔵 مجموعة2 صاعد: {group2_bullish_signals}")
        logger.debug(f"   🔵 مجموعة2 هابط: {group2_bearish_signals}")
        logger.debug(f"   🟢 مجموعة3 صاعد: {group3_bullish_signals}")
        logger.debug(f"   🟢 مجموعة3 هابط: {group3_bearish_signals}")
        
        return 'unknown'

    def validate_signal_strict(self, signal_type):
        """🎯 التحقق الصارم من وجود الإشارة في أي قائمة"""
        if not signal_type or not signal_type.strip():
            return False, None
            
        signal_lower = signal_type.lower().strip()
        
        # 🛠️ الإصلاح: معالجة خاصة لإشارات GROUP3
        group3_signal_clean = signal_lower
        if signal_lower.startswith('bullish_'):
            group3_signal_clean = signal_lower.replace('bullish_', '')
        elif signal_lower.startswith('bearish_'):
            group3_signal_clean = signal_lower.replace('bearish_', '')
        
        # التحقق في جميع القوائم
        all_categories = {
            'trend': self.signals.get('trend', []),
            'trend_confirm': self.signals.get('trend_confirm', []),
            'exit': self.signals.get('exit', []),
            'entry_bullish': self.signals.get('entry_bullish', []),
            'entry_bearish': self.signals.get('entry_bearish', []),
            'entry_bullish1': self.signals.get('entry_bullish1', []),
            'entry_bearish1': self.signals.get('entry_bearish1', []),
            'group3_bullish': self.signals.get('group3_bullish', []),
            'group3_bearish': self.signals.get('group3_bearish', [])
        }
        
        for category, signals in all_categories.items():
            signal_list = [s.lower().strip() for s in signals]
            if signal_lower in signal_list or (category.startswith('group3') and group3_signal_clean in signal_list):
                return True, category
                
        return False, None