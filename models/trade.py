from datetime import datetime
import uuid

class Trade:
    """نموذج بيانات الصفقة"""
    
    def __init__(self, ticker, direction, signal_type, strategy_type):
        self.trade_id = str(uuid.uuid4())
        self.ticker = ticker
        self.direction = direction
        self.signal_type = signal_type
        self.strategy_type = strategy_type
        self.entry_time = datetime.now().isoformat()
        self.status = 'OPEN'
        self.confirmation_count = 1
        self.confirmed_signals = [signal_type]
        
    def to_dict(self):
        """تحويل النموذج إلى dictionary"""
        return {
            'trade_id': self.trade_id,
            'ticker': self.ticker,
            'direction': self.direction,
            'signal_type': self.signal_type,
            'entry_time': self.entry_time,
            'status': self.status,
            'strategy_type': self.strategy_type,
            'confirmation_count': self.confirmation_count,
            'confirmed_signals': self.confirmed_signals
        }
    
    def close(self, exit_signal=None):
        """إغلاق الصفقة"""
        self.status = 'CLOSED'
        self.exit_time = datetime.now().isoformat()
        self.exit_signal = exit_signal