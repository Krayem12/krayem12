import schedule
import threading
import time
from flask import Flask
from datetime import datetime

from config.config_manager import ConfigManager
from core.signal_processor import SignalProcessor
from core.trade_manager import TradeManager
from core.group_manager import GroupManager
from core.webhook_handler import WebhookHandler
from notifications.notification_manager import NotificationManager
from maintenance.cleanup_manager import CleanupManager

class TradingSystem:
    """Trading System with NEW STRATEGY IMPLEMENTATION"""

    def __init__(self):
        print("🚀 Starting Trading System with NEW STRATEGY...")
        try:
            self.setup_managers()
            self.setup_flask()
            self.setup_scheduler()
            self.display_system_info()
            print("✅ System initialized successfully")
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            raise

    def setup_managers(self):
        """Setup all manager classes"""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.signals = self.config_manager.signals
        self.keywords = self.config_manager.keywords
        self.port = self.config_manager.port

        # Initialize core managers
        self.signal_processor = SignalProcessor(self.config, self.signals, self.keywords)
        self.trade_manager = TradeManager(self.config)
        
        # 🎯 NEW: Pass trade_manager to group_manager
        self.group_manager = GroupManager(self.config, self.trade_manager)
        
        self.notification_manager = NotificationManager(self.config)
        self.cleanup_manager = CleanupManager(
            self.config, 
            self.trade_manager, 
            self.group_manager,
            self.notification_manager
        )
        
        self.webhook_handler = WebhookHandler(
            self.config,
            self.signal_processor,
            self.group_manager,
            self.trade_manager,
            self.notification_manager,
            self.cleanup_manager
        )

    def setup_flask(self):
        """Setup Flask app with routes"""
        self.app = Flask(__name__)
        
        # Register routes from webhook handler
        self.webhook_handler.register_routes(self.app)
        
        # Additional system routes
        @self.app.route('/status')
        def status():
            return self.get_system_status()

    def setup_scheduler(self):
        """Setup daily cleanup scheduler"""
        self.cleanup_manager.setup_scheduler()

    def display_system_info(self):
        """Display system information"""
        self.config_manager.display_config()
        self.display_loaded_signals()

    def display_loaded_signals(self):
        """Display loaded signals information"""
        print("\n📊 Loaded Signals Summary:")
        total_signals = 0
        for category, signals in self.signals.items():
            print(f"   📁 {category}: {len(signals)} signals")
            total_signals += len(signals)

        print(f"\n📈 Total signals loaded: {total_signals}")
        
        # 🎯 NEW: Display strategy information
        print(f"\n🎯 Active Trading Strategy: {self.config['TRADING_MODE']}")
        print(f"   • Group1 Trend Mode: {self.config['GROUP1_TREND_MODE']}")
        print(f"   • Group2 Enabled: {'✅ YES' if self.config['GROUP2_ENABLED'] else '❌ NO'}")
        print(f"   • Group3 Enabled: {'✅ YES' if self.config['GROUP3_ENABLED'] else '❌ NO'}")

    def get_system_status(self):
        """Get system status"""
        return {
            "status": "active",
            "version": "10.0_new_strategy",
            "timestamp": datetime.now().isoformat(),
            "port": self.port,
            "trading_mode": self.config['TRADING_MODE'],
            "group1_trend_mode": self.config['GROUP1_TREND_MODE'],
            "group2_enabled": self.config['GROUP2_ENABLED'],
            "group3_enabled": self.config['GROUP3_ENABLED']
        }