# core/webhook_handler.py
import json
import re
from flask import request, jsonify

class WebhookHandler:
    """Webhook receiver for processing incoming alerts - UPDATED FOR MULTI-MODE"""

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
            try:
                if raw:
                    data = json.loads(raw)
            except Exception:
                data = None

            # 2) تفكيك نصّي إذا لم يكن JSON
            if not data:
                symbol, signal_type = self._parse_plaintext_alert(raw)
                if not symbol or not signal_type:
                    print("❌ لم يتمكن النظام من استخراج symbol أو signal_type من الرسالة")
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
                
                # إرسال الإشعارات فقط إذا كان هناك تغيير حقيقي في الاتجاه
                if should_report and self.notification_manager.should_send_message('trend'):
                    from notifications.message_formatter import MessageFormatter
                    new_trend = self.trade_manager.current_trend.get(symbol, 'UNKNOWN')
                    
                    # 🆕 استخدام الاتجاه السابق الحقيقي بدلاً من الاتجاه الحالي
                    trend_message = MessageFormatter.format_trend_message(
                        signal_data, 
                        new_trend,
                        old_trend or "UNKNOWN"  # 🆕 استخدام الاتجاه السابق الحقيقي
                    )
                    self.notification_manager.send_notifications(trend_message, 'trend')
                    print(f"📤 تم إرسال إشعار تغيير الاتجاه لـ {symbol}: {old_trend} → {new_trend}")
                else:
                    print(f"🔇 لم يتم إرسال إشعار الاتجاه لـ {symbol} (لا تغيير حقيقي)")
                
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
                    exit_message = MessageFormatter.format_exit_message(
                        symbol, signal_type, active_for_symbol, total_active, self.config
                    )
                    self.notification_manager.send_notifications(exit_message, 'exit')
                
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
                    
                    # استخدام الرسالة المفصلة مع معلومات النمط
                    entry_message = MessageFormatter.format_detailed_entry_message(
                        symbol=trade_result['symbol'],
                        signal_type=signal_type,
                        direction=trade_result['direction'],
                        current_trend=current_trend,
                        strategy_type=trade_result['strategy_type'],
                        group1_signals=trade_result['group1_signals'],
                        group2_signals=trade_result['group2_signals'],
                        group3_signals=trade_result['group3_signals'],
                        active_for_symbol=active_for_symbol,
                        total_active=total_active,
                        config=self.config,
                        mode_key=trade_result.get('mode_key', 'TRADING_MODE')  # 🎯 MULTI-MODE
                    )
                    self.notification_manager.send_notifications(entry_message, 'entry')
                    print(f"📤 تم إرسال إشعار دخول للنمط: {trade_result.get('mode_key', 'TRADING_MODE')}")

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