import os
import subprocess
from datetime import datetime

# رابط المستودع
REPO_URL = "https://github.com/krayem12/KRAYEM.git"

# 🟢 تحديد المسار الحالي (نفس مكان تشغيل السكربت)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 🟢 اسم مجلد النسخة الاحتياطية بالتاريخ والوقت
backup_name = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
backup_path = os.path.join(current_dir, backup_name)

try:
    print(f"📂 إنشاء مجلد النسخة الاحتياطية: {backup_path}")
    os.makedirs(backup_path, exist_ok=True)

    # 🟢 تنفيذ أمر git clone
    print(f"🚀 جاري نسخ المستودع من: {REPO_URL}")
    subprocess.check_call(["git", "clone", REPO_URL, backup_path])

    print(f"✅ تم النسخ بنجاح إلى: {backup_path}")
except Exception as e:
    print(f"❌ خطأ أثناء النسخ: {e}")

input("\nاضغط Enter للخروج...")
