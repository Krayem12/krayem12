# tests/integration/test_full_trading_cycle.py
import pytest
from core.trading_system import TradingSystem

class TestFullTradingCycle:
    @pytest.fixture
    def trading_system(self):
        """نظام تداول كامل للاختبار"""
        system = TradingSystem()
        system.config['TELEGRAM_ENABLED'] = False  # تعطيل الإشعارات
        return system
    
    def test_signal_to_trade_flow(self, trading_system):
        """اختبار دورة كاملة من الإشارة إلى الصفقة"""
        # إرسال إشارة اتجاه صاعد
        trend_signal = {
            'symbol': 'INTEGRATION_TEST',
            'signal_type': 'bullish_tracer',
            'timestamp': datetime.now().isoformat()
        }
        
        # معالجة الإشارة
        classification = trading_system.signal_processor.classify_signal(trend_signal)
        assert classification == 'trend'
        
        # تحديث الاتجاه
        should_report, old_trend = trading_system.trade_manager.update_trend(
            'INTEGRATION_TEST', classification, trend_signal
        )
        assert should_report == True
        
        # إرسال إشارة دخول
        entry_signal = {
            'symbol': 'INTEGRATION_TEST', 
            'signal_type': 'oversold_bullish_hyperwave_signal',
            'timestamp': datetime.now().isoformat()
        }
        
        entry_classification = trading_system.signal_processor.classify_signal(entry_signal)
        assert entry_classification == 'entry_bullish'
        
        # توجيه الإشارة وفتح الصفقة
        trades = trading_system.group_manager.route_signal(
            'INTEGRATION_TEST', entry_signal, entry_classification
        )
        
        # التحقق من فتح الصفقة
        assert len(trades) > 0
        assert trades[0]['symbol'] == 'INTEGRATION_TEST'
        assert trades[0]['direction'] == 'buy'