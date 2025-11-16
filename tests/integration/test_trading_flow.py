import unittest
import sys
import os

try:
    from core.trading_system import TradingSystem
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from core.trading_system import TradingSystem

class TestTradingFlow(unittest.TestCase):
    """🧪 اختبارات دورة التداول الكاملة"""
    
    def setUp(self):
        """إعداد نظام تداول كامل للاختبار"""
        self.system = TradingSystem()
        # تعطيل الإشعارات للاختبار
        self.system.config['TELEGRAM_ENABLED'] = False
        self.system.config['EXTERNAL_SERVER_ENABLED'] = False
        print("✅ تم إعداد نظام التداول للاختبار")
    
    def test_1_system_initialization(self):
        """✅ اختبار تهيئة النظام"""
        print("🔍 اختبار تهيئة النظام...")
        self.assertIsNotNone(self.system.config)
        self.assertIsNotNone(self.system.signal_processor)
        self.assertIsNotNone(self.system.trade_manager)
        self.assertIsNotNone(self.system.group_manager)
        print("✅ نجح اختبار تهيئة النظام")
    
    def test_2_webhook_integration(self):
        """✅ اختبار تكامل الويب هووك"""
        print("🔍 اختبار تكامل الويب هووك...")
        
        # محاكاة طلب ويب هووك
        with self.system.app.test_client() as client:
            response = client.post('/webhook', json={
                'ticker': 'INT_TEST',
                'signal': 'bullish_tracer'
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('status', data)
            print("✅ نجح اختبار تكامل الويب هووك")

if __name__ == '__main__':
    print("🧪 تشغيل اختبارات دورة التداول...")
    unittest.main(verbosity=2)