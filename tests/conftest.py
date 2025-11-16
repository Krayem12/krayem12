# tests/conftest.py
import pytest
import sys
import os
from datetime import datetime

# إضافة مسار المشروع إلى Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

@pytest.fixture
def sample_config():
    """توفير إعدادات اختبارية"""
    return {
        'DEBUG': True,
        'MAX_OPEN_TRADES': 5,
        'MAX_TRADES_PER_SYMBOL': 2,
        'TRADING_MODE': 'GROUP1_GROUP2',
        'GROUP1_TREND_MODE': 'ONLY_TREND',
        'TELEGRAM_ENABLED': False,  # تعطيل في الاختبارات
        'EXTERNAL_SERVER_ENABLED': False
    }

@pytest.fixture
def sample_signals():
    """إشارات اختبارية"""
    return {
        'trend': ['bullish_tracer', 'bearish_tracer'],
        'entry_bullish': ['oversold_bullish_hyperwave_signal'],
        'entry_bearish': ['overbought_bearish_hyperwave_signal']
    }

@pytest.fixture
def mock_trade_manager(sample_config):
    """مدير صفقات وهمي للاختبار"""
    from core.trade_manager import TradeManager
    return TradeManager(sample_config)