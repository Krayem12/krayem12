#!/usr/bin/env python3
from core.trading_system import TradingSystem

if __name__ == '__main__':
    print("🚀 Starting Trading System with COMPLETE METHOD IMPLEMENTATION + GROUP3...")
    system = TradingSystem()
    print(f"🌐 Server running on port {system.port}")
    system.app.run(host='0.0.0.0', port=system.port, debug=False)
else:
    system = TradingSystem()
    app = system.app