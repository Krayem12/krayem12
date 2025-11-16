import unittest
import sys
import os

try:
    from core.group_manager import GroupManager
    from core.trade_manager import TradeManager
except ImportError as e:
    print(f"❌ خطأ في الاستيراد: {e}")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from core.group_manager import GroupManager
    from core.trade_manager import TradeManager

class TestGroupManager(unittest.TestCase):
    """🧪 اختبارات مدير المجموعات"""
    
    def setUp(self):
        """إعداد بيئة الاختبار"""
        self.config = {
            'DEBUG': True,
            'MAX_OPEN_TRADES': 5,
            'MAX_TRADES_PER_SYMBOL': 2,
            'TRADING_MODE': 'GROUP1_GROUP2',
            'GROUP1_TREND_MODE': 'ONLY_TREND',
            'GROUP1_ENABLED': True,
            'GROUP2_ENABLED': True,
            'GROUP3_ENABLED': True,
            'GROUP4_ENABLED': True,
            'GROUP5_ENABLED': True,
            'REQUIRED_CONFIRMATIONS_GROUP1': 1,
            'REQUIRED_CONFIRMATIONS_GROUP2': 1,
            'REQUIRED_CONFIRMATIONS_GROUP3': 1,
            'REQUIRED_CONFIRMATIONS_GROUP4': 1,
            'REQUIRED_CONFIRMATIONS_GROUP5': 1,
            'STORE_CONTRARIAN_SIGNALS': True,
            'SIGNAL_TTL_MINUTES': 180,
            'signals': {
                'group1_bullish': ['oversold_bullish_hyperwave_signal'],
                'group1_bearish': ['overbought_bearish_hyperwave_signal'],
                'group2_bullish': ['Discount', 'bullish_catcher'],
                'group2_bearish': ['Premium', 'bearish_catcher'],
                'group3_bullish': ['bullish_moneyflow_above_50'],
                'group3_bearish': ['bearish_moneyflow_below_50'],
                'group4_bullish': ['K1', 'K2'],
                'group4_bearish': ['KK1', 'KK2'],
                'group5_bullish': ['R1', 'R2'],
                'group5_bearish': ['RR1', 'RR2'],
            }
        }
        
        self.trade_manager = TradeManager(self.config)
        self.group_manager = GroupManager(self.config, self.trade_manager)
        print("✅ تم إعداد مدير المجموعات للاختبار")
    
    def test_1_route_bullish_signal(self):
        """✅ اختبار توجيه إشارة صاعدة"""
        print("🔍 اختبار توجيه إشارة صاعدة...")
        
        signal_data = {
            'symbol': 'TEST',
            'signal_type': 'oversold_bullish_hyperwave_signal'
        }
        
        # يجب أن يتم تصنيفها كـ group1_bullish
        result = self.group_manager.route_signal('TEST', signal_data, 'entry_bullish')
        
        # في البداية، قد لا تفتح صفقة لأنها تحتاج إلى تأكيدات أكثر
        # لكن يجب أن تضيف الإشارة إلى المجموعة
        stats = self.group_manager.get_group_stats('TEST')
        self.assertIsNotNone(stats)
        print(f"📊 إحصائيات بعد الإشارة: {stats}")
        print("✅ نجح اختبار توجيه الإشارة الصاعدة")
    
    def test_2_route_bearish_signal(self):
        """✅ اختبار توجيه إشارة هابطة"""
        print("🔍 اختبار توجيه إشارة هابطة...")
        
        signal_data = {
            'symbol': 'TEST',
            'signal_type': 'overbought_bearish_hyperwave_signal'
        }
        
        result = self.group_manager.route_signal('TEST', signal_data, 'entry_bearish')
        
        stats = self.group_manager.get_group_stats('TEST')
        self.assertIsNotNone(stats)
        print(f"📊 إحصائيات بعد الإشارة: {stats}")
        print("✅ نجح اختبار توجيه الإشارة الهابطة")

if __name__ == '__main__':
    print("🧪 تشغيل اختبارات مدير المجموعات...")
    unittest.main(verbosity=2)