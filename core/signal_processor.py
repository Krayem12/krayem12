# core/signal_processor.py
import re
import hashlib
from datetime import datetime

class SignalProcessor:
    """Process and classify trading signals with 100% STRICT EXACT MATCH only"""

    def __init__(self, config, signals, keywords):
        self.config = config
        self.signals = signals
        self.keywords = keywords  # 🚨 نحتفظ بها ولكن لا نستخدمها
        self.signal_index = {}
        self.setup_signal_index()
        print("🎯 نظام التصنيف الصارم مفعل - التطابق التام 100% فقط")

    def setup_signal_index(self):
        """Optimized signal lookup index for better performance"""
        for category, signal_list in self.signals.items():
            for signal in signal_list:
                normalized = signal.lower().strip()
                self.signal_index[normalized] = category
                # تسجيل جميع الإشارات المعروفة
                print(f"   📝 مسجل: '{signal}' → {category}")

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
            print(f"💥 Parse error: {e}")
            return None

    def classify_signal(self, signal_data):
        """🎯 100% STRICT EXACT MATCH CLASSIFICATION - NO KEYWORDS, NO PARTIAL MATCHES"""
        if not signal_data or 'signal_type' not in signal_data:
            print("❌ لا توجد بيانات إشارة أو نوع إشارة")
            return 'unknown'

        signal_type = signal_data['signal_type']
        signal_lower = signal_type.lower().strip()
        
        print(f"🔍 تحليل الإشارة: '{signal_type}'")
        
        # 🎯 100% STRICT EXACT MATCH: Convert all signals to lowercase for exact comparison
        trend_signals = [s.lower().strip() for s in self.signals.get('trend', [])]
        trend_confirm_signals = [s.lower().strip() for s in self.signals.get('trend_confirm', [])]
        exit_signals = [s.lower().strip() for s in self.signals.get('exit', [])]
        group1_bullish_signals = [s.lower().strip() for s in self.signals.get('entry_bullish', [])]
        group1_bearish_signals = [s.lower().strip() for s in self.signals.get('entry_bearish', [])]
        group2_bullish_signals = [s.lower().strip() for s in self.signals.get('entry_bullish1', [])]
        group2_bearish_signals = [s.lower().strip() for s in self.signals.get('entry_bearish1', [])]
        group3_signals = [s.lower().strip() for s in self.signals.get('group3', [])]

        # 🎯 HIGHEST PRIORITY: Check for trend signals - 100% EXACT MATCH ONLY
        for trend_signal in trend_signals:
            if trend_signal == signal_lower:
                print(f"🎯 تم التصنيف كإشارة اتجاه (تطابق تام 100%): '{signal_type}' → 'trend'")
                return 'trend'
        
        # 🎯 Check for trend confirmation signals - 100% EXACT MATCH ONLY
        for trend_confirm_signal in trend_confirm_signals:
            if trend_confirm_signal == signal_lower:
                print(f"🎯 تم التصنيف كتأكيد اتجاه (تطابق تام 100%): '{signal_type}' → 'trend_confirm'")
                return 'trend_confirm'

        # 🎯 Check for exit signals - 100% EXACT MATCH ONLY
        for exit_signal in exit_signals:
            if exit_signal == signal_lower:
                print(f"🎯 تم التصنيف كإشارة خروج (تطابق تام 100%): '{signal_type}' → 'exit'")
                return 'exit'

        # 🎯 Check group1 signals - 100% EXACT MATCH ONLY
        for signal in group1_bullish_signals:
            if signal == signal_lower:
                print(f"🎯 تم التصنيف كدخول صاعد (مجموعة1 - تطابق تام 100%): '{signal_type}' → 'entry_bullish'")
                return 'entry_bullish'
                
        for signal in group1_bearish_signals:
            if signal == signal_lower:
                print(f"🎯 تم التصنيف كدخول هابط (مجموعة1 - تطابق تام 100%): '{signal_type}' → 'entry_bearish'")
                return 'entry_bearish'

        # 🎯 Check group2 signals - 100% EXACT MATCH ONLY
        for signal in group2_bullish_signals:
            if signal == signal_lower:
                print(f"🎯 تم التصنيف كدخول صاعد (مجموعة2 - تطابق تام 100%): '{signal_type}' → 'entry_bullish1'")
                return 'entry_bullish1'
                
        for signal in group2_bearish_signals:
            if signal == signal_lower:
                print(f"🎯 تم التصنيف كدخول هابط (مجموعة2 - تطابق تام 100%): '{signal_type}' → 'entry_bearish1'")
                return 'entry_bearish1'

        # 🎯 Check group3 signals - 100% EXACT MATCH ONLY
        for group3_signal in group3_signals:
            if group3_signal == signal_lower:
                print(f"🎯 تم التصنيف كمجموعة ثالثة (تطابق تام 100%): '{signal_type}' → 'group3'")
                return 'group3'

        # 🚫 NO FALLBACK - NO KEYWORD MATCHING - NO PARTIAL MATCHING
        print(f"❌ نوع إشارة غير معروف (لا يوجد تطابق تام 100%): '{signal_type}'")
        print(f"📋 الإشارات المعروفة في المجموعات:")
        print(f"   🔴 مجموعة1 صاعد: {group1_bullish_signals}")
        print(f"   🔴 مجموعة1 هابط: {group1_bearish_signals}")
        print(f"   🔵 مجموعة2 صاعد: {group2_bullish_signals}")
        print(f"   🔵 مجموعة2 هابط: {group2_bearish_signals}")
        print(f"   🟢 مجموعة3: {group3_signals}")
        
        return 'unknown'

    def validate_signal_strict(self, signal_type):
        """🎯 التحقق الصارم من وجود الإشارة في أي قائمة"""
        signal_lower = signal_type.lower().strip()
        
        # التحقق في جميع القوائم
        all_categories = {
            'trend': self.signals.get('trend', []),
            'trend_confirm': self.signals.get('trend_confirm', []),
            'exit': self.signals.get('exit', []),
            'entry_bullish': self.signals.get('entry_bullish', []),
            'entry_bearish': self.signals.get('entry_bearish', []),
            'entry_bullish1': self.signals.get('entry_bullish1', []),
            'entry_bearish1': self.signals.get('entry_bearish1', []),
            'group3': self.signals.get('group3', [])
        }
        
        for category, signals in all_categories.items():
            signal_list = [s.lower().strip() for s in signals]
            if signal_lower in signal_list:
                return True, category
                
        return False, None