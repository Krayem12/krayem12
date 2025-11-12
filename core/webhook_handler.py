# core/webhook_handler.py
import json
import re
import logging
from flask import request, jsonify

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Webhook receiver for processing incoming alerts - WITHOUT SIGNAL CLEANUP"""

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
        يدعم:
        - 'TSLA bullish moneyflow_above_50'
        - 'MSFT moneyflow_below_50' 
        - 'SPX500 bearish_catcher'
        - 'Ticker : SYMBOL Signal : SIGNAL_TYPE'
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
                
                # التحقق من أن الرمز يحتوي على أحرف/أرقام فقط
                if symbol_candidate and re.match(r'^[A-Z0-9]{1,10}$', symbol_candidate):
                    signal_candidate = ' '.join(parts[1:]).strip()
                    
                    logger.debug(f"✅ تم التعرف على التنسيق البسيط: {symbol_candidate} -> {signal_candidate}")
                    return symbol_candidate, signal_candidate

        # 🎯 القائمة 2: التنسيق مع النقطتين "Ticker: SYMBOL Signal: SIGNAL"
        m_sym = re.search(r'(?i)(?:ticker|symbol|sym)\s*:\s*([A-Za-z0-9._\-]+)', text)
        symbol = m_sym.group(1).upper().strip() if m_sym else None

        m_sig = re.search(r'(?i)signal\s*:\s*([A-Za-z0-9_+\- ]+)', text)
        if not m_sig:
            m_sig = re.search(r'(?i)alert\s*:\s*([A-Za-z0-9_+\- ]+)', text)
        signal_type = m_sig.group(1).strip() if m_sig else None

        if symbol and signal_type:
            logger.debug(f"✅ تم التعرف على التنسيق مع النقطتين: {symbol} -> {signal_type}")
            return symbol, signal_type

        # 🎯 القائمة 3: البحث الذكي عن الرمز والإشارة
        if not symbol:
            # البحث عن رموز الأسهم الشائعة (1-5 أحرف، قد تحتوي أرقام)
            symbol_match = re.search(r'\b([A-Z]{1,5}[0-9]{0,2}[A-Z]?)\b', text)
            if symbol_match:
                symbol = symbol_match.group(1).upper()
                logger.debug(f"🔍 تم العثور على رمز: {symbol}")

        if not signal_type:
            # 🎯 قائمة شاملة بالإشارات المعروفة في النظام
            known_signals = [
                # GROUP3 Bullish
                "bullish moneyflow_above_50", "bullish_moneyflow_above_50", 
                "bullish moneyflow_co_50", "bullish_moneyflow_co_50",
                # GROUP3 Bearish  
                "moneyflow_below_50", "bearish_moneyflow_below_50",
                "moneyflow_cu_50", "bearish_moneyflow_cu_50",
                # GROUP1/GROUP2
                "bearish_catcher", "bullish_catcher",
                "oversold_bullish_hyperwave_signal", "regular_bullish_hyperwave_signal",
                "overbought_bearish_hyperwave_signal", "regular_bearish_hyperwave_signal", 
                "Discount", "Premium",
                # Exit Signals
                "exit_buy", "exit_sell",
                # Trend Signals
                "bullish_tracer", "bearish_tracer", "rayian"
            ]
            
            text_lower = text.lower()
            for signal in known_signals:
                if signal.lower() in text_lower:
                    signal_type = signal
                    logger.debug(f"🔍 تم العثور على إشارة معروفة: {signal_type}")
                    break

            # إذا لم نجد إشارة معروفة، نأخذ كل شيء بعد الرمز كنوع الإشارة
            if not signal_type and symbol:
                # إزالة الرمز من النص للحصول على الإشارة
                signal_candidate = text.replace(symbol, '').strip()
                if signal_candidate:
                    signal_type = signal_candidate
                    logger.debug(f"🔍 استخدام النص المتبقي كإشارة: {signal_type}")

        if symbol and signal_type:
            logger.debug(f"✅ النجاح باستخدام البحث الذكي: {symbol} -> {signal_type}")
            return symbol, signal_type

        logger.error(f"❌ فشل في استخراج البيانات من: '{text}'")
        logger.info(f"📋 تلميح: استخدم التنسيق 'SYMBOL SIGNAL_TYPE' مثل 'TSLA bullish_catcher'")
        return None, None

    def _validate_signal_data(self, symbol: str, signal_type: str) -> bool:
        """🆕 التحقق من صحة بيانات الإشارة"""
        if not symbol or symbol == 'UNKNOWN':
            logger.error("❌ رمز غير صالح")
            return False
            
        if not signal_type or not signal_type.strip():
            logger.error("❌ نوع الإشارة فارغ")
            return False
            
        # التحقق من أن الرمز يحتوي على أحرف وأرقام فقط
        if not re.match(r'^[A-Z0-9]{1,10}$', symbol):
            logger.error(f"❌ تنسيق الرمز غير صالح: {symbol}")
            return False
            
        return True

    def handle_webhook(self):
        # 🛠️ الإصلاح: تفعيل التسجيل المفصل في بداية كل طلب
        logger.debug("=" * 60)
        logger.debug("📥 📥 📥 طلب واردة جديدة إلى الويب هووك 📥 📥 📥")
        logger.debug("=" * 60)
        
        try:
            raw = request.data.decode('utf-8').strip()
            logger.debug(f"📨 البيانات الخام المستلمة: {raw[:200]}...")
            logger.debug(f"🔍 رؤوس الطلب: {dict(request.headers)}")

            # 1) جرّب JSON أولاً
            data = None
            json_parse_error = None
            try:
                if raw and raw.strip():
                    data = json.loads(raw)
                    logger.debug(f"✅ تم تحليل JSON بنجاح: {data}")
                else:
                    logger.warning("⚠️ البيانات الخام فارغة")
            except json.JSONDecodeError as e:
                json_parse_error = f"خطأ في تحليل JSON: {e}"
                logger.debug(f"❌ {json_parse_error}")
                data = None
            except Exception as e:
                json_parse_error = f"خطأ غير متوقع في تحليل JSON: {e}"
                logger.error(f"❌ {json_parse_error}")
                data = None

            # 2) تفكيك نصّي إذا لم يكن JSON
            if not data:
                logger.debug("🔍 محاولة التحليل النصي...")
                symbol, signal_type = self._parse_plaintext_alert(raw)
                logger.debug(f"📝 نتيجة التحليل النصي: {symbol} -> {signal_type}")
                
                # 🆕 التحقق من صحة البيانات المستخرجة
                if not self._validate_signal_data(symbol, signal_type):
                    error_msg = "❌ بيانات الإشارة غير صالحة"
                    if json_parse_error:
                        error_msg += f" (أخطاء JSON: {json_parse_error})"
                    logger.error(error_msg)
                    return jsonify({"error": "Invalid alert format"}), 400
                    
                data = {"symbol": symbol, "signal_type": signal_type}

            # Normalize
            symbol = data["symbol"].upper().strip()
            signal_type = data["signal_type"].strip()

            logger.debug(f"🎯 بيانات الإشارة المستخرجة: رمز={symbol}, إشارة={signal_type}")

            # 🆕 التحقق النهائي من صحة البيانات
            if not self._validate_signal_data(symbol, signal_type):
                logger.error(f"❌ تحقق فاشل: {symbol} -> {signal_type}")
                return jsonify({"error": "Invalid symbol or signal type"}), 400

            signal_data = {
                "symbol": symbol,
                "signal_type": signal_type,
                "timestamp": data.get("timestamp")
            }

            logger.debug(f"🔍 بدء معالجة الإشارة: {symbol} -> {signal_type}")

            # 🆕 استخدام التصنيف الآمن مع تفاصيل أكثر
            logger.debug("🎯 بدء تصنيف الإشارة...")
            classification = self.signal_processor.safe_classify_signal(signal_data)

            logger.debug(f"🎯 نتيجة التصنيف: {classification}")

            if not classification or classification == 'unknown':
                logger.warning(f"⚠️ نوع إشارة غير معروف بعد التصنيف: '{signal_type}' للرمز {symbol}")
                return jsonify({"error": f"Unknown signal: {signal_type}"}), 400

            logger.debug(f"✅ تم تصنيف الإشارة بنجاح: {classification}")

            # ✅ إشارات الاتجاه — لا تفتح صفقات
            if classification in ['trend', 'trend_confirm']:
                logger.debug(f"🔄 تحديث الاتجاه بدون فتح صفقة: {symbol} | {classification}")
                
                # استخدام الدالة المعدلة التي ترجع ما إذا كان يجب الإبلاغ والاتجاه السابق
                should_report, old_trend = self.trade_manager.update_trend(symbol, classification, signal_data)
                
                # 🆕 إرسال إشعار الاتجاه فقط بدون تنظيف
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
                    
                    # 🆕 استخدام معالجة آمنة
                    try:
                        exit_message = MessageFormatter.format_exit_message(
                            symbol, signal_type, active_for_symbol, total_active, self.config
                        )
                        self.notification_manager.send_notifications(exit_message, 'exit')
                    except Exception as e:
                        logger.error(f"⚠️ خطأ في تنسيق رسالة الخروج: {e}")
                        # رسالة بديلة
                        fallback_msg = f"🚪 إشارة خروج: {symbol} - {signal_type}"
                        self.notification_manager.send_notifications(fallback_msg, 'exit')
                
                return jsonify({"status": "exit_processed", "symbol": symbol})

            # ✅ إشارات الدخول (Group Manager Logic) - MULTI-MODE SUPPORT
            logger.debug(f"🎯 توجيه إشارة دخول إلى GroupManager: {symbol} -> {classification}")
            
            # 🎯 MULTI-MODE: الحصول على قائمة بالصفقات المفتوحة
            trade_results = self.group_manager.route_signal(symbol, signal_data, classification)
            
            # 🎯 MULTI-MODE: إرسال إشعار لكل صفقة مفتوحة
            if trade_results and self.notification_manager.should_send_message('entry'):
                from notifications.message_formatter import MessageFormatter
                
                for trade_result in trade_results:
                    current_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                    active_for_symbol = self.trade_manager.get_active_trades_count(symbol)
                    total_active = self.trade_manager.get_active_trades_count()
                    
                    # 🆕 استخدام معالجة آمنة
                    try:
                        # استخدام الرسالة المفصلة مع معلومات النمط
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
                        # 🛠️ محاولة استخدام الدالة الإصلاحية
                        try:
                            entry_message = MessageFormatter.format_detailed_entry_message_fixed(
                                symbol=trade_result['symbol'],
                                signal_type=signal_type,
                                direction=trade_result['direction'],
                                current_trend=current_trend,
                                strategy_type=trade_result['strategy_type'],
                                group1_signals=trade_result.get('group1_signals'),
                                group2_signals=trade_result.get('group2_signals'),
                                group3_signals=trade_result.get('group3_signals'),
                                active_for_symbol=active_for_symbol,
                                total_active=total_active,
                                config=self.config,
                                mode_key=trade_result.get('mode_key', 'TRADING_MODE')
                            )
                            self.notification_manager.send_notifications(entry_message, 'entry')
                            logger.debug(f"✅ تم إرسال الإشعار باستخدام الدالة الإصلاحية")
                        except Exception as e2:
                            logger.error(f"❌ فشل الإرسال بالدالة الإصلاحية: {e2}")
                            # رسالة بديلة
                            fallback_msg = f"🚀 دخول صفقة: {symbol} - {signal_type} - {trade_result['direction']} - النمط: {trade_result.get('mode_key', 'TRADING_MODE')}"
                            self.notification_manager.send_notifications(fallback_msg, 'entry')

            return jsonify({
                "status": "entry_processed", 
                "symbol": symbol, 
                "classification": classification,
                "trades_opened": len(trade_results),
                "trade_modes": [trade.get('mode_key', 'TRADING_MODE') for trade in trade_results]
            })

        except Exception as e:
            logger.error(f"💥 خطأ في معالجة الويب هووك: {e}")
            return jsonify({"error": str(e)}), 500

    # 🚫 تم حذف الدوال التالية:
    # - _safe_send_trend_notification