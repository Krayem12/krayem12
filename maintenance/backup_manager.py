import os
import json
from datetime import datetime

class BackupManager:
    """مدير متخصص للنسخ الاحتياطي"""
    
    def __init__(self, config):
        self.config = config
        self.backup_dir = "backups"
        
    def create_backup(self, system_data):
        """إنشاء نسخة احتياطية للنظام"""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            backup_file = f"{self.backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(system_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Backup created: {backup_file}")
            return True
        except Exception as e:
            print(f"❌ Backup creation failed: {e}")
            return False
    
    def list_backups(self):
        """عرض قائمة النسخ الاحتياطية المتاحة"""
        try:
            if not os.path.exists(self.backup_dir):
                return []
            
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.startswith('backup_') and file.endswith('.json'):
                    file_path = os.path.join(self.backup_dir, file)
                    file_time = os.path.getmtime(file_path)
                    backups.append({
                        'name': file,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'created': datetime.fromtimestamp(file_time)
                    })
            
            return sorted(backups, key=lambda x: x['created'], reverse=True)
        except Exception as e:
            print(f"❌ Error listing backups: {e}")
            return []