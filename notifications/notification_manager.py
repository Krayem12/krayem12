# notifications/notification_manager.py
import requests
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    """إدارة جميع أنواع الإشعارات والإرسال"""

    def __init__(self, config):
        self.config = config

    def should_send_message(self, message_type):
        """Check if message should be sent - STRICTLY FROM .ENV"""
        controls = {
            'trend': self.config['SEND_TREND_MESSAGES'],
            'entry': self.config['SEND_ENTRY_MESSAGES'],
            'exit': self.config['SEND_EXIT_MESSAGES'],
            'confirmation': self.config['SEND_CONFIRMATION_MESSAGES'],
            'general': self.config['SEND_GENERAL_MESSAGES']
        }

        result = controls.get(message_type, False)

        if self.config['DEBUG']:
            print(f"🔔 تحكم في الرسائل: {message_type} -> {'✅ إرسال' if result else '❌ حظر'}")

        return result

    def send_notifications(self, message, message_type):
        """Send notifications - STRICTLY CHECK ALL SETTINGS"""
        print(f"📤 محاولة إرسال إشعار: {message_type}")
        
        # التحقق من إعدادات الإرسال أولاً
        if not self.should_send_message(message_type):
            print(f"🔕 الإشعارات محجوبة لـ {message_type} حسب الإعدادات")
            return

        # إرسال لتليجرام إذا كان مفعل
        telegram_success = False
        if self.config['TELEGRAM_ENABLED']:
            telegram_success = self.send_telegram(message)
            if telegram_success:
                print("✅ تم الإرسال لتليجرام بنجاح")
            else:
                print("❌ فشل الإرسال لتليجرام")
        else:
            print("🔕 تليجرام غير مفعل")

        # إرسال للخادم الخارجي إذا كان مفعل
        external_success = False
        if self.config['EXTERNAL_SERVER_ENABLED']:
            external_success = self.send_external(message)
            if external_success:
                print("✅ تم الإرسال للخادم الخارجي بنجاح")
            else:
                print("❌ فشل الإرسال للخادم الخارجي")
        else:
            print("🔕 الخادم الخارجي غير مفعل")

        return telegram_success or external_success

    def send_telegram(self, message):
        """Improved Telegram sending with better timeout handling"""
        try:
            if not self.config['TELEGRAM_BOT_TOKEN'] or not self.config['TELEGRAM_CHAT_ID']:
                print("❌ بيانات تليجرام مفقودة")
                return False

            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            
            print(f"📤 جاري الإرسال لتليجرام...")
            
            response = requests.post(url, json={
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=(3, 10))
            
            if response.status_code == 200:
                print("📤 تم إرسال الإشعار لتليجرام بنجاح")
                return True
            else:
                print(f"❌ خطأ في تليجرام: {response.status_code}")
                logger.error(f"Telegram error: {response.status_code} | {response.text}")
                return False
        except requests.exceptions.Timeout:
            print("❌ انتهت مهلة تليجرام - الرسالة طويلة جداً أو مشكلة في الشبكة")
            logger.error("Telegram timeout")
            return False
        except Exception as e:
            print(f"❌ خطأ في تليجرام: {e}")
            logger.error(f"Telegram error: {e}")
            return False

    def send_external(self, message):
        """Improved external server sending with better timeout handling"""
        try:
            if not self.config['EXTERNAL_SERVER_URL']:
                print("❌ رابط الخادم الخارجي مفقود")
                return False

            print(f"🌐 جاري الإرسال للخادم الخارجي...")
            
            response = requests.post(
                self.config['EXTERNAL_SERVER_URL'],
                data=message.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=(3, 10)
            )
            
            if response.status_code in (200, 201, 204):
                print("🌐 تم إرسال الإشعار للخادم الخارجي بنجاح")
                return True
            else:
                print(f"❌ خطأ في الخادم الخارجي: {response.status_code}")
                logger.error(f"External server error: {response.status_code} | {response.text}")
                return False
        except requests.exceptions.Timeout:
            print("❌ انتهت مهلة الخادم الخارجي")
            logger.error("External server timeout")
            return False
        except Exception as e:
            print(f"❌ خطأ في الخادم الخارجي: {e}")
            logger.error(f"External server error: {e}")
            return False