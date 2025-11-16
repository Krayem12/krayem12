import unittest
import sys
import os

# إضافة مسار المشروع لاستيراد الوحدات
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.signal_processor import SignalProcessor

class TestSignalProcessor(unittest.TestCase):
    
    def setUp(self):
        """إعداد بيئة الاختبار"""
        self.config = {
            'DEBUG': True,
            'MAX_OPEN_TRADES': 5,
        }
        
        self.signals = {
            'trend': ['bullish_tracer', 'bearish_tracer'],
            'entry_bullish': ['oversold_bullish_hyperwave_signal', 'regular_bullish_hyperwave_signal'],
            'entry_bearish': ['overbought_bearish_hyperwave_signal', 'regular_bearish_hyperwave_signal'],
            'exit': ['exit_buy', 'exit_sell'],
        }
        
        self.keywords = {}
        self.processor = SignalProcessor(self.config, self.signals, self.keywords)
    
    def test_bullish_trend_signal(self):
        """اختبار تصنيف إشارة الاتجاه الصاعد"""
        signal_data = {'signal_type': 'bullish_tracer'}
        result = self.processor.classify_signal(signal_data)
        self.assertEqual(result, 'trend')
    
    def test_bearish_trend_signal(self):
        """اختبار تصنيف إشارة الاتجاه الهابط"""
        signal_data = {'signal_type': 'bearish_tracer'}
        result = self.processor.classify_signal(signal_data)
        self.assertEqual(result, 'trend')
    
    def test_bullish_entry_signal(self):
        """اختبار تصنيف إشارة الدخول الصاعدة"""
        signal_data = {'signal_type': 'oversold_bullish_hyperwave_signal'}
        result = self.processor.classify_signal(signal_data)
        self.assertEqual(result, 'entry_bullish')
    
    def test_unknown_signal(self):
        """اختبار تصنيف إشارة غير معروفة"""
        signal_data = {'signal_type': 'unknown_signal_123'}
        result = self.processor.classify_signal(signal_data)
        self.assertEqual(result, 'unknown')
    
    def test_empty_signal_data(self):
        """اختبار بيانات إشارة فارغة"""
        signal_data = {}
        result = self.processor.classify_signal(signal_data)
        self.assertEqual(result, 'unknown')

if __name__ == '__main__':
    unittest.main()