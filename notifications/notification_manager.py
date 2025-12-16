import requests
import logging
import time
from typing import Optional, List, Dict
from collections import deque
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

class NotificationManager:
    """🎯 مدير الإشعارات مع Circuit Breaker و Retry Mechanism"""

    def __init__(self, config):
        self.config = config
        self._error_log = deque(maxlen=500)
        
        # 🛠️ إعداد Circuit Breaker
        self.telegram_circuit_state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.external_circuit_state = 'CLOSED'
        self.telegram_failures = 0
        self.external_failures = 0
        self.last_failure_time = {}
        self.circuit_reset_time = 60  # 60 ثانية قبل إعادة المحاولة
        
        # 🛠️ إعداد Retry Mechanism
        self.max_retries = 3
        self.retry_delay = 2  # 2 ثانية بين المحاولات
        
        # قفل للتزامن
        self.lock = threading.RLock()
        
        # 🛠️ التحقق من التهيئة
        logger.debug(f"🔧 تهيئة NotificationManager - EXTERNAL_SERVER_ENABLED: {self.config.get('EXTERNAL_SERVER_ENABLED')}")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append({
            'timestamp': datetime.now().isoformat(),
            'error': full_error
        })

    def _can_send_telegram(self) -> bool:
        """التحقق من إمكانية إرسال عبر Telegram"""
        with self.lock:
            if self.telegram_circuit_state == 'OPEN':
                # التحقق إذا حان وقت إعادة المحاولة
                if self.last_failure_time.get('telegram'):
                    time_since_failure = datetime.now() - self.last_failure_time['telegram']
                    if time_since_failure.total_seconds() > self.circuit_reset_time:
                        self.telegram_circuit_state = 'HALF_OPEN'
                        logger.info("🔄 Circuit Breaker لـ Telegram في وضع HALF_OPEN")
                    else:
                        logger.debug("🚫 Circuit Breaker لـ Telegram مفتوح")
                        return False
            return True

    def _can_send_external(self) -> bool:
        """التحقق من إمكانية إرسال للخادم الخارجي"""
        with self.lock:
            if self.external_circuit_state == 'OPEN':
                # التحقق إذا حان وقت إعادة المحاولة
                if self.last_failure_time.get('external'):
                    time_since_failure = datetime.now() - self.last_failure_time['external']
                    if time_since_failure.total_seconds() > self.circuit_reset_time:
                        self.external_circuit_state = 'HALF_OPEN'
                        logger.info("🔄 Circuit Breaker للخادم الخارجي في وضع HALF_OPEN")
                    else:
                        logger.debug("🚫 Circuit Breaker للخادم الخارجي مفتوح")
                        return False
            return True

    def _record_telegram_failure(self):
        """تسجيل فشل في Telegram"""
        with self.lock:
            self.telegram_failures += 1
            self.last_failure_time['telegram'] = datetime.now()
            
            if self.telegram_failures >= 3:  # بعد 3 فشل متتالي
                self.telegram_circuit_state = 'OPEN'
                logger.warning("🚫 Circuit Breaker لـ Telegram فُتح بسبب فشل متكرر")
                
                # إعادة تعيين بعد فترة
                threading.Timer(self.circuit_reset_time, self._reset_telegram_circuit).start()

    def _record_telegram_success(self):
        """تسجيل نجاح في Telegram"""
        with self.lock:
            self.telegram_failures = 0
            if self.telegram_circuit_state == 'HALF_OPEN':
                self.telegram_circuit_state = 'CLOSED'
                logger.info("✅ Circuit Breaker لـ Telegram أُغلق بعد نجاح")

    def _reset_telegram_circuit(self):
        """إعادة تعيين Circuit Breaker لـ Telegram"""
        with self.lock:
            if self.telegram_circuit_state == 'OPEN':
                self.telegram_circuit_state = 'HALF_OPEN'
                logger.info("🔄 إعادة تعيين Circuit Breaker لـ Telegram إلى HALF_OPEN")

    def _record_external_failure(self):
        """تسجيل فشل في الخادم الخارجي"""
        with self.lock:
            self.external_failures += 1
            self.last_failure_time['external'] = datetime.now()
            
            if self.external_failures >= 3:  # بعد 3 فشل متتالي
                self.external_circuit_state = 'OPEN'
                logger.warning("🚫 Circuit Breaker للخادم الخارجي فُتح بسبب فشل متكرر")
                
                # إعادة تعيين بعد فترة
                threading.Timer(self.circuit_reset_time, self._reset_external_circuit).start()

    def _record_external_success(self):
        """تسجيل نجاح في الخادم الخارجي"""
        with self.lock:
            self.external_failures = 0
            if self.external_circuit_state == 'HALF_OPEN':
                self.external_circuit_state = 'CLOSED'
                logger.info("✅ Circuit Breaker للخادم الخارجي أُغلق بعد نجاح")

    def _reset_external_circuit(self):
        """إعادة تعيين Circuit Breaker للخادم الخارجي"""
        with self.lock:
            if self.external_circuit_state == 'OPEN':
                self.external_circuit_state = 'HALF_OPEN'
                logger.info("🔄 إعادة تعيين Circuit Breaker للخادم الخارجي إلى HALF_OPEN")

    def should_send_message(self, message_type: str) -> bool:
        """التحقق من إمكانية إرسال الرسالة"""
        controls = {
            'trend': self.config.get('SEND_TREND_MESSAGES', False),
            'entry': self.config.get('SEND_ENTRY_MESSAGES', False),
            'exit': self.config.get('SEND_EXIT_MESSAGES', False),
            'confirmation': self.config.get('SEND_CONFIRMATION_MESSAGES', False),
            'general': self.config.get('SEND_GENERAL_MESSAGES', False)
        }

        result = controls.get(message_type, False)

        if self.config.get('DEBUG', False):
            logger.debug(f"🔔 تحكم في الرسائل: {message_type} -> {'✅ إرسال' if result else '❌ حظر'}")

        return result

    def send_notifications(self, message: str, message_type: str) -> bool:
        """إرسال الإشعارات مع معالجة محسنة للأخطاء"""
        # 🛠️ تحقق إضافي قوي
        if not hasattr(self, 'config'):
            logger.error("❌ كائن الإعدادات غير موجود في NotificationManager")
            return False
            
        if not isinstance(self.config, dict):
            logger.error("❌ الإعدادات ليست قاموسًا صالحًا")
            return False

        if not self.should_send_message(message_type):
            logger.debug(f"🔕 تم حظر الإرسال لنوع الرسالة: {message_type}")
            return False

        try:
            telegram_success = False
            external_success = False
            
            # 🛠️ تحقق مفصل مع تسجيل
            telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            
            logger.debug(f"🔍 حالة الخدمات - التليجرام: {telegram_enabled}, الخارجي: {external_enabled}")
            
            if telegram_enabled:
                telegram_success = self._send_telegram_with_retry(message)
                logger.debug(f"📱 نتيجة التليجرام: {telegram_success}")
            else:
                logger.debug("🔕 التليجرام معطل - تم تخطي الإرسال")
                
            if external_enabled:
                external_success = self._send_external_with_retry(message)
                logger.debug(f"🌐 نتيجة الخادم الخارجي: {external_success}")
            else:
                logger.debug("🔕 الخادم الخارجي معطل - تم تخطي الإرسال")

            return telegram_success or external_success

        except Exception as e:
            self._handle_error("💥 خطأ في إرسال الإشعارات", e)
            return False

    def _send_telegram_with_retry(self, message: str) -> bool:
        """إرسال إلى تليجرام مع Retry Mechanism"""
        if not self._can_send_telegram():
            return False
            
        for attempt in range(self.max_retries):
            try:
                success = self._send_telegram(message)
                if success:
                    self._record_telegram_success()
                    return True
                else:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"🔄 إعادة محاولة إرسال تليجرام ({attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
            except Exception as e:
                self._handle_error(f"❌ فشل محاولة إرسال تليجرام {attempt + 1}", e)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        self._record_telegram_failure()
        return False

    def _send_telegram(self, message: str) -> bool:
        """إرسال إلى تليجرام مع مهلة محسنة"""
        try:
            if not self.config.get('TELEGRAM_BOT_TOKEN') or not self.config.get('TELEGRAM_CHAT_ID'):
                logger.error("❌ بيانات تليجرام مفقودة")
                return False

            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            
            response = requests.post(url, json={
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=10)
            
            success = response.status_code == 200
            if success:
                logger.debug("✅ تم الإرسال لتليجرام")
            else:
                logger.error(f"❌ خطأ في تليجرام: {response.status_code} - {response.text}")
                
            return success
            
        except requests.exceptions.Timeout:
            logger.error("❌ انتهت مهلة تليجرام")
            return False
        except Exception as e:
            self._handle_error("❌ خطأ في تليجرام", e)
            return False

    def _send_external_with_retry(self, message: str) -> bool:
        """إرسال للخادم الخارجي مع Retry Mechanism"""
        if not self._can_send_external():
            return False
            
        for attempt in range(self.max_retries):
            try:
                success = self._send_external(message)
                if success:
                    self._record_external_success()
                    return True
                else:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"🔄 إعادة محاولة إرسال للخادم الخارجي ({attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
            except Exception as e:
                self._handle_error(f"❌ فشل محاولة إرسال للخادم الخارجي {attempt + 1}", e)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        self._record_external_failure()
        return False

    def _send_external(self, message: str) -> bool:
        """إرسال للخادم الخارجي مع التحقق المعزز"""
        try:
            # 🛠️ تحقق مزدوج ومحسّن
            external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
            if not external_enabled:
                logger.debug("🔕 الخادم الخارجي معطل - تم إلغاء الإرسال")
                return False
                
            external_url = self.config.get('EXTERNAL_SERVER_URL', '').strip()
            if not external_url:
                logger.error("❌ رابط الخادم الخارجي مفقود أو فارغ")
                return False

            if self.config.get('DEBUG', False):
                logger.info(f"🔗 محاولة الإرسال للخادم الخارجي: {external_url}")
            else:
                logger.debug(f"🔗 محاولة الإرسال للخادم الخارجي")

            response = requests.post(
                external_url,
                data=message.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=10
            )
            
            success = response.status_code in (200, 201, 204)
            if success:
                logger.debug("✅ تم الإرسال للخادم الخارجي")
            else:
                logger.error(f"❌ خطأ في الخادم الخارجي: {response.status_code} - {response.text}")
                
            return success
            
        except requests.exceptions.Timeout:
            logger.error("❌ انتهت مهلة الخادم الخارجي")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ خطأ في الاتصال بالخادم الخارجي")
            return False
        except Exception as e:
            self._handle_error("❌ خطأ في الخادم الخارجي", e)
            return False

    def get_error_log(self) -> List[Dict]:
        """الحصول على سجل الأخطاء"""
        return list(self._error_log)

    def get_circuit_status(self) -> Dict:
        """الحصول على حالة Circuit Breaker"""
        return {
            'telegram': {
                'state': self.telegram_circuit_state,
                'failures': self.telegram_failures,
                'last_failure': self.last_failure_time.get('telegram')
            },
            'external': {
                'state': self.external_circuit_state,
                'failures': self.external_failures,
                'last_failure': self.last_failure_time.get('external')
            }
        }

    def cleanup_memory(self) -> Dict:
        """🧹 تنظيف الذاكرة وإدارة التخزين"""
        try:
            # تنظيف error_log إذا تجاوز الحد
            error_log_cleaned = 0
            if len(self._error_log) > 500:
                error_log_cleaned = len(self._error_log) - 500
                for _ in range(error_log_cleaned):
                    if self._error_log:
                        self._error_log.popleft()
            
            logger.info(f"🧹 تنظيف الذاكرة في NotificationManager: تم تنظيف {error_log_cleaned} خطأ")
            
            return {
                'error_log_cleaned': error_log_cleaned,
                'current_error_log_size': len(self._error_log),
                'circuit_status': self.get_circuit_status(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self._handle_error("💥 خطأ في تنظيف الذاكرة", e)
            return {'error': str(e)}