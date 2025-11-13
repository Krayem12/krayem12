# notifications/notification_manager.py
import requests
import logging
from typing import Optional, List  # أضفت List هنا

logger = logging.getLogger(__name__)

class NotificationManager:
    """🎯 مدير الإشعارات مع تحسينات الأداء ومعالجة الأخطاء"""

    def __init__(self, config):
        self.config = config
        self._error_log = []

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append(full_error)

    def should_send_message(self, message_type: str) -> bool:
        """التحقق من إمكانية إرسال الرسالة"""
        controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }

        result = controls.get(message_type, False)

        if self.config['DEBUG']:
            logger.debug(f"🔔 تحكم في الرسائل: {message_type} -> {'✅ إرسال' if result else '❌ حظر'}")

        return result

    def send_notifications(self, message: str, message_type: str) -> bool:
        """إرسال الإشعارات مع معالجة محسنة للأخطاء"""
        if not self.should_send_message(message_type):
            return False

        try:
            telegram_success = self._send_telegram(message) if self.config['TELEGRAM_ENABLED'] else False
            external_success = self._send_external(message) if self.config['EXTERNAL_SERVER_ENABLED'] else False

            return telegram_success or external_success

        except Exception as e:
            self._handle_error("💥 خطأ في إرسال الإشعارات", e)
            return False

    def _send_telegram(self, message: str) -> bool:
        """إرسال إلى تليجرام مع مهلة محسنة"""
        try:
            if not self.config['TELEGRAM_BOT_TOKEN'] or not self.config['TELEGRAM_CHAT_ID']:
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
                logger.error(f"❌ خطأ في تليجرام: {response.status_code}")
                
            return success
            
        except requests.exceptions.Timeout:
            logger.error("❌ انتهت مهلة تليجرام")
            return False
        except Exception as e:
            self._handle_error("❌ خطأ في تليجرام", e)
            return False

    def _send_external(self, message: str) -> bool:
        """إرسال للخادم الخارجي"""
        try:
            if not self.config['EXTERNAL_SERVER_URL']:
                logger.error("❌ رابط الخادم الخارجي مفقود")
                return False

            response = requests.post(
                self.config['EXTERNAL_SERVER_URL'],
                data=message.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=10
            )
            
            success = response.status_code in (200, 201, 204)
            if success:
                logger.debug("✅ تم الإرسال للخادم الخارجي")
            else:
                logger.error(f"❌ خطأ في الخادم الخارجي: {response.status_code}")
                
            return success
            
        except requests.exceptions.Timeout:
            logger.error("❌ انتهت مهلة الخادم الخارجي")
            return False
        except Exception as e:
            self._handle_error("❌ خطأ في الخادم الخارجي", e)
            return False

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()