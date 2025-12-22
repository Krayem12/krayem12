# core/__init__.py
"""
📦 حزمة النظام الأساسي للتداول
"""

__version__ = "1.2.0"  # ✅ تحديث الإصدار
__author__ = "Trading System Team"

# تصدير الفئات الرئيسية
from .trade_manager import TradeManager
from .group_manager import GroupManager
from .signal_processor import SignalProcessor
from .webhook_handler import WebhookHandler
from .redis_manager import RedisManager
from .group_mapper import GroupMapper  # ✅ إضافة الجديدة
from .debug_guard import DebugGuard    # ✅ إضافة الجديدة

__all__ = [
    'TradeManager',
    'GroupManager',
    'SignalProcessor',
    'WebhookHandler',
    'RedisManager',
    'GroupMapper',    # ✅ إضافة الجديدة
    'DebugGuard',     # ✅ إضافة الجديدة
]
