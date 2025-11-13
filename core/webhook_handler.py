# core/webhook_handler.py
import json
import re
import logging
from flask import request, jsonify
from typing import Dict, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookHandler:
    """🎯 معالج الويب هووك مع تحسينات الأداء ومعالجة الأخطاء"""

    def __init__(self, config, signal_processor, group_manager, trade_manager, notification_manager, cleanup_manager):
        self.config = config
        self.signal_processor = signal_processor
        self.group_manager = group_manager
        self.trade_manager = trade_manager
        self.notification_manager = notification_manager
        self.cleanup_manager = cleanup_manager
        self._error_log = []

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append(full_error)

    def register_routes(self, app) -> None:
        """تسجيل المسارات"""
        app.add_url_rule("/webhook", view_func=self.handle_webhook, methods=["POST"])
        logger.info("🔗 تم تسجيل مسار الويب هووك")

    def handle_webhook(self):
        """معالجة طلبات الويب هووك مع تحسينات الأداء"""
        logger.debug("📥 طلب واردة جديدة")
        
        try:
            raw_data = request.data.decode('utf-8').strip()
            signal_data = self._parse_incoming_request(raw_data)
            
            if not signal_data:
                return jsonify({"error": "Invalid signal data"}), 400

            # معالجة الإشارة
            return self._process_signal(signal_data)

        except Exception as e:
            self._handle_error("💥 خطأ في معالجة الويب هووك", e)
            return jsonify({"error": "Internal server error"}), 500

    def _parse_incoming_request(self, raw_data: str) -> Optional[Dict]:
        """تحليل الطلب الوارد"""
        content_type = (request.headers.get('Content-Type') or '').lower()
        
        if 'application/json' in content_type:
            return self._parse_json_request(raw_data)
        else:
            return self._parse_plaintext_request(raw_data)

    def _parse_json_request(self, raw_data: str) -> Optional[Dict]:
        """تحليل طلب JSON"""
        try:
            if not raw_data.strip():
                return None
                
            data = json.loads(raw_data)
            symbol = data.get('ticker') or data.get('symbol') or 'UNKNOWN'
            signal_type = data.get('signal') or data.get('action') or 'UNKNOWN'
            
            if symbol == 'UNKNOWN' or signal_type == 'UNKNOWN':
                return None
                
            return {
                'symbol': symbol.upper().strip(),
                'signal_type': signal_type.strip(),
                'timestamp': datetime.now().isoformat()
            }
            
        except json.JSONDecodeError:
            return self._parse_plaintext_request(raw_data)
        except Exception as e:
            self._handle_error("❌ خطأ في تحليل JSON", e)
            return None

    def _parse_plaintext_request(self, raw_data: str) -> Optional[Dict]:
        """تحليل طلب نصي"""
        try:
            symbol, signal_type = self._extract_from_plaintext(raw_data)
            if not symbol or not signal_type:
                return None
                
            return {
                'symbol': symbol.upper().strip(),
                'signal_type': signal_type.strip(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self._handle_error("❌ خطأ في تحليل النص", e)
            return None

    def _extract_from_plaintext(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """استخراج الرمز والإشارة من النص"""
        # نمط Ticker: SYMBOL Signal: SIGNAL
        match = re.search(r'(?i)ticker\s*:\s*([A-Z0-9]+).*?signal\s*:\s*([A-Za-z0-9_ ]+)', text)
        if match:
            return match.group(1), match.group(2)

        # نمط SYMBOL SIGNAL
        match = re.match(r'([A-Z0-9]+)\s+([A-Za-z0-9_ ]+)', text)
        if match:
            return match.group(1), match.group(2)

        return None, None

    def _process_signal(self, signal_data: Dict):
        """معالجة الإشارة"""
        classification = self.signal_processor.safe_classify_signal(signal_data)
        
        logger.debug(f"🎯 تصنيف الإشارة: {signal_data['signal_type']} -> {classification}")
        
        if classification == 'unknown':
            return jsonify({"error": f"Unknown signal: {signal_data['signal_type']}"}), 400

        # 🆕 NEW: تحسين توجيه الإشارات ليشمل جميع أنواع المجموعات
        if classification in ['trend', 'trend_confirm']:
            return self._handle_trend_signal(signal_data, classification)
        elif classification == 'exit':
            return self._handle_exit_signal(signal_data)
        elif classification in ['entry_bullish', 'entry_bearish', 'entry_bullish1', 
                              'entry_bearish1', 'group3', 'group4', 'group5',
                              'group3_bullish', 'group3_bearish',  # 🆕 إضافة group3
                              'group4_bullish', 'group4_bearish', 'group5_bullish', 'group5_bearish']:
            return self._handle_entry_signal(signal_data, classification)
        else:
            logger.error(f"❌ تصنيف غير معالج: {classification} للإشارة: {signal_data['signal_type']}")
            return jsonify({"error": f"Unhandled classification: {classification}"}), 400

    def _handle_trend_signal(self, signal_data: Dict, classification: str):
        """معالجة إشارات الاتجاه"""
        symbol = signal_data['symbol']
        
        should_report, old_trend = self.trade_manager.update_trend(symbol, classification, signal_data)
        
        if should_report and self.notification_manager.should_send_message('trend'):
            self._send_trend_notification(signal_data, self.trade_manager.current_trend.get(symbol), old_trend)
        
        return jsonify({
            "status": "trend_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trend_changed": should_report
        })

    def _handle_exit_signal(self, signal_data: Dict):
        """معالجة إشارات الخروج"""
        symbol = signal_data['symbol']
        self.trade_manager.handle_exit_signal(symbol, signal_data['signal_type'])
        
        if self.notification_manager.should_send_message('exit'):
            self._send_exit_notification(signal_data)
        
        return jsonify({"status": "exit_processed", "symbol": symbol})

    def _handle_entry_signal(self, signal_data: Dict, classification: str):
        """معالجة إشارات الدخول"""
        symbol = signal_data['symbol']
        
        # 🆕 NEW: تحسين تسجيل المعلومات للتصحيح
        logger.debug(f"🎯 معالجة إشارة دخول: {symbol} -> {classification}")
        
        trade_results = self.group_manager.route_signal(symbol, signal_data, classification)
        
        # 🆕 NEW: تسجيل تفاصيل النتائج
        logger.debug(f"📊 نتائج التداول لـ {symbol}: {len(trade_results)} صفقات")
        
        if trade_results and self.notification_manager.should_send_message('entry'):
            self._send_entry_notifications(signal_data, trade_results)
        
        return jsonify({
            "status": "entry_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trades_opened": len(trade_results)
        })

    def _send_trend_notification(self, signal_data: Dict, new_trend: str, old_trend: Optional[str]):
        """إرسال إشعار الاتجاه"""
        try:
            from notifications.message_formatter import MessageFormatter
            message = MessageFormatter.format_trend_message(signal_data, new_trend, old_trend or "UNKNOWN")
            self.notification_manager.send_notifications(message, 'trend')
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الاتجاه", e)

    def _send_exit_notification(self, signal_data: Dict):
        """إرسال إشعار الخروج"""
        try:
            from notifications.message_formatter import MessageFormatter
            symbol = signal_data['symbol']
            active_count = self.trade_manager.get_active_trades_count(symbol)
            total_active = self.trade_manager.get_active_trades_count()
            
            message = MessageFormatter.format_exit_message(symbol, signal_data['signal_type'], 
                                                         active_count, total_active, self.config)
            self.notification_manager.send_notifications(message, 'exit')
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الخروج", e)

    def _send_entry_notifications(self, signal_data: Dict, trade_results: List[Dict]):
        """إرسال إشعارات الدخول"""
        try:
            from notifications.message_formatter import MessageFormatter
            
            for trade in trade_results:
                symbol = trade['symbol']
                current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                active_count = self.trade_manager.get_active_trades_count(symbol)
                total_active = self.trade_manager.get_active_trades_count()
                
                message = MessageFormatter.format_detailed_entry_message(
                    symbol=symbol,
                    signal_type=signal_data['signal_type'],
                    direction=trade['direction'],
                    current_trend=current_trend,
                    strategy_type=trade['strategy_type'],
                    group1_signals=trade.get('group1_signals', []),
                    group2_signals=trade.get('group2_signals', []),
                    group3_signals=trade.get('group3_signals', []),
                    group4_signals=trade.get('group4_signals', []),
                    group5_signals=trade.get('group5_signals', []),
                    active_for_symbol=active_count,
                    total_active=total_active,
                    config=self.config,
                    mode_key=trade.get('mode_key', 'TRADING_MODE')
                )
                self.notification_manager.send_notifications(message, 'entry')
                
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعارات الدخول", e)

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()