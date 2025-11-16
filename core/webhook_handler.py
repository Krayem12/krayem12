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
        
        # 🛠️ التحقق من التهيئة
        logger.debug(f"🔧 تهيئة WebhookHandler - EXTERNAL_SERVER_ENABLED: {self.config.get('EXTERNAL_SERVER_ENABLED')}")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append(full_error)

    def register_routes(self, app) -> None:
        """تسجيل المسارات"""
        app.add_url_rule("/webhook", view_func=self.handle_webhook, methods=["POST"])
        app.add_url_rule("/health", view_func=self.health_check, methods=["GET"])
        logger.info("🔗 تم تسجيل مسار الويب هووك والفحص الصحي")

    def health_check(self):
        """فحص صحة النظام"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "11.0_detailed_trend_with_group4_group5"
        })

    def handle_webhook(self):
        """🎯 معالجة طلبات الويب هووك مع تسجيل محسن"""
        logger.info("📥 📥 📥 طلب ويب هووك واردة جديدة 📥 📥 📥")
        
        try:
            # 🛠️ الإصلاح: تسجيل معلومات الطلب الأساسية
            client_ip = request.remote_addr
            content_type = request.headers.get('Content-Type', '')
            content_length = request.headers.get('Content-Length', 0)
            
            logger.info(f"🌐 معلومات الطلب: IP={client_ip}, Content-Type={content_type}, Length={content_length}")
            
            # الحصول على البيانات الخام
            raw_data = request.get_data(as_text=True)
            if not raw_data:
                logger.warning("⚠️ طلب فارغ - لا توجد بيانات")
                return jsonify({"error": "Empty request body"}), 400
            
            logger.info(f"📝 البيانات الواردة: {raw_data[:500]}{'...' if len(raw_data) > 500 else ''}")
            
            # تحليل الطلب
            signal_data = self._parse_incoming_request(raw_data)
            
            if not signal_data:
                logger.error("❌ فشل تحليل بيانات الإشارة")
                return jsonify({"error": "Invalid signal data"}), 400

            logger.info(f"🎯 تم تحليل الإشارة: رمز={signal_data['symbol']}, نوع={signal_data['signal_type']}")

            # معالجة الإشارة
            result = self._process_signal(signal_data)
            logger.info(f"✅ تم معالجة الإشارة بنجاح")
            
            return result

        except Exception as e:
            error_msg = f"💥 خطأ في معالجة الويب هووك: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    def _parse_incoming_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل الطلب الوارد مع تسجيل محسن"""
        logger.debug("🔍 بدء تحليل الطلب الوارد...")
        
        content_type = (request.headers.get('Content-Type') or '').lower()
        
        if 'application/json' in content_type:
            logger.debug("📋 تحليل طلب JSON...")
            return self._parse_json_request(raw_data)
        else:
            logger.debug("📋 تحليل طلب نصي...")
            return self._parse_plaintext_request(raw_data)

    def _parse_json_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل طلب JSON مع تسجيل محسن"""
        try:
            if not raw_data.strip():
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
            self._handle_error("❌ خطأ في تحليل JSON", e)
            return None

    def _parse_plaintext_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل طلب نصي مع تسجيل محسن"""
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
            self._handle_error("❌ خطأ في تحليل النص", e)
            return None

    def _extract_from_plaintext(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """🎯 استخراج الرمز والإشارة من النص مع تسجيل محسن"""
        logger.debug(f"🔍 استخراج من النص: {text}")
        
        # نمط Ticker: SYMBOL Signal: SIGNAL
        match = re.search(r'(?i)ticker\s*:\s*([A-Z0-9]+).*?signal\s*:\s*([A-Za-z0-9_ ]+)', text)
        if match:
            symbol, signal = match.group(1), match.group(2)
            logger.debug(f"✅ تم الاستخراج بنمط Ticker/Signal: {symbol} -> {signal}")
            return symbol, signal

        # نمط SYMBOL SIGNAL
        match = re.match(r'([A-Z0-9]+)\s+([A-Za-z0-9_ ]+)', text)
        if match:
            symbol, signal = match.group(1), match.group(2)
            logger.debug(f"✅ تم الاستخراج بنمط Symbol/Signal: {symbol} -> {signal}")
            return symbol, signal

        # نمط الإشارة فقط (استخدام UNKNOWN للرمز)
        if text.strip():
            logger.debug(f"⚠️ استخدام النمط الافتراضي: UNKNOWN -> {text}")
            return "UNKNOWN", text.strip()

        logger.warning("❌ فشل جميع أنماط الاستخراج")
        return None, None

    def _process_signal(self, signal_data: Dict):
        """🎯 معالجة الإشارة مع تسجيل محسن"""
        logger.info(f"🎯 بدء معالجة الإشارة: {signal_data['signal_type']} للرمز {signal_data['symbol']}")
        
        classification = self.signal_processor.safe_classify_signal(signal_data)
        
        logger.info(f"🎯 تصنيف الإشارة: {signal_data['signal_type']} -> {classification}")
        
        if classification == 'unknown':
            logger.warning(f"⚠️ إشارة غير معروفة: {signal_data['signal_type']}")
            return jsonify({"error": f"Unknown signal: {signal_data['signal_type']}"}), 400

        # 🎯 توجيه الإشارة بناءً على التصنيف
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
                return jsonify({"error": f"Unhandled classification: {classification}"}), 400
                
        except Exception as e:
            error_msg = f"💥 خطأ في معالجة الإشارة المصنفة: {e}"
            logger.error(error_msg, exc_info=True)
            return jsonify({"error": "Signal processing error"}), 500

    def _handle_trend_signal(self, signal_data: Dict, classification: str):
        """🎯 معالجة إشارات الاتجاه مع تسجيل محسن"""
        symbol = signal_data['symbol']
        logger.info(f"📈 معالجة إشارة اتجاه لـ {symbol}: {signal_data['signal_type']}")
        
        # 🎯 الإصلاح: الحصول على قائمة الإشارات المستخدمة في تغيير الاتجاه
        should_report, old_trend, trend_signals = self.trade_manager.update_trend(symbol, classification, signal_data)
        
        logger.info(f"📊 نتيجة تحديث الاتجاه: {symbol} -> تغيير={should_report}, اتجاه قديم={old_trend}, عدد الإشارات={len(trend_signals)}")
        
        if should_report:
            # 🛠️ الإصلاح: التحقق من وجود خدمات مفعلة قبل الإرسال
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            logger.debug(f"🔍 تحقق الإشعار - التليجرام: {telegram_enabled}, الخارجي: {external_enabled}")
            
            if telegram_enabled or external_enabled:
                self._send_trend_notification(signal_data, self.trade_manager.current_trend.get(symbol), old_trend, trend_signals)
            else:
                logger.debug("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعار الاتجاه")
        
        return jsonify({
            "status": "trend_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trend_changed": should_report,
            "current_trend": self.trade_manager.current_trend.get(symbol),
            "old_trend": old_trend,
            "signals_used": len(trend_signals),
            "signals_details": [{"signal_type": s['signal_type'], "direction": s['direction']} for s in trend_signals]
        })

    def _handle_exit_signal(self, signal_data: Dict):
        """🎯 معالجة إشارات الخروج مع تسجيل محسن"""
        symbol = signal_data['symbol']
        logger.info(f"🚪 معالجة إشارة خروج لـ {symbol}: {signal_data['signal_type']}")
        
        self.trade_manager.handle_exit_signal(symbol, signal_data['signal_type'])
        
        if self.notification_manager.should_send_message('exit'):
            # 🛠️ الإصلاح: التحقق من وجود خدمات مفعلة قبل الإرسال
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if telegram_enabled or external_enabled:
                self._send_exit_notification(signal_data)
            else:
                logger.debug("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعار الخروج")
        
        return jsonify({
            "status": "exit_processed", 
            "symbol": symbol,
            "signal_type": signal_data['signal_type']
        })

    def _handle_entry_signal(self, signal_data: Dict, classification: str):
        """🎯 معالجة إشارات الدخول مع تسجيل محسن"""
        symbol = signal_data['symbol']
        logger.info(f"🚀 معالجة إشارة دخول لـ {symbol}: {classification} -> {signal_data['signal_type']}")
        
        trade_results = self.group_manager.route_signal(symbol, signal_data, classification)
        
        logger.info(f"📊 نتائج التداول لـ {symbol}: {len(trade_results)} صفقات مفتوحة")
        
        if trade_results and self.notification_manager.should_send_message('entry'):
            # 🛠️ الإصلاح: التحقق من وجود خدمات مفعلة قبل الإرسال
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if telegram_enabled or external_enabled:
                self._send_entry_notifications(signal_data, trade_results)
            else:
                logger.debug("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعارات الدخول")
        
        return jsonify({
            "status": "entry_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trades_opened": len(trade_results),
            "trade_details": trade_results
        })

    def _send_trend_notification(self, signal_data: Dict, new_trend: str, old_trend: Optional[str], trend_signals: List[Dict]):
        """🎯 إرسال إشعار الاتجاه مع تحقق إضافي"""
        try:
            # 🛠️ تحقق إضافي مفصل
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            logger.debug(f"🔍 تحقق الإشعار - التليجرام: {telegram_enabled}, الخارجي: {external_enabled}")
            
            if not (telegram_enabled or external_enabled):
                logger.debug("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال")
                return
                
            # 🛠️ تحقق إضافي: إذا كان الخارجي معطلًا، لا ننشئ الرسالة إلا إذا كان التليجرام مفعلًا
            if not external_enabled and not telegram_enabled:
                logger.debug("🔕 لا توجد خدمات مفعلة - تم إلغاء الإرسال")
                return
                
            from notifications.message_formatter import MessageFormatter
            message = MessageFormatter.format_trend_message(signal_data, new_trend, old_trend or "UNKNOWN", trend_signals)
            
            # 🛠️ تحقق نهائي قبل الإرسال
            if not external_enabled:
                logger.debug("🔒 الإرسال للخادم الخارجي مغلق - سيتم الإرسال للتليجرام فقط إذا كان مفعلًا")
                
            success = self.notification_manager.send_notifications(message, 'trend')
            logger.info(f"📤 إشعار الاتجاه: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'} - {len(trend_signals)} إشارة مستخدمة")
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الاتجاه", e)

    def _send_exit_notification(self, signal_data: Dict):
        """🎯 إرسال إشعار الخروج مع تسجيل محسن"""
        try:
            # 🛠️ الإصلاح: التحقق من وجود خدمات مفعلة قبل الإرسال
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.debug("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال")
                return
                
            from notifications.message_formatter import MessageFormatter
            symbol = signal_data['symbol']
            active_count = self.trade_manager.get_active_trades_count(symbol)
            total_active = self.trade_manager.get_active_trades_count()
            
            message = MessageFormatter.format_exit_message(symbol, signal_data['signal_type'], 
                                                         active_count, total_active, self.config)
            success = self.notification_manager.send_notifications(message, 'exit')
            logger.info(f"📤 إشعار الخروج: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'}")
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الخروج", e)

    def _send_entry_notifications(self, signal_data: Dict, trade_results: List[Dict]):
        """🎯 إرسال إشعارات الدخول مع تسجيل محسن"""
        try:
            # 🛠️ الإصلاح: التحقق من وجود خدمات مفعلة قبل الإرسال
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.debug("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال")
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
            self._handle_error("⚠️ خطأ في إرسال إشعارات الدخول", e)

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()