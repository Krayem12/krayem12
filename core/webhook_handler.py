# core/webhook_handler.py - النسخة المحدثة
import json
import re
import logging
from flask import request, jsonify
from typing import Dict, Optional, Tuple, List
from collections import deque
from datetime import datetime, timedelta

# ✅ استيراد موحد
from utils.time_utils import saudi_time
from .debug_guard import DebugGuard  # ✅ إضافة الجديدة

logger = logging.getLogger(__name__)

class WebhookHandler:
    """🎯 معالج الويب هووك بالتوقيت السعودي مع حماية Debug APIs"""

    def __init__(self, config, signal_processor, group_manager, trade_manager, notification_manager, cleanup_manager):
        self.config = config
        self.signal_processor = signal_processor
        self.group_manager = group_manager
        self.trade_manager = trade_manager
        self.notification_manager = notification_manager
        self.cleanup_manager = cleanup_manager
        self._error_log = deque(maxlen=500)
        
        # 🛠️ إضافة DebugGuard
        self.debug_guard = DebugGuard(config)
        logger.info("✅ DebugGuard مفعل لحماية واجهات التصحيح")
        
        # 🛠️ إعداد rate limiting
        self.request_counts = {}
        self.rate_limit_requests = self.config.get('RATE_LIMIT_REQUESTS', 60)
        self.rate_limit_period = self.config.get('RATE_LIMIT_PERIOD', 60)

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None, 
                     extra_data: Optional[Dict] = None) -> None:
        """🎯 معالجة الأخطاء بالتوقيت السعودي"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        if extra_data:
            full_error += f" | Extra: {extra_data}"
        logger.error(full_error)
        
        error_entry = {
            'timestamp': saudi_time.now().isoformat(),
            'timezone': 'Asia/Riyadh 🇸🇦',
            'error': full_error
        }
        self._error_log.append(error_entry)
        
        if len(self._error_log) > 500:
            excess = len(self._error_log) - 500
            for _ in range(excess):
                if self._error_log:
                    self._error_log.popleft()

    def _check_rate_limit(self, client_ip: str) -> bool:
        """🔒 التحقق من معدل الطلبات"""
        try:
            current_time = saudi_time.now()
            
            if client_ip in self.request_counts:
                self.request_counts[client_ip] = [
                    req_time for req_time in self.request_counts[client_ip]
                    if (current_time - req_time).total_seconds() < self.rate_limit_period
                ]
            
            if client_ip not in self.request_counts:
                self.request_counts[client_ip] = []
            
            if len(self.request_counts[client_ip]) >= self.rate_limit_requests:
                logger.warning(f"🚫 تجاوز معدل الطلبات للعميل: {client_ip}")
                return False
            
            self.request_counts[client_ip].append(current_time)
            return True
            
        except Exception as e:
            self._handle_error("💥 خطأ في rate limiting", e)
            return True

    def register_routes(self, app) -> None:
        """✅ المحدث: تسجيل المسارات مع حماية Debug APIs"""
        
        # المسارات الأساسية
        app.add_url_rule("/webhook", view_func=self.handle_webhook, methods=["POST"])
        app.add_url_rule("/health", view_func=self.health_check, methods=["GET"])
        
        # 🔒 جميع واجهات التصحيح محمية بـ DebugGuard
        app.add_url_rule("/debug/trend/<symbol>", 
                        view_func=self.debug_guard.require_debug_auth(self.debug_trend), 
                        methods=["GET"])
        
        app.add_url_rule("/debug/force_trend/<symbol>/<direction>", 
                        view_func=self.debug_guard.require_debug_auth(self.debug_force_trend), 
                        methods=["POST"])
        
        app.add_url_rule("/debug/force_trade/<symbol>/<direction>", 
                        view_func=self.debug_guard.require_debug_auth(self.debug_force_trade), 
                        methods=["POST"])
        
        app.add_url_rule("/debug/clear_trend/<symbol>", 
                        view_func=self.debug_guard.require_debug_auth(self.debug_clear_trend), 
                        methods=["POST"])
        
        app.add_url_rule("/debug/stats", 
                        view_func=self.debug_guard.require_debug_auth(self.debug_stats), 
                        methods=["GET"])
        
        app.add_url_rule("/debug/cleanup_memory", 
                        view_func=self.debug_guard.require_debug_auth(self.debug_cleanup_memory), 
                        methods=["POST"])
        
        # واجهة التحقق من حالة التصحيح (محمية أيضًا)
        @app.route("/debug/status", methods=["GET"])
        @self.debug_guard.require_debug_auth
        def debug_status():
            """🔒 واجهة آمنة للتحقق من حالة التصحيح"""
            return jsonify(self.debug_guard.get_debug_status())
        
        logger.info("🔗 تم تسجيل مسارات الويب هووك والتصحيح مع حماية DebugGuard - التوقيت السعودي 🇸🇦")

    def health_check(self):
        """فحص صحة النظام بالتوقيت السعودي"""
        try:
            return jsonify({
                "status": "healthy",
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦",
                "version": "12.1_saudi_time_with_debug_guard",
                "debug_protection": self.debug_guard.get_debug_status(),
                "system_metrics": {
                    "active_trades": self.trade_manager.get_active_trades_count(),
                    "pending_signals": sum(len(signals) for symbol_data in self.group_manager.pending_signals.values() 
                                         for signals in symbol_data.values() if hasattr(signals, '__len__')),
                    "error_count": len(self._error_log),
                    "current_trends": len(self.trade_manager.current_trend),
                    "signal_processor_stats": self.signal_processor.get_system_stats() if hasattr(self.signal_processor, 'get_system_stats') else {}
                }
            })
        except Exception as e:
            self._handle_error("💥 خطأ في health check", e)
            return jsonify({"status": "error", "error": str(e)}), 500

    def debug_trend(self, symbol):
        """🔧 تصحيح حالة الاتجاه لرمز معين بالتوقيت السعودي"""
        try:
            trend_status = self.trade_manager.get_trend_status(symbol)
            trend_history = self.trade_manager.get_trend_history(symbol, 10)
            group_stats = self.group_manager.get_group_stats(symbol)
            
            return jsonify({
                "symbol": symbol,
                "trend_status": trend_status,
                "trend_history": trend_history,
                "group_stats": group_stats,
                "group_mapper_used": True,
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦"
            })
        except Exception as e:
            self._handle_error(f"💥 خطأ في debug_trend لـ {symbol}", e)
            return jsonify({"error": str(e)}), 500

    def debug_force_trend(self, symbol, direction):
        """🔧 تغيير اتجاه قسري بالتوقيت السعودي"""
        try:
            if direction not in ['bullish', 'bearish']:
                return jsonify({"error": "الاتجاه يجب أن يكون 'bullish' أو 'bearish'"}), 400
            
            success = self.trade_manager.force_trend_change(symbol, direction)
            
            return jsonify({
                "success": success,
                "symbol": symbol,
                "new_trend": direction,
                "group_mapper_used": True,
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦"
            })
        except Exception as e:
            self._handle_error(f"💥 خطأ في debug_force_trend لـ {symbol}", e)
            return jsonify({"error": str(e)}), 500

    def debug_force_trade(self, symbol, direction):
        """🔧 فتح صفقة قسرية بالتوقيت السعودي"""
        try:
            if direction not in ['buy', 'sell']:
                return jsonify({"error": "الاتجاه يجب أن يكون 'buy' أو 'sell'"}), 400
            
            success = self.group_manager.force_open_trade(symbol, direction)
            
            return jsonify({
                "success": success,
                "symbol": symbol,
                "direction": direction,
                "group_mapper_used": True,
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦"
            })
        except Exception as e:
            self._handle_error(f"💥 خطأ في debug_force_trade لـ {symbol}", e)
            return jsonify({"error": str(e)}), 500

    def debug_clear_trend(self, symbol):
        """🔧 مسح بيانات الاتجاه بالتوقيت السعودي"""
        try:
            success = self.trade_manager.clear_trend_data(symbol)
            
            return jsonify({
                "success": success,
                "symbol": symbol,
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦"
            })
        except Exception as e:
            self._handle_error(f"💥 خطأ في debug_clear_trend لـ {symbol}", e)
            return jsonify({"error": str(e)}), 500

    def debug_stats(self):
        """📊 الحصول على إحصائيات النظام"""
        try:
            stats = {
                "webhook_handler": {
                    "error_log_size": len(self._error_log),
                    "rate_limit_stats": {ip: len(times) for ip, times in self.request_counts.items()},
                    "total_clients": len(self.request_counts)
                },
                "debug_guard": self.debug_guard.get_debug_status(),
                "signal_processor": self.signal_processor.get_system_stats() if hasattr(self.signal_processor, 'get_system_stats') else {},
                "trade_manager": self.trade_manager.get_system_stats() if hasattr(self.trade_manager, 'get_system_stats') else {},
                "group_manager": self.group_manager.get_performance_metrics() if hasattr(self.group_manager, 'get_performance_metrics') else {},
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦"
            }
            return jsonify(stats)
        except Exception as e:
            self._handle_error("💥 خطأ في debug_stats", e)
            return jsonify({"error": str(e)}), 500

    def debug_cleanup_memory(self):
        """🧹 تنظيف ذاكرة النظام"""
        try:
            results = {}
            
            if hasattr(self.signal_processor, 'cleanup_memory'):
                results['signal_processor'] = self.signal_processor.cleanup_memory()
            
            if hasattr(self.trade_manager, 'cleanup_memory'):
                results['trade_manager'] = self.trade_manager.cleanup_memory()
            
            if hasattr(self.group_manager, 'cleanup_memory'):
                results['group_manager'] = self.group_manager.cleanup_memory()
            
            results['webhook_handler'] = self.cleanup_memory()
            
            # تنظيف DebugGuard
            if hasattr(self.debug_guard, 'cleanup_old_requests'):
                cleaned = self.debug_guard.cleanup_old_requests()
                results['debug_guard'] = {'cleaned_requests': cleaned}
            
            return jsonify({
                "success": True,
                "results": results,
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦"
            })
        except Exception as e:
            self._handle_error("💥 خطأ في debug_cleanup_memory", e)
            return jsonify({"error": str(e)}), 500

    # باقي الدوال تبقى كما هي (handle_webhook, _parse_incoming_request, etc.)
    # ... (نفس الكود الأصلي مع تعديلات طفيفة)

    def handle_webhook(self):
        """🎯 معالجة طلبات الويب هووك مع إصلاحات بالتوقيت السعودي"""
        current_time = saudi_time.format_time()
        logger.info(f"📥 📥 📥 طلب ويب هووك واردة جديدة - التوقيت: {current_time} 🇸🇦")
        
        try:
            client_ip = request.remote_addr or '0.0.0.0'
            
            if not self._check_rate_limit(client_ip):
                return jsonify({"error": "Rate limit exceeded"}), 429
                
            content_type = request.headers.get('Content-Type', '')
            content_length = request.headers.get('Content-Length', 0)
            user_agent = request.headers.get('User-Agent', '')
            
            logger.info(f"🌐 معلومات الطلب: IP={client_ip}, Content-Type={content_type}, Length={content_length} - التوقيت السعودي 🇸🇦")
            
            raw_data = request.get_data(as_text=True)
            if not raw_data or not raw_data.strip():
                logger.warning("⚠️ طلب فارغ - لا توجد بيانات")
                return jsonify({"error": "Empty request body"}), 400
            
            logger.info(f"📝 البيانات الواردة: {raw_data[:500]}{'...' if len(raw_data) > 500 else ''} - التوقيت السعودي 🇸🇦")
            
            signal_data = self._parse_incoming_request(raw_data)
            
            if not signal_data:
                logger.error("❌ فشل تحليل بيانات الإشارة")
                return jsonify({"error": "Invalid signal data"}), 400

            logger.info(f"🎯 تم تحليل الإشارة: رمز={signal_data['symbol']}, نوع={signal_data['signal_type']} - التوقيت السعودي 🇸🇦")

            result = self._process_signal(signal_data)
            logger.info(f"✅ تم معالجة الإشارة بنجاح - التوقيت السعودي 🇸🇦")
            
            return result

        except Exception as e:
            error_msg = f"💥 خطأ في معالجة الويب هووك: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._handle_error(error_msg, e)
            return jsonify({"error": "Internal server error"}), 500

    def _parse_incoming_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل الطلب الوارد بالتوقيت السعودي"""
        logger.debug("🔍 بدء تحليل الطلب الوارد...")
        
        content_type = (request.headers.get('Content-Type') or '').lower()
        
        if 'application/json' in content_type:
            logger.debug("📋 تحليل طلب JSON...")
            return self._parse_json_request(raw_data)
        else:
            logger.debug("📋 تحليل طلب نصي...")
            return self._parse_plaintext_request(raw_data)

    def _parse_json_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل طلب JSON بالتوقيت السعودي"""
        try:
            if not raw_data or not raw_data.strip():
                logger.warning("⚠️ بيانات JSON فارغة")
                return None
                
            data = json.loads(raw_data)
            logger.debug(f"📊 بيانات JSON المحللة: {data}")
            
            symbol = data.get('ticker') or data.get('symbol') or 'UNKNOWN'
            signal_type = data.get('signal') or data.get('action') or data.get('type') or 'UNKNOWN'
            
            symbol = str(symbol).strip().upper() if symbol else 'UNKNOWN'
            signal_type = str(signal_type).strip() if signal_type else 'UNKNOWN'
            
            if symbol == 'UNKNOWN' or signal_type == 'UNKNOWN':
                logger.warning(f"⚠️ رمز أو إشارة غير معروفة: symbol={symbol}, signal={signal_type}")
                return None
                
            result = {
                'symbol': symbol,
                'signal_type': signal_type,
                'timestamp': saudi_time.now().isoformat(),
                'timezone': 'Asia/Riyadh 🇸🇦',
                'raw_data': data
            }
            
            logger.info(f"✅ تم تحليل JSON: {symbol} -> {signal_type} - التوقيت السعودي 🇸🇦")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ خطأ في تحليل JSON، التحويل إلى نص: {e}")
            return self._parse_plaintext_request(raw_data)
        except Exception as e:
            self._handle_error("❌ خطأ في تحليل JSON", e, {'raw_data_preview': raw_data[:200]})
            return None

    def _parse_plaintext_request(self, raw_data: str) -> Optional[Dict]:
        """🎯 تحليل طلب نصي بالتوقيت السعودي"""
        try:
            logger.debug(f"🔍 تحليل النص الخام: {raw_data}")
            
            symbol, signal_type = self._extract_from_plaintext(raw_data)
            if not symbol or not signal_type or symbol == 'UNKNOWN' or signal_type == 'UNKNOWN':
                logger.warning(f"⚠️ فشل استخراج الرمز والإشارة من النص: {raw_data}")
                return None
                
            result = {
                'symbol': symbol.upper().strip(),
                'signal_type': signal_type.strip(),
                'timestamp': saudi_time.now().isoformat(),
                'timezone': 'Asia/Riyadh 🇸🇦',
                'raw_data': raw_data
            }
            
            logger.info(f"✅ تم تحليل النص: {symbol} -> {signal_type} - التوقيت السعودي 🇸🇦")
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

            match = re.search(r'(?i)ticker\s*:\s*([A-Z0-9]+).*?signal\s*:\s*([A-Za-z0-9_\-\s]+)', text, re.DOTALL)
            if match:
                symbol, signal = match.group(1), match.group(2)
                if symbol and signal:
                    logger.debug(f"✅ تم الاستخراج بنمط Ticker/Signal: {symbol} -> {signal} - التوقيت السعودي 🇸🇦")
                    return symbol.strip(), signal.strip()

            match = re.match(r'([A-Za-z0-9]+)\s+([A-Za-z0-9_\-\s]+)', text)
            if match:
                symbol, signal = match.group(1), match.group(2)
                if symbol and signal:
                    logger.debug(f"✅ تم الاستخراج بنمط Symbol/Signal: {symbol} -> {signal} - التوقيت السعودي 🇸🇦")
                    return symbol.strip(), signal.strip()

            if text.strip():
                words = text.split()
                if len(words) >= 2:
                    symbol = words[0]
                    signal = ' '.join(words[1:])
                    logger.debug(f"✅ تم الاستخراج بنمط الكلمات المتعددة: {symbol} -> {signal} - التوقيت السعودي 🇸🇦")
                    return symbol.strip(), signal.strip()
                else:
                    logger.warning(f"⚠️ نص غير كافٍ: {text} - التوقيت السعودي 🇸🇦")
                    return "UNKNOWN", text.strip()

            logger.warning("❌ فشل جميع أنماط الاستخراج - التوقيت السعودي 🇸🇦")
            return None, None
            
        except Exception as e:
            self._handle_error("💥 خطأ في استخراج البيانات من النص", e)
            return None, None

    def _process_signal(self, signal_data: Dict):
        """🎯 معالجة الإشارة مع إصلاحات بالتوقيت السعودي"""
        logger.info(f"🎯 بدء معالجة الإشارة: {signal_data['signal_type']} للرمز {signal_data['symbol']} - التوقيت السعودي 🇸🇦")
        
        classification = self.signal_processor.safe_classify_signal(signal_data)
        
        logger.info(f"🎯 تصنيف الإشارة: {signal_data['signal_type']} -> {classification} - التوقيت السعودي 🇸🇦")
        
        if classification == 'unknown':
            logger.warning(f"⚠️ إشارة غير معروفة: {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")
            self._handle_error("إشارة غير معروفة", None, {
                'signal_type': signal_data['signal_type'],
                'symbol': signal_data['symbol']
            })
            return jsonify({"error": f"Unknown signal: {signal_data['signal_type']}"}), 400

        try:
            if classification in ['trend', 'trend_confirm']:
                logger.info(f"📈 معالجة إشارة اتجاه: {classification} - التوقيت السعودي 🇸🇦")
                return self._handle_trend_signal(signal_data, classification)
            elif classification == 'exit':
                logger.info(f"🚪 معالجة إشارة خروج: {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")
                return self._handle_exit_signal(signal_data)
            elif classification in ['entry_bullish', 'entry_bearish', 'entry_bullish1', 
                                  'entry_bearish1', 'group3', 'group4', 'group5',
                                  'group3_bullish', 'group3_bearish',
                                  'group4_bullish', 'group4_bearish', 'group5_bullish', 'group5_bearish']:
                logger.info(f"🚀 معالجة إشارة دخول: {classification} - التوقيت السعودي 🇸🇦")
                return self._handle_entry_signal(signal_data, classification)
            else:
                logger.error(f"❌ تصنيف غير معالج: {classification} للإشارة: {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")
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
        """🎯 معالجة إشارات الاتجاه مع إصلاحات بالتوقيت السعودي"""
        symbol = signal_data['symbol']
        logger.info(f"📈 معالجة إشارة اتجاه لـ {symbol}: {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")
        
        should_report, old_trend, trend_signals = self.trade_manager.update_trend(symbol, classification, signal_data)
        current_trend = self.trade_manager.get_current_trend(symbol)
        
        logger.info(f"📊 نتيجة تحديث الاتجاه: {symbol} -> تغيير={should_report}, اتجاه قديم={old_trend}, عدد الإشارات={len(trend_signals)} - التوقيت السعودي 🇸🇦")
        
        signals_details = []
        if trend_signals:
            for signal in trend_signals:
                try:
                    if isinstance(signal, dict):
                        signal_type = signal.get('signal_type')
                        direction = signal.get('direction')
                    elif isinstance(signal, str):
                        signal_type = signal
                        direction = current_trend
                    else:
                        signal_type = str(signal) if signal else 'UNKNOWN'
                        direction = current_trend
                    
                    signals_details.append({
                        "signal_type": signal_type or 'UNKNOWN',
                        "direction": direction or current_trend or 'UNKNOWN'
                    })
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في معالجة إشارة الاتجاه: {e}")
                    continue
        
        response_data = {
            "status": "trend_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trend_changed": should_report,
            "current_trend": current_trend,
            "old_trend": old_trend or "UNKNOWN",
            "signals_used": len(signals_details),
            "signals_details": signals_details,
            "timezone": "Asia/Riyadh 🇸🇦"
        }

        if should_report:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            logger.info(f"🔍 تحقق الإشعار - التليجرام: {telegram_enabled}, الخارجي: {external_enabled} - التوقيت السعودي 🇸🇦")
            
            if telegram_enabled or external_enabled:
                self._send_trend_notification(signal_data, current_trend, old_trend, signals_details)
            else:
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعار الاتجاه - التوقيت السعودي 🇸🇦")
        
        return jsonify(response_data)

    def _handle_exit_signal(self, signal_data: Dict):
        """🎯 معالجة إشارات الخروج مع التحقق من وجود صفقات مفتوحة بالتوقيت السعودي"""
        symbol = signal_data['symbol']
        logger.info(f"🚪 معالجة إشارة خروج لـ {symbol}: {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")
        
        active_trades_count = self.trade_manager.get_active_trades_count(symbol)
        
        if active_trades_count == 0:
            logger.info(f"🔕 لا توجد صفقات مفتوحة لـ {symbol} - تم تجاهل إشارة الخروج - التوقيت السعودي 🇸🇦")
            return jsonify({
                "status": "exit_ignored", 
                "symbol": symbol,
                "signal_type": signal_data['signal_type'],
                "reason": "لا توجد صفقات مفتوحة للرمز",
                "active_trades": 0,
                "timezone": "Asia/Riyadh 🇸🇦"
            })
        
        closed_trades = self.trade_manager.handle_exit_signal(symbol, signal_data['signal_type'])
        
        remaining_trades = self.trade_manager.get_active_trades_count(symbol)
        
        logger.info(f"📊 نتيجة معالجة الخروج: {symbol} -> تم إغلاق {closed_trades} صفقة، الصفقات المتبقية: {remaining_trades} - التوقيت السعودي 🇸🇦")
        
        if closed_trades > 0 and self.notification_manager.should_send_message('exit'):
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if telegram_enabled or external_enabled:
                self._send_exit_notification(signal_data, closed_trades, remaining_trades)
            else:
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعار الخروج - التوقيت السعودي 🇸🇦")
        
        return jsonify({
            "status": "exit_processed", 
            "symbol": symbol,
            "signal_type": signal_data['signal_type'],
            "trades_closed": closed_trades,
            "remaining_trades": remaining_trades,
            "timezone": "Asia/Riyadh 🇸🇦"
        })

    def _handle_entry_signal(self, signal_data: Dict, classification: str):
        """🎯 معالجة إشارات الدخول بالتوقيت السعودي"""
        symbol = signal_data['symbol']
        logger.info(f"🚀 معالجة إشارة دخول لـ {symbol}: {classification} -> {signal_data['signal_type']} - التوقيت السعودي 🇸🇦")
        
        trade_results = self.group_manager.route_signal(symbol, signal_data, classification)
        
        logger.info(f"📊 نتائج التداول لـ {symbol}: {len(trade_results)} صفقات مفتوحة - التوقيت السعودي 🇸🇦")
        
        if trade_results and self.notification_manager.should_send_message('entry'):
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if telegram_enabled or external_enabled:
                self._send_entry_notifications(signal_data, trade_results)
            else:
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إرسال إشعارات الدخول - التوقيت السعودي 🇸🇦")
        
        return jsonify({
            "status": "entry_processed", 
            "symbol": symbol, 
            "classification": classification,
            "trades_opened": len(trade_results),
            "trade_details": trade_results,
            "timezone": "Asia/Riyadh 🇸🇦"
        })

    def _send_trend_notification(self, signal_data: Dict, new_trend: str, old_trend: Optional[str], trend_signals: List[Dict]):
        """🎯 إرسال إشعار الاتجاه مع التحسينات بالتوقيت السعودي"""
        try:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال - التوقيت السعودي 🇸🇦")
                return
                
            if not self.notification_manager.should_send_message('trend'):
                logger.info("🔕 إشعارات الاتجاه معطلة - تم تخطي الإرسال - التوقيت السعودي 🇸🇦")
                return
                
            from notifications.message_formatter import MessageFormatter
            message = MessageFormatter.format_trend_message(signal_data, new_trend, old_trend or "UNKNOWN", trend_signals)
            
            success = self.notification_manager.send_notifications(message, 'trend')
            logger.info(f"📤 إشعار الاتجاه: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'} - {len(trend_signals)} إشارة مستخدمة - التوقيت السعودي 🇸🇦")
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الاتجاه", e, {
                'symbol': signal_data.get('symbol'),
                'new_trend': new_trend,
                'old_trend': old_trend
            })

    def _send_exit_notification(self, signal_data: Dict, closed_trades: int, remaining_trades: int):
        """🎯 إرسال إشعار الخروج مع معلومات الصفقات المغلقة بالتوقيت السعودي"""
        try:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال - التوقيت السعودي 🇸🇦")
                return
                
            from notifications.message_formatter import MessageFormatter
            symbol = signal_data['symbol']
            total_active = self.trade_manager.get_active_trades_count()
            
            message = MessageFormatter.format_exit_message(symbol, signal_data['signal_type'], 
                                                         closed_trades, remaining_trades, total_active, self.config)
            success = self.notification_manager.send_notifications(message, 'exit')
            logger.info(f"📤 إشعار الخروج: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'} - {closed_trades} صفقة مغلقة - التوقيت السعودي 🇸🇦")
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعار الخروج", e, {
                'symbol': signal_data.get('symbol'),
                'signal_type': signal_data.get('signal_type')
            })

    def _send_entry_notifications(self, signal_data: Dict, trade_results: List[Dict]):
        """🎯 إرسال إشعارات الدخول بالتوقيت السعودي"""
        try:
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            if not (telegram_enabled or external_enabled):
                logger.info("🔕 جميع خدمات الإشعارات معطلة - تم تخطي الإرسال - التوقيت السعودي 🇸🇦")
                return
                
            from notifications.message_formatter import MessageFormatter
            
            for trade in trade_results:
                symbol = trade['symbol']
                current_trend = self.trade_manager.get_current_trend(symbol)
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
                logger.info(f"📤 إشعار الدخول: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'} - التوقيت السعودي 🇸🇦")
                
        except Exception as e:
            self._handle_error("⚠️ خطأ في إرسال إشعارات الدخول", e, {
                'trade_results_count': len(trade_results),
                'symbol': signal_data.get('symbol')
            })

    def get_error_log(self) -> List[Dict]:
        """الحصول على سجل الأخطاء"""
        return list(self._error_log)

    def get_system_status(self) -> Dict:
        """🎯 الحصول على حالة النظام المفصلة بالتوقيت السعودي"""
        try:
            return {
                "status": "active",
                "timestamp": saudi_time.now().isoformat(),
                "timezone": "Asia/Riyadh 🇸🇦",
                "active_trades": self.trade_manager.get_active_trades_count(),
                "pending_signals": sum(len(signals) for symbol_data in self.group_manager.pending_signals.values() 
                                     for signals in symbol_data.values() if hasattr(signals, '__len__')),
                "current_trends": len(self.trade_manager.current_trend),
                "error_count": len(self._error_log),
                "webhook_errors": len(self._error_log),
                "debug_protection": self.debug_guard.get_debug_status(),
                "rate_limit_stats": {
                    "total_clients": len(self.request_counts),
                    "active_requests": sum(len(times) for times in self.request_counts.values())
                }
            }
        except Exception as e:
            self._handle_error("💥 خطأ في الحصول على حالة النظام", e)
            return {"status": "error", "error": str(e)}

    def cleanup_memory(self) -> Dict:
        """🧹 تنظيف الذاكرة وإدارة التخزين"""
        try:
            current_time = saudi_time.now()
            cleaned_ips = 0
            for ip in list(self.request_counts.keys()):
                self.request_counts[ip] = [
                    req_time for req_time in self.request_counts[ip]
                    if (current_time - req_time).total_seconds() < self.rate_limit_period * 2
                ]
                if not self.request_counts[ip]:
                    del self.request_counts[ip]
                    cleaned_ips += 1
            
            error_log_cleaned = 0
            if len(self._error_log) > 500:
                error_log_cleaned = len(self._error_log) - 500
                for _ in range(error_log_cleaned):
                    if self._error_log:
                        self._error_log.popleft()
            
            # تنظيف DebugGuard
            debug_guard_cleaned = 0
            if hasattr(self.debug_guard, 'cleanup_old_requests'):
                debug_guard_cleaned = self.debug_guard.cleanup_old_requests()
            
            logger.info(f"🧹 تنظيف الذاكرة في webhook_handler: تم تنظيف {cleaned_ips} IP، {error_log_cleaned} خطأ، {debug_guard_cleaned} طلب تصحيح - التوقيت السعودي 🇸🇦")
            
            return {
                'cleaned_ips': cleaned_ips,
                'error_log_cleaned': error_log_cleaned,
                'debug_guard_cleaned': debug_guard_cleaned,
                'current_error_log_size': len(self._error_log),
                'current_request_counts': len(self.request_counts),
                'timestamp': current_time.isoformat(),
                'timezone': 'Asia/Riyadh 🇸🇦'
            }
            
        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف الذاكرة", e)
            return {'error': str(e)}
