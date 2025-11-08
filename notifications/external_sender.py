import requests

class ExternalSender:
    """مخصص للإرسال لخوادم خارجية فقط"""
    
    def __init__(self, config):
        self.config = config
    
    def send_message(self, message):
        """إرسال رسالة لخادم خارجي"""
        return self._send_external(message)
    
    def _send_external(self, message):
        """تنفيذ الإرسال الخارجي"""
        try:
            if not self.config['EXTERNAL_SERVER_URL']:
                print("❌ External server URL missing")
                return False

            response = requests.post(
                self.config['EXTERNAL_SERVER_URL'],
                data=message.encode('utf-8'),
                headers={"Content-Type": "text/plain; charset=utf-8"},
                timeout=(3, 10)
            )
            
            if response.status_code in (200, 201, 204):
                print("🌐 External server notification sent")
                return True
            else:
                print(f"❌ External server error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ External server error: {e}")
            return False