# core/webhook_handler.py
import json
import re
import logging
from flask import request, jsonify
from notifications.message_formatter import MessageFormatter  # 🆕 إضافة الاستيراد

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Webhook receiver for processing incoming alerts - مع التحقق من الاستراتيجية"""

    def __init__(self, config, signal_processor, group_manager, trade_manager, notification_manager, cleanup_manager):
        self.config = config
        self.signal_processor = signal_processor
        self.group_manager = group_manager
        self.trade_manager = trade_manager
        self.notification_manager = notification_manager
        self.cleanup_manager = cleanup_manager

    def register_routes(self, app):
        app.add_url_rule(
            "/webhook",
            view_func=self.handle_webhook,
            methods=["POST"]
        )
        logger.info("🔗 تم تسجيل مسار الويب هووك في /webhook")

    def _parse_plaintext_alert(self, raw: str):
        """
        🎯 محسن لاستخراج الرمز ونوع الإشارة من تنسيقات متعددة
        """
        if not raw or not raw.strip():
            logger.error("❌ نص الإشارة فارغ")
            return None, None

        text = raw.strip()
        logger.debug(f"🔍 جاري تحليل النص: '{text}'")

        # 🎯 القائمة 1: التنسيق البسيط "SYMBOL SIGNAL"
        if ' ' in text and not ':' in text:
            parts = text.split()
            if len(parts) >= 2:
                symbol_candidate = parts[0].upper().strip()
                
                if symbol_candidate and re.match(r'^[A-Z0-9]{1,10}$', symbol_candidate):
                    signal_candidate = ' '.join(parts[1:]).strip()
                    logger.debug(f"✅ تم التعرف على التنسيق البسيط: {symbol_candidate} -> {signal_candidate}")
                    return symbol_candidate, signal_candidate

        # 🎯 القائمة 2: التنسيق مع النقطتين
        m_sym = re.search(r'(?i)(?:ticker|symbol|sym)\s*:\s*([A-Za-z0-9._\-]+)', text)
        symbol = m_sym.group(1).upper().strip() if m_sym else None

        m_sig = re.search(r'(?i)signal\s*:\s*([A-Za-z0-9_+\- ]+)', text)
        if not m_sig:
            m_sig = re.search(r'(?i)alert\s*:\s*([A-Za-z0-9_+\- ]+)', text)
        signal_type = m_sig.group(1).strip() if m_sig else None

        if symbol and signal_type:
            logger.debug(f"✅ تم التعرف على التنسيق مع النقطتين: {symbol} -> {signal_type}")
            return symbol, signal_type

        # 🎯 القائمة 3: البحث الذكي
        if not symbol:
            symbol_match = re.search(r'\b([A-Z]{1,5}[0-9]{0,2}[A-Z]?)\b', text)
            if symbol_match:
                symbol = symbol_match.group(1).upper()
                logger.debug(f"🔍 تم العثور على رمز: {symbol}")

        if not signal_type:
            known_signals = [
                "bullish moneyflow_above_50", "bullish_moneyflow_above_50", 
                "bullish moneyflow_co_50", "bullish_moneyflow_co_50",
                "moneyflow_below_50", "bearish_moneyflow_below_50",
                "moneyflow_cu_50", "bearish_moneyflow_cu_50",
                "bearish_catcher", "bullish_catcher",
                "oversold_bullish_hyperwave_signal", "regular_bullish_hyperwave_signal",
                "overbought_bearish_hyperwave_signal", "regular_bearish_hyperwave_signal", 
                "Discount", "Premium", "exit_buy", "exit_sell",
                "bullish_tracer", "bearish_tracer", "rayian"
            ]
            
            text_lower = text.lower()
            for signal in known_signals:
                if signal.lower() in text_lower:
                    signal_type = signal
                    logger.debug(f"🔍 تم العثور على إشارة معروفة: {signal_type}")
                    break

            if not signal_type and symbol:
                signal_candidate = text.replace(symbol, '').strip()
                if signal_candidate:
                    signal_type = signal_candidate
                    logger.debug(f"🔍 استخدام النص المتبقي كإشارة: {signal_type}")

        if symbol and signal_type:
            logger.debug(f"✅ النجاح باستخدام البحث الذكي: {symbol} -> {signal_type}")
            return symbol, signal_type

        logger.error(f"❌ فشل في استخراج البيانات من: '{text}'")
        return None, None

    def _validate_signal_data(self, symbol: str, signal_type: str) -> bool:
        """🆕 التحقق من صحة بيانات الإشارة"""
        if not symbol or symbol == 'UNKNOWN':
            logger.error("❌ رمز غير صالح")
            return False
            
        if not signal_type or not signal_type.strip():
            logger.error("❌ نوع الإشارة فارغ")
            return False
            
        if not re.match(r'^[A-Z0-9]{1,10}$', symbol):
            logger.error(f"❌ تنسيق الرمز غير صالح: {symbol}")
            return False
            
        return True

    def handle_webhook(self):
        """🛠️ الإصدار المحسن النهائي - مع التحقق من تطبيق الاستراتيجية"""
        logger.debug("=" * 60)
        logger.debug("📥 📥 📥 طلب واردة جديدة إلى الويب هووك 📥 📥 📥")
        logger.debug("=" * 60)
        
        try:
            raw = request.data.decode('utf-8').strip()
            logger.debug(f"📨 البيانات الخام المستلمة: {raw[:200]}...")
            
            # 🛠️ الإصلاح النهائي: فحص دقيق لنوع المحتوى
            content_type = (request.headers.get('Content-Type') or '').lower()
            logger.debug(f"🔍 نوع المحتوى: {content_type}")
            
            data = None
            
            # 🎯 معالجة ذكية لأنواع المحتوى
            if 'application/json' in content_type:
                logger.debug("🔍 المحتوى من نوع JSON، جاري التحليل...")
                try:
                    if raw and raw.strip():
                        data = json.loads(raw)
                        logger.debug(f"✅ تم تحليل JSON بنجاح")
                    else:
                        logger.warning("⚠️ البيانات الخام فارغة")
                except json.JSONDecodeError:
                    logger.debug("🔍 فشل تحليل JSON، الانتقال للتحليل النصي")
                    data = None
                except Exception as e:
                    logger.error(f"❌ خطأ غير متوقع في تحليل JSON: {e}")
                    data = None
            else:
                # 🎯 كل الأنواع الأخرى تعتبر نصية
                logger.debug(f"🔍 نوع محتوى غير JSON، استخدام التحليل النصي مباشرة")
                data = None

            # 🎯 إذا لم يكن JSON أو فشل التحليل، استخدم التحليل النصي
            if not data:
                logger.debug("🔍 بدء التحليل النصي...")
                symbol, signal_type = self._parse_plaintext_alert(raw)
                
                if not symbol or not signal_type:
                    logger.error("❌ فشل التحليل النصي")
                    return jsonify({"error": "Invalid alert format"}), 400
                    
                logger.debug(f"✅ نجح التحليل النصي: {symbol} -> {signal_type}")
                data = {"symbol": symbol, "signal_type": signal_type}

            # Normalize
            symbol = data["symbol"].upper().strip()
            signal_type = data["signal_type"].strip()

            logger.debug(f"🎯 بيانات الإشارة المستخرجة: رمز={symbol}, إشارة={signal_type}")

            # التحقق من صحة البيانات
            if not self._validate_signal_data(symbol, signal_type):
                logger.error(f"❌ تحقق فاشل: {symbol} -> {signal_type}")
                return jsonify({"error": "Invalid symbol or signal type"}), 400

            signal_data = {
                "symbol": symbol,
                "signal_type": signal_type,
                "timestamp": data.get("timestamp")
            }

            logger.debug(f"🔍 بدء معالجة الإشارة: {symbol} -> {signal_type}")

            # التصنيف والمعالجة
            logger.debug("🎯 بدء تصنيف الإشارة...")
            classification = self.signal_processor.safe_classify_signal(signal_data)

            logger.debug(f"🎯 نتيجة التصنيف: {classification}")

            if not classification or classification == 'unknown':
                logger.warning(f"⚠️ نوع إشارة غير معروف: '{signal_type}' للرمز {symbol}")
                return jsonify({"error": f"Unknown signal: {signal_type}"}), 400

            logger.debug(f"✅ تم تصنيف الإشارة بنجاح: {classification}")

            # ✅ إشارات الاتجاه
            if classification in ['trend', 'trend_confirm']:
                logger.debug(f"🔄 تحديث الاتجاه بدون فتح صفقة: {symbol} | {classification}")
                
                should_report, old_trend = self.trade_manager.update_trend(symbol, classification, signal_data)
                
                if should_report and self.notification_manager.should_send_message('trend'):
                    from notifications.message_formatter import MessageFormatter
                    
                    new_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                    
                    try:
                        trend_message = MessageFormatter.format_trend_message(
                            signal_data, 
                            new_trend,
                            old_trend or "UNKNOWN"
                        )
                    except AttributeError:
                        trend_message = MessageFormatter.format_simple_trend_message(
                            symbol=symbol,
                            new_trend=new_trend,
                            old_trend=old_trend or "UNKNOWN",
                            trigger_signal=signal_data['signal_type']
                        )
                    
                    self.notification_manager.send_notifications(trend_message, 'trend')
                    logger.debug(f"📤 تم إرسال إشعار تغيير الاتجاه لـ {symbol}")
                
                return jsonify({
                    "status": "trend_processed", 
                    "symbol": symbol, 
                    "classification": classification,
                    "trend_changed": should_report,
                    "old_trend": old_trend,
                    "new_trend": self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                })

            # ✅ إشارات الخروج
            if classification == 'exit':
                logger.debug(f"🚪 معالجة إشارة خروج: {symbol}")
                self.trade_manager.handle_exit_signal(symbol, signal_type)
                
                if self.notification_manager.should_send_message('exit'):
                    from notifications.message_formatter import MessageFormatter
                    active_for_symbol = self.trade_manager.get_active_trades_count(symbol)
                    total_active = self.trade_manager.get_active_trades_count()
                    
                    try:
                        exit_message = MessageFormatter.format_exit_message(
                            symbol, signal_type, active_for_symbol, total_active, self.config
                        )
                        self.notification_manager.send_notifications(exit_message, 'exit')
                    except Exception as e:
                        logger.error(f"⚠️ خطأ في تنسيق رسالة الخروج: {e}")
                        fallback_msg = f"🚪 إشارة خروج: {symbol} - {signal_type}"
                        self.notification_manager.send_notifications(fallback_msg, 'exit')
                
                return jsonify({"status": "exit_processed", "symbol": symbol})

            # ✅ إشارات الدخول
            logger.debug(f"🎯 توجيه إشارة دخول إلى GroupManager: {symbol} -> {classification}")
            
            trade_results = self.group_manager.route_signal(symbol, signal_data, classification)
            
            # 🆕 التحقق من أن الاستراتيجية المطبقة تتطابق مع الإعدادات
            for trade_result in trade_results:
                mode_key = trade_result.get('mode_key', 'TRADING_MODE')
                applied_strategy = trade_result.get('strategy_type')
                expected_strategy = self.config.get(mode_key, 'GROUP1')
                
                if applied_strategy != expected_strategy:
                    logger.error(f"❌ تناقض استراتيجية: {applied_strategy} vs {expected_strategy} للنمط {mode_key}")
            
            if trade_results and self.notification_manager.should_send_message('entry'):
                from notifications.message_formatter import MessageFormatter
                
                for trade_result in trade_results:
                    current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                    active_for_symbol = self.trade_manager.get_active_trades_count(symbol)
                    total_active = self.trade_manager.get_active_trades_count()
                    
                    try:
                        # 🆕 استخدام الدالة الأساسية فقط
                        entry_message = MessageFormatter.format_detailed_entry_message(
                            symbol=trade_result['symbol'],
                            signal_type=signal_type,
                            direction=trade_result['direction'],
                            current_trend=current_trend,
                            strategy_type=trade_result['strategy_type'],
                            group1_signals=trade_result.get('group1_signals', []),
                            group2_signals=trade_result.get('group2_signals', []),
                            group3_signals=trade_result.get('group3_signals', []),
                            active_for_symbol=active_for_symbol,
                            total_active=total_active,
                            config=self.config,
                            mode_key=trade_result.get('mode_key', 'TRADING_MODE')
                        )
                        self.notification_manager.send_notifications(entry_message, 'entry')
                        logger.debug(f"📤 تم إرسال إشعار دخول للنمط: {trade_result.get('mode_key', 'TRADING_MODE')}")
                    except Exception as e:
                        logger.error(f"⚠️ خطأ في تنسيق رسالة الدخول: {e}")
                        # 🆕 رسالة بديلة مبسطة
                        fallback_msg = f"🚀 دخول صفقة: {symbol} - {signal_type} - {trade_result['direction']} - النمط: {trade_result.get('mode_key', 'TRADING_MODE')}"
                        self.notification_manager.send_notifications(fallback_msg, 'entry')

            return jsonify({
                "status": "entry_processed", 
                "symbol": symbol, 
                "classification": classification,
                "trades_opened": len(trade_results)
            })

        except Exception as e:
            logger.error(f"💥 خطأ في معالجة الويب هووك: {e}")
            return jsonify({"error": str(e)}), 500