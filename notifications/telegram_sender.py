import requests

class TelegramSender:
    """مخصص لإرسال رسائل التليجرام فقط"""
    
    def __init__(self, config):
        self.config = config
    
    def send_message(self, message):
        """إرسال رسالة تليجرام"""
        return self._send_telegram(message)
    
    def _send_telegram(self, message):
        """تنفيذ إرسال التليجرام"""
        try:
            if not self.config['TELEGRAM_BOT_TOKEN'] or not self.config['TELEGRAM_CHAT_ID']:
                print("❌ Telegram credentials missing")
                return False

            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            
            response = requests.post(url, json={
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=(3, 10))
            
            if response.status_code == 200:
                print("📤 Telegram notification sent")
                return True
            else:
                print(f"❌ Telegram error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            return False