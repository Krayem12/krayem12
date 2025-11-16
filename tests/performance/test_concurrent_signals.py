# tests/performance/test_concurrent_signals.py
import threading
import time
import pytest

class TestConcurrentSignals:
    def test_multiple_concurrent_signals(self, trading_system):
        """اختبار معالجة إشارات متزامنة"""
        results = []
        errors = []
        
        def process_signal(symbol, signal_type):
            try:
                signal_data = {
                    'symbol': symbol,
                    'signal_type': signal_type,
                    'timestamp': datetime.now().isoformat()
                }
                classification = trading_system.signal_processor.classify_signal(signal_data)
                results.append((symbol, signal_type, classification))
            except Exception as e:
                errors.append(str(e))
        
        # إنشاء 10 خيوط معالجة متزامنة
        threads = []
        for i in range(10):
            symbol = f"SYMBOL_{i}"
            thread = threading.Thread(
                target=process_signal, 
                args=(symbol, 'bullish_tracer')
            )
            threads.append(thread)
        
        # بدء جميع الخيوط
        for thread in threads:
            thread.start()
        
        # انتظار انتهاء جميع الخيوط
        for thread in threads:
            thread.join()
        
        # التحقق من النتائج
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result[2] == 'trend' for result in results)