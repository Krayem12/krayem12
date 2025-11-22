import json
import re
import logging
from flask import request, jsonify
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

class WebhookHandler:
    """🎯 معالج الويب هووك مع إصلاحات شاملة"""

    def __init__(self, config, signal_processor, group_manager, trade_manager, notification_manager, cleanup_manager):
        self.config = config
        self.signal_processor = signal_processor
        self.group_manager = group_manager
        self.trade_manager = trade_manager
        self.notification_manager = notification_manager
        self.cleanup_manager = cleanup_manager
        self._error_log = []
        
        logger.info("🎯 WebhookHandler المصحح جاهز")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None, 
                     extra_data: Optional[Dict] = None) -> None:
        """🎯 معالجة الأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        if extra_data:
            full_error += f" | Extra: {extra_data}"
        logger.error(full_error)
        
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error': full_error
        }
        self._error_log.append(error_entry)

    def register_routes(self, app) -> None:
        """تسجيل المسارات"""
        app.add_url_rule("/webhook", view_func=self.handle_webhook, methods=["POST"])
        app.add_url_rule("/health", view_func=self.health_check, methods=["GET"])
        app.add_url_rule("/debug/trend/<symbol>", view_func=self.debug_trend, methods=["GET"])
        app.add_url_rule("/debug/force_trend/<symbol>/<direction>", view_func=self.debug_force_trend, methods=["POST"])
        app.add_url_rule("/debug/force_trade/<symbol>/<direction>", view_func=self.debug_force_trade, methods=["POST"])
        app.add_url_rule("/debug/clear_trend/<symbol>", view_func=self.debug_clear_trend, methods=["POST"])
        
        logger.info("🔗 تم تسجيل مسارات الويب هووك والتصحيح")

    def health_check(self):
        """فحص صحة النظام"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "12.1_fixed_parsing_and_groups",
            "system_metrics": {
                "active_trades": self.trade_manager.get_active_trades_count(),
                "pending_signals": sum(len(signals) for symbol_data in self.group_manager.pending_signals.values() 
                                     for signals in symbol_data.values() if isinstance(signals, deque)),
                "error_count": len(self._error_log),
                "current_trends": len(self.trade_manager.current_trend)
            }
        })

    def debug_trend(self, symbol):
        """🔧 تصحيح حالة الاتجاه لرمز معين"""
        try:
            trend_status = self.trade_manager.get_trend_status(symbol)
            trend_history = self.trade_manager.get_trend_history(symbol, 10)
            group_stats = self.group_manager.get_group_stats(symbol)
            
            return jsonify({
                "symbol": symbol,
                "trend_status": trend_status,
                "trend_history": trend_history,
                "group_stats": group_stats,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def debug_force_trend(self, symbol, direction):
        """🔧 تغيير اتجاه قسري"""
        try:
            if direction not in ['bullish', 'bearish']:
                return jsonify({"error": "الاتجاه يجب أن يكون 'bullish' أو 'bearish'"}), 400
            
            success = self.trade_manager.force_trend_change(symbol, direction)
            
            return jsonify({
                "success": success,
                "symbol": symbol,
                "new_trend": direction,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def debug_force_trade(self, symbol, direction):
        """🔧 فتح صفقة قسرية"""
        try:
            if direction not in ['buy', 'sell']:
                return jsonify({"error": "الاتجاه يجب أن يكون 'buy' أو 'sell'"}), 400
            
            success = self.group_manager.force_open_trade(symbol, direction)
            
            return jsonify({
                "success": success,
                "symbol": symbol,
                "direction": direction,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def debug_clear_trend(self, symbol):
        """🔧 مسح بيانات الاتجاه"""
        try:
            success = self.trade_manager.clear_trend_data(symbol)
            
            return jsonify({
                "success": success,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def handle_webhook(self):
        """🎯 معالجة طلبات الويب هووك مع إصلاحات"""
        logger.info("📥 📥 📥 طلب ويب هووك واردة جديدة 📥 📥 📥")
        
        try:
            client_ip = request.remote_addr
            content_type = request.headers.get('Content-Type', '')
            content_length = request.headers.get('Content-Length', 0)
            user_agent = request.headers.get('User-Agent', '')
            
            logger.info(f"🌐 معلومات الطلب: IP={client_ip}, Content-Type={content_type}, Length={content_length}")
            
            raw_data = request.get_data(as_text=True)
            if not raw_data:
                logger.warning("⚠️ طلب فارغ - لا توجد بيانات")
                return jsonify({"error": "Empty request body"}), 400
            
            logger.info(f"📝 البيانات الواردة: {raw_data[:500]}{'...' if len(raw_data) > 500 else ''}")
            
            signal_data = self._parse_incoming_request(raw_data)
            
            if not signal_data:
                logger.error("❌ فشل تحليل بيانات الإشارة")
                return jsonify({"error": "Invalid signal data"}), 400

            logger.info(f"🎯 تم تحليل الإشارة: رمز={signal_data['symbol']}, نوع={signal_data['signal_type']}")

            result = self._process_signal(signal_data)
            logger.info(f"✅ تم معالجة الإشارة بنجاح")
            
            return result

        except Exception as e:
            error_msg = f"💥 خطأ في معالجة الويب هووك: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._handle_error(error_msg, e)
            return jsonify({"error": "Internal server error"}), 500

    def _parse_incoming_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل الطلب الوارد"""
        logger.debug("🔍 بدء تحليل الطلب الوارد...")
        
        content_type = (request.headers.get('Content-Type') or '').lower()
        
        if 'application/json' in content_type:
            logger.debug("📋 تحليل طلب JSON...")
            return self._parse_json_request(raw_data)
        else:
            logger.debug("📋 تحليل طلب نصي...")
            return self._parse_plaintext_request(raw_data)

    def _parse_json_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل طلب JSON"""
        try:
            if not raw_data or not raw_data.strip():
                logger.warning("⚠️ بيانات JSON فارغة")
                return None
                
            data = json.loads(raw_data)
            logger.debug(f"📊 بيانات JSON المحللة: {data}")
            
            symbol = data.get('ticker') or data.get('symbol') or 'UNKNOWN'
            signal_type = data.get('signal') or data.get('action') or data.get('type') or 'UNKNOWN'
            
            if symbol == 'UNKNOWN' or signal_type == 'UNKNOWN':
                logger.warning(f"⚠️ رمز أو إشارة غير معروفة: symbol={symbol}, signal={signal_type}")
                return None
                
            result = {
                'symbol': symbol.upper().strip(),
                'signal_type': signal_type.strip(),
                'timestamp': datetime.now().isoformat(),
                'raw_data': data
            }
            
            logger.info(f"✅ تم تحليل JSON: {symbol} -> {signal_type}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ خطأ في تحليل JSON، التحويل إلى نص: {e}")
            return self._parse_plaintext_request(raw_data)
        except Exception as e:
            self._handle_error("❌ خطأ في تحليل JSON", e, {'raw_data_preview': raw_data[:200]})
            return None

    def _parse_plaintext_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل طلب نصي"""
        try:
            logger.debug(f"🔍 تحليل النص الخام: {raw_data}")
            
            symbol, signal_type = self._extract_from_plaintext(raw_data)
            if not symbol or not signal_type:
                logger.warning(f"⚠️ فشل استخراج الرمز والإشارة من النص: {raw_data}")
                return None
                
            result = {
                'symbol': symbol.upper().strip(),
                'signal_type': signal_type.strip(),
                'timestamp': datetime.now().isoformat(),
                'raw_data': raw_data
            }
            
            logger.info(f"✅ تم تحليل النص: {symbol} -> {signal_type}")
            return result
            
        except Exception as e:
            self._handle_error("❌ خطأ في تحليل النص", e, {'raw_data_preview': raw_data[:200]})
            return None

    def _extract_from_plaintext(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """🎯 استخراج الرمز والإشارة من النص مع تحسينات"""
        try:
            logger.debug(f"🔍 استخراج من النص: '{text}'")
            
            text = text.strip()
            if not text:
                logger.warning("❌ نص الإشارة فارغ")
                return None, None

            # نمط Ticker: SYMBOL Signal: SIGNAL
            match = re.search(r'(?i)ticker\s*:\s*([A-Z0-9]+).*?signal\s*:\s*([A-Za-z0-9_ ]+)', text)
            if match:
                symbol, signal = match.group(1), match.group(2)
                logger.debug(f"✅ تم الاستخراج بنمط Ticker/Signal: {symbol} -> {signal}")
                return symbol, signal

            # نمط SYMBOL SIGNAL (تحسين)
            match = re.match(r'([A-Za-z0-9]+)\s+([A-Za-z0-9_ ]+)', text)
            if match:
                symbol, signal = match.group(1), match.group(2)
                logger.debug(f"✅ تم الاستخراج بنمط Symbol/Signal: {symbol} -> {signal}")
                return symbol, signal

            # نمط الإشارة فقط مع رمز افتراضي
            if text.strip():
                # محاولة استخراج الرمز من بداية النص
                words = text.split()
                if len(words) >= 2:
                    symbol = words[0]
                    signal = ' '.join(words[1:])
                    logger.debug(f"✅ تم الاستخراج بنمط الكلمات المتعددة: {symbol} -> {signal}")
                    return symbol, signal
                else:
                    logger.warning(f"⚠️ نص غير كافٍ: {text}")
                    return "UNKNOWN", text.strip()

            logger.warning("❌ فشل جميع أنماط الاستخراج")
            return None, None
            
        except Exception as e:
            self._handle_error("💥 خطأ في استخراج البيانات من النص", e)
            return None, None

    def _process_signal(self, signal_data: Dict):
        """🎯 معالجة الإشارة مع إصلاحات"""
        logger.info(f"🎯 بدء معالجة الإشارة: {signal_data['signal_type']} للرمز {signal_data['symbol']}")
        
        classification = self.signal_processor.safe_classify_signal(signal_data)
        
        logger.info(f"🎯 تصنيف الإشارة: {signal_data['signal_type']} -> {classification}")
        
        if classification == 'unknown':
            logger.warning(f"⚠️ إشارة غير معروفة: {signal_data['signal_type']}")
            self._handle_error("إشارة غير معروفة", None, {
                'signal_type': signal_data['signal_type'],
                'symbol': signal_data['symbol']
            })
            return jsonify({"error": f"Unknown signal: {signal_data['signal_type']}"}), 400

        try:
            if classification in ['trend', 'trend_confirm']:
                logger.info(f"📈 معالجة إشارة اتجاه: {classification}")
                return self._handle_trend_signal(signal_data, classification)
            elif classification == 'exit':
                logger.info(f"🚪 معالجة إشارة خروج: {signal_data['signal_type']}")
                return self._handle_exit_signal(signal_data)
            elif classification in ['entry_bullish', 'entry_bearish', 'entry_bullish1', 
                                  'entry_bearish1', 'group3', 'group4', 'group5',
                                  'group3_bullish', 'group3_bearish',
                                  'group4_bullish', 'group4_bearish', 'group5_bullish', 'group5_bearish']:
                logger.info(f"🚀 معالجة إشارة دخول: {classification}")
                return self._handle_entry_signal(signal_data, classification)
            else:
                logger.error(f"❌ تصنيف غير معالج: {classification} للإشارة: {signal_data['signal_type']}")
                self._handle_error("تصنيف غير معالج", None, {
                    'classification': classification,
                    'signal_type': signal_data['signal_type']
                })
                return jsonify({"error": f"Unhandled classification: {classification}"}), 400
                
        except Exception as e:
            error_msg = f"💥 خطأ في معالجة الإشارة المصنفة: {e}"
            logger.error(error_msg, exc_info=True)
            self._handle_error(error_msg, e, {
                'classification': classification,
                'signal_type': signal_data['signal_type'],
                'symbol': signal_data['symbol']
            })
            return jsonify({"error": "Signal processing error"}), 500

    def _handle_trend_signal(self, signal_data: Dict, classification: str):
        """🎯 معالجة إشارات الاتجاه مع إصلاحات"""
        symbol = signal_data['symbol']
        logger.info(f"📈 معالجة إشارة اتجاه لـ {symbol}: {signal_data['signal_type']}")
        
        should_report, old_trend, trend_signals = self.trade_manager.update_trend(symbol, classification, signal_data)
        
        logger.info(f"📊 نتيجة تحديث الاتجاه: {symbol} -> تغيير={should_report}, اتجاه قديم={old_trend}, عدد الإشارات={len(trend_signals)}")
        
        response_data = {
            "status": "trend_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trend_changed": should_report,
            "current_trend": self.trade_manager.current_trend.get(symbol, "UNKNOWN"),
            "old_trend": old_trend or "UNKNOWN",
            "signals_used": len(trend_signals),
            "signals_details": [{"signal_type": s['signal_type'], "direction": s['direction']} for s in trend_signals]
        }

        if should_report:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            logger.info(f"🔍 تحقق الإشعار - التليجرام: {telegram_enabled}, الخارجي: {external_enabled}")
            
            if telegram_enabled or external_enabled:
                self._send_trend_notification(signal_data, self.trade_manager.current_trend.get(symbol, "UNKNOWN"), old_trend, trend_signals)
            else:
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعار الاتجاه")
        
        return jsonify(response_data)

    def _handle_exit_signal(self, signal_data: Dict):
        """🎯 معالجة إشارات الخروج مع التحقق من وجود صفقات مفتوحة"""
        symbol = signal_data['symbol']
        logger.info(f"🚪 معالجة إشارة خروج لـ {symbol}: {signal_data['signal_type']}")
        
        # 🆕 الجديد: التحقق من وجود صفقات مفتوحة قبل معالجة إشارة الخروج
        active_trades_count = self.trade_manager.get_active_trades_count(symbol)
        
        if active_trades_count == 0:
            logger.info(f"🔕 لا توجد صفقات مفتوحة لـ {symbol} - تم تجاهل إشارة الخروج")
            return jsonify({
                "status": "exit_ignored", 
                "symbol": symbol,
                "signal_type": signal_data['signal_type'],
                "reason": "لا توجد صفقات مفتوحة للرمز",
                "active_trades": 0
            })
        
        # معالجة إشارة الخروج فقط إذا كانت هناك صفقات مفتوحة
        closed_trades = self.trade_manager.handle_exit_signal(symbol, signal_data['signal_type'])
        
        # 🆕 الجديد: التحقق من وجود صفقات مفتوحة بعد معالجة الخروج
        remaining_trades = self.trade_manager.get_active_trades_count(symbol)
        
        logger.info(f"📊 نتيجة معالجة الخروج: {symbol} -> تم إغلاق {closed_trades} صفقة، الصفقات المتبقية: {remaining_trades}")
        
        # 🆕 الجديد: إرسال إشعار الخروج فقط إذا كانت هناك صفقات تم إغلاقها بالفعل
        if closed_trades > 0 and self.notification_manager.should_send_message('exit'):
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if telegram_enabled or external_enabled:
                self._send_exit_notification(signal_data, closed_trades, remaining_trades)
            else:
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعار الخروج")
        
        return jsonify({
            "status": "exit_processed", 
            "symbol": symbol,
            "signal_type": signal_data['signal_type'],
            "trades_closed": closed_trades,
            "remaining_trades": remaining_trades
        })

    def _handle_entry_signal(self, signal_data: Dict, classification: str):
        """🎯 معالجة إشارات الدخول"""
        symbol = signal_data['symbol']
        logger.info(f"🚀 معالجة إشارة دخول لـ {symbol}: {classification} -> {signal_data['signal_type']}")
        
        trade_results = self.group_manager.route_signal(symbol, signal_data, classification)
        
        logger.info(f"📊 نتائج التداول لـ {symbol}: {len(trade_results)} صفقات مفتوحة")
        
        if trade_results and self.notification_manager.should_send_message('entry'):
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if telegram_enabled or external_enabled:
                self._send_entry_notifications(signal_data, trade_results)
            else:
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعارات الدخول")
        
        return jsonify({
            "status": "entry_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trades_opened": len(trade_results),
            "trade_details": trade_results
        })

    def _send_trend_notification(self, signal_data: Dict, new_trend: str, old_trend: Optional[str], trend_signals: List[Dict]):
        """🎯 إرسال إشعار الاتجاه مع التحسينات"""
        try:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال")
                return
                
            # ✅ التحقق من صلاحية إرسال رسائل الاتجاه
            if not self.notification_manager.should_send_message('trend'):
                logger.info("🔕 إشعارات الاتجاه معطلة - تم تخطي الإرسال")
                return
                
            from notifications.message_formatter import MessageFormatter
            message = MessageFormatter.format_trend_message(signal_data, new_trend, old_trend or "UNKNOWN", trend_signals)
            
            success = self.notification_manager.send_notifications(message, 'trend')
            logger.info(f"📤 إشعار الاتجاه: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'} - {len(trend_signals)} إشارة مستخدمة")
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الاتجاه", e, {
                'symbol': signal_data.get('symbol'),
                'new_trend': new_trend,
                'old_trend': old_trend
            })

    def _send_exit_notification(self, signal_data: Dict, closed_trades: int, remaining_trades: int):
        """🎯 إرسال إشعار الخروج مع معلومات الصفقات المغلقة"""
        try:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال")
                return
                
            from notifications.message_formatter import MessageFormatter
            symbol = signal_data['symbol']
            total_active = self.trade_manager.get_active_trades_count()
            
            message = MessageFormatter.format_exit_message(symbol, signal_data['signal_type'], 
                                                         closed_trades, remaining_trades, total_active, self.config)
            success = self.notification_manager.send_notifications(message, 'exit')
            logger.info(f"📤 إشعار الخروج: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'} - {closed_trades} صفقة مغلقة")
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الخروج", e, {
                'symbol': signal_data.get('symbol'),
                'signal_type': signal_data.get('signal_type')
            })

    def _send_entry_notifications(self, signal_data: Dict, trade_results: List[Dict]):
        """🎯 إرسال إشعارات الدخول"""
        try:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال")
                return
                
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
                success = self.notification_manager.send_notifications(message, 'entry')
                logger.info(f"📤 إشعار الدخول: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'}")
                
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعارات الدخول", e, {
                'trade_results_count': len(trade_results),
                'symbol': signal_data.get('symbol')
            })

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()

    def get_system_status(self) -> Dict:
        """🎯 الحصول على حالة النظام المفصلة"""
        return {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "active_trades": self.trade_manager.get_active_trades_count(),
            "pending_signals": sum(len(signals) for symbol_data in self.group_manager.pending_signals.values() 
                                 for signals in symbol_data.values() if hasattr(signals, '__len__')),
            "current_trends": len(self.trade_manager.current_trend),
            "error_count": len(self._error_log),
            "webhook_errors": len(self._error_log)
        }