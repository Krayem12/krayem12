import re
from datetime import datetime

class Signal:
    """نموذج بيانات الإشارة"""
    
    def __init__(self, raw_signal):
        self.raw_signal = raw_signal
        self.ticker = "UNKNOWN"
        self.signal_type = "UNKNOWN"
        self.original_signal = raw_signal
        self.timestamp = datetime.now()
        self.category = "unknown"
        
        self.parse_signal()
    
    def parse_signal(self):
        """تحليل الإشارة النصية"""
        text = (self.raw_signal or "").strip()
        if not text:
            return

        try:
            match = re.match(r'Ticker\s*:\s*(.+?)\s+Signal\s*:\s*(.+)', text)
            if match:
                ticker, signal_type = match.groups()
                self.ticker = ticker.strip().upper()
                self.signal_type = signal_type.strip()
                return

            match = re.match(r'([A-Za-z0-9]+)\s+(.+)', text)
            if match:
                ticker, signal_type = match.groups()
                self.ticker = ticker.strip().upper()
                self.signal_type = signal_type.strip()
                return

            self.signal_type = text

        except Exception as e:
            print(f"💥 Parse error: {e}")
    
    def to_dict(self):
        """تحويل النموذج إلى dictionary"""
        return {
            'ticker': self.ticker,
            'signal_type': self.signal_type,
            'original_signal': self.original_signal,
            'timestamp': self.timestamp,
            'category': self.category
        }