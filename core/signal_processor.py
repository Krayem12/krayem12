# core/signal_processor.py
import re
import hashlib
from datetime import datetime

class SignalProcessor:
    """Process and classify trading signals"""

    def __init__(self, config, signals, keywords):
        self.config = config
        self.signals = signals
        self.keywords = keywords
        self.signal_index = {}
        self.setup_signal_index()

    def setup_signal_index(self):
        """Optimized signal lookup index for better performance"""
        for category, signal_list in self.signals.items():
            for signal in signal_list:
                normalized = signal.lower().strip().replace(' ', '')
                self.signal_index[normalized] = category
                self.signal_index[signal] = category

    def extract_signal(self, request):
        """Extract signal from request with IMPROVED error handling"""
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
        """Optimized signal classification with IMPROVED TREND detection"""
        if not signal_data or 'signal_type' not in signal_data:
            return 'unknown'

        signal_type = signal_data['signal_type']
        signal_lower = signal_type.lower()
        
        # HIGHEST PRIORITY: Check for trend signals FIRST - EXACT MATCH ONLY
        trend_signals = self.signals.get('trend', [])
        for trend_signal in trend_signals:
            trend_signal_lower = trend_signal.lower()
            # التطابق التام فقط لإشارات الاتجاه
            if trend_signal_lower == signal_lower:
                print(f"🎯 تم التصنيف كإشارة اتجاه: '{signal_type}' يطابق إشارة الاتجاه '{trend_signal}'")
                return 'trend'
        
        # Check for trend confirmation signals - EXACT MATCH ONLY
        trend_confirm_signals = self.signals.get('trend_confirm', [])
        for trend_confirm_signal in trend_confirm_signals:
            trend_confirm_lower = trend_confirm_signal.lower()
            if trend_confirm_lower == signal_lower:
                print(f"🎯 تم التصنيف كتأكيد اتجاه: '{signal_type}' يطابق إشارة تأكيد الاتجاه '{trend_confirm_signal}'")
                return 'trend_confirm'

        # Then check for exit signals
        exit_signals = self.signals.get('exit', [])
        for exit_signal in exit_signals:
            if exit_signal.lower() in signal_lower:
                print(f"🎯 تم التصنيف كإشارة خروج: '{signal_type}'")
                return 'exit'
                
        if any(kw in signal_lower for kw in self.keywords['exit']):
            print(f"🎯 تم التصنيف كإشارة خروج: '{signal_type}'")
            return 'exit'

        # Then check for entry signals - ONLY if not already classified as trend
        # Check group1 signals first (exact matches)
        group1_bullish_signals = self.signals.get('entry_bullish', [])
        group1_bearish_signals = self.signals.get('entry_bearish', [])
        
        for signal in group1_bullish_signals:
            if signal.lower() in signal_lower:
                print(f"🎯 تم التصنيف كدخول صاعد (مجموعة1): '{signal_type}'")
                return 'entry_bullish'
                
        for signal in group1_bearish_signals:
            if signal.lower() in signal_lower:
                print(f"🎯 تم التصنيف كدخول هابط (مجموعة1): '{signal_type}'")
                return 'entry_bearish'

        # Check group2 signals
        group2_bullish_signals = self.signals.get('entry_bullish1', [])
        group2_bearish_signals = self.signals.get('entry_bearish1', [])
        
        for signal in group2_bullish_signals:
            if signal.lower() in signal_lower:
                print(f"🎯 تم التصنيف كدخول صاعد (مجموعة2): '{signal_type}'")
                return 'entry_bullish1'
                
        for signal in group2_bearish_signals:
            if signal.lower() in signal_lower:
                print(f"🎯 تم التصنيف كدخول هابط (مجموعة2): '{signal_type}'")
                return 'entry_bearish1'

        # Check group3 signals
        if self.config['GROUP3_ENABLED']:
            group3_signals = self.signals.get('group3', [])
            for group3_signal in group3_signals:
                if group3_signal.lower() in signal_lower:
                    print(f"🎯 تم التصنيف كمجموعة ثالثة: '{signal_type}' يطابق إشارة المجموعة الثالثة '{group3_signal}'")
                    return 'group3'

        # Finally, check general keywords only if no exact matches found
        if any(kw in signal_lower for kw in self.keywords['bullish']):
            print(f"🎯 تم التصنيف كدخول صاعد (كلمات مفتاحية): '{signal_type}'")
            return 'entry_bullish'

        if any(kw in signal_lower for kw in self.keywords['bearish']):
            print(f"🎯 تم التصنيف كدخول هابط (كلمات مفتاحية): '{signal_type}'")
            return 'entry_bearish'

        print(f"⚠️ نوع إشارة غير معروف: '{signal_type}'")
        return 'unknown'