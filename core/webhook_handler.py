# core/webhook_handler.py
import json
import re
from flask import request, jsonify

class WebhookHandler:
    """Webhook receiver for processing incoming alerts - FIXED MESSAGE FORMATTER ISSUES"""

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
        print("🔗 تم تسجيل مسار الويب هووك في /webhook")

    def _parse_plaintext_alert(self, raw: str):
        """
        يدعم صيغ مثل:
        'Ticker : KRAYEM Signal : bearish_catcher'
        """
        # التقط الرمز
        m_sym = re.search(r'(?i)\b(?:ticker|symbol|sym)\s*:\s*([A-Za-z0-9._\-]+)', raw)
        symbol = m_sym.group(1).upper().strip() if m_sym else None

        # التقط نوع الإشارة
        m_sig = re.search(r'(?i)\bsignal\s*:\s*([A-Za-z0-9_+\- ]+)', raw)
        if not m_sig:
            m_sig = re.search(r'(?i)\balert\s*:\s*([A-Za-z0-9_+\- ]+)', raw)
        signal_type = m_sig.group(1).strip() if m_sig else None

        if not signal_type:
            candidates = [
                "catcher", "tracer", "confirmation", "confirmation+",
                "hyperwave", "moneyflow_above_50", "moneyflow_below_50",
                "moneyflow", "divergence", "sbos", "bos", "ichoch",
                "exit_buy", "exit_sell", "switch_bullish_catcher", "switch_bearish_catcher",
                "switch_bullish_tracer", "switch_bearish_tracer",
                "bullish_confirmation+", "bearish_confirmation+"
            ]
            found = []
            lower_raw = raw.lower()
            for key in candidates:
                if key in lower_raw:
                    found.append(key)
            if found:
                signal_type = found[-1]

        if not symbol or not signal_type:
            return None, None
        return symbol, signal_type

    def handle_webhook(self):
        try:
            raw = request.data.decode('utf-8').strip()
            print(f"📥 طلب واردة: {raw[:200]}...")

            # 1) جرّب JSON أولاً
            data = None
            json_parse_error = None
            try:
                if raw and raw.strip():
                    data = json.loads(raw)
                    print(f"✅ تم تحليل JSON بنجاح: {list(data.keys())}")
            except json.JSONDecodeError as e:
                json_parse_error = f"خطأ في تحليل JSON: {e}"
                print(f"❌ {json_parse_error}")
                data = None
            except Exception as e:
                json_parse_error = f"خطأ غير متوقع في تحليل JSON: {e}"
                print(f"❌ {json_parse_error}")
                data = None

            # 2) تفكيك نصّي إذا لم يكن JSON
            if not data:
                print("🔍 محاولة التحليل النصي...")
                symbol, signal_type = self._parse_plaintext_alert(raw)
                if not symbol or not signal_type:
                    error_msg = "❌ لم يتمكن النظام من استخراج symbol أو signal_type من الرسالة"
                    if json_parse_error:
                        error_msg += f" (أخطاء JSON: {json_parse_error})"
                    print(error_msg)
                    return jsonify({"error": "Invalid alert format"}), 400
                data = {"symbol": symbol, "signal_type": signal_type}

            # Normalize
            symbol = data["symbol"].upper().strip()
            signal_type = data["signal_type"].strip()

            # حماية من حالات مثل "KRAYEM Signal" الناتجة عن سطر واحد فيه حقلين
            if "signal" in signal_type.lower() and ":" in raw.lower():
                try:
                    m_last_signal = list(re.finditer(r'(?i)\bsignal\s*:\s*([A-Za-z0-9_+\- ]+)', raw))
                    if m_last_signal:
                        signal_type = m_last_signal[-1].group(1).strip()
                except Exception:
                    pass

            signal_data = {
                "symbol": symbol,
                "signal_type": signal_type,
                "timestamp": data.get("timestamp")
            }

            print(f"🔍 معالجة الإشارة: {symbol} -> {signal_type}")

            classification = self.signal_processor.classify_signal(signal_data)

            if not classification or classification == 'unknown':
                print(f"⚠️ نوع إشارة غير معروف بعد التصنيف: '{signal_type}' للرمز {symbol}")
                return jsonify({"error": f"Unknown signal: {signal_type}"}), 400

            print(f"🎯 تصنيف الإشارة: {classification}")

            # ✅ إشارات الاتجاه — لا تفتح صفقات
            if classification in ['trend', 'trend_confirm']:
                print(f"🔄 تحديث الاتجاه بدون فتح صفقة: {symbol} | {classification}")
                
                # استخدام الدالة المعدلة التي ترجع ما إذا كان يجب الإبلاغ والاتجاه السابق
                should_report, old_trend = self.trade_manager.update_trend(symbol, classification, signal_data)
                
                # 🆕 إصلاح: استخدام معالجة آمنة للإشعارات
                self._safe_send_trend_notification(symbol, signal_data, should_report, old_trend)
                
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
                print(f"🚪 معالجة إشارة خروج: {symbol}")
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
                        print(f"⚠️ خطأ في تنسيق رسالة الخروج: {e}")
                        # رسالة بديلة
                        fallback_msg = f"🚪 إشارة خروج: {symbol} - {signal_type}"
                        self.notification_manager.send_notifications(fallback_msg, 'exit')
                
                return jsonify({"status": "exit_processed", "symbol": symbol})

            # ✅ إشارات الدخول (Group Manager Logic) - MULTI-MODE SUPPORT
            print(f"🎯 توجيه إشارة دخول إلى GroupManager: {symbol} -> {classification}")
            
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
                            group3_signals=trade_result.get('group3_signals', []),  # 🛠️ الإصلاح هنا
                            active_for_symbol=active_for_symbol,
                            total_active=total_active,
                            config=self.config,
                            mode_key=trade_result.get('mode_key', 'TRADING_MODE')
                        )
                        self.notification_manager.send_notifications(entry_message, 'entry')
                        print(f"📤 تم إرسال إشعار دخول للنمط: {trade_result.get('mode_key', 'TRADING_MODE')}")
                    except Exception as e:
                        print(f"⚠️ خطأ في تنسيق رسالة الدخول: {e}")
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
                            print(f"✅ تم إرسال الإشعار باستخدام الدالة الإصلاحية")
                        except Exception as e2:
                            print(f"❌ فشل الإرسال بالدالة الإصلاحية: {e2}")
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
            import traceback
            print(f"💥 خطأ في معالجة الويب هووك: {e}")
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    def _safe_send_trend_notification(self, symbol: str, signal_data: dict, should_report: bool, old_trend: str):
        """🆕 معالجة آمنة لإرسال إشعارات الاتجاه"""
        try:
            if should_report and self.notification_manager.should_send_message('trend'):
                from notifications.message_formatter import MessageFormatter
                
                new_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                
                # 🆕 محاولة استخدام الدالة الأساسية أولاً
                try:
                    trend_message = MessageFormatter.format_trend_message(
                        signal_data, 
                        new_trend,
                        old_trend or "UNKNOWN"
                    )
                except AttributeError:
                    # 🆕 إذا فشلت، استخدم الدالة المبسطة
                    print("⚠️ استخدام الدالة البديلة format_simple_trend_message")
                    trend_message = MessageFormatter.format_simple_trend_message(
                        symbol=symbol,
                        new_trend=new_trend,
                        old_trend=old_trend or "UNKNOWN",
                        trigger_signal=signal_data['signal_type']
                    )
                
                self.notification_manager.send_notifications(trend_message, 'trend')
                print(f"📤 تم إرسال إشعار تغيير الاتجاه لـ {symbol}: {old_trend} → {new_trend}")
            else:
                print(f"🔇 لم يتم إرسال إشعار الاتجاه لـ {symbol} (لا تغيير حقيقي أو إشعارات معطلة)")
                
        except Exception as e:
            print(f"⚠️ خطأ في إرسال إشعار الاتجاه: {e}")
            # محاولة إرسال رسالة بديلة بسيطة
            try:
                new_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                simple_msg = f"📊 تغيير الاتجاه: {symbol} | {old_trend} → {new_trend} | الإشارة: {signal_data['signal_type']}"
                self.notification_manager.send_notifications(simple_msg, 'trend')
            except:
                print(f"❌ فشل إرسال الرسالة البديلة أيضًا")