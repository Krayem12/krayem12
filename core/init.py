"""
📦 حزمة النظام الأساسي للتداول
"""

__version__ = "1.0.0"
__author__ = "Trading System Team"

# تصدير الفئات الرئيسية
from .trade_manager import TradeManager
from .group_manager import GroupManager
from .signal_processor import SignalProcessor
from .webhook_handler import WebhookHandler
from .redis_manager import RedisManager

__all__ = [
    'TradeManager',
    'GroupManager',
    'SignalProcessor',
    'WebhookHandler',
    'RedisManager'
]
