import requests
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class NotificationManager:
    """🎯 مدير الإشعارات مع تحسينات الأداء ومعالجة الأخطاء"""

    def __init__(self, config):
        self.config = config
        self._error_log = []
        
        # 🛠️ التحقق من التهيئة
        logger.debug(f"🔧 تهيئة NotificationManager - EXTERNAL_SERVER_ENABLED: {self.config.get('EXTERNAL_SERVER_ENABLED')}")

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
                telegram_success = self._send_telegram(message)
                logger.debug(f"📱 نتيجة التليجرام: {telegram_success}")
            else:
                logger.debug("🔕 التليجرام معطل - تم تخطي الإرسال")
                
            if external_enabled:
                external_success = self._send_external(message)
                logger.debug(f"🌐 نتيجة الخادم الخارجي: {external_success}")
            else:
                logger.debug("🔕 الخادم الخارجي معطل - تم تخطي الإرسال")

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

            if self.config['DEBUG']:
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
                logger.error(f"❌ خطأ في الخادم الخارجي: {response.status_code}")
                
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

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return self._error_log.copy()