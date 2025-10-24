import subprocess
import os

# مسار المشروع بعد فك الضغط
LOCAL_PATH = "c://nawal1"

# رابط مستودع GitHub
GITHUB_REPO = "https://github.com/Krayem12/krayem12.git"

# الدخول للمجلد
os.chdir(LOCAL_PATH)

# تنفيذ أوامر Git من داخل بايثون
subprocess.run(["git", "init"])
subprocess.run(["git", "branch", "-M", "main"])
subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
subprocess.run(["git", "remote", "add", "origin", GITHUB_REPO])
subprocess.run(["git", "add", "."])
subprocess.run(["git", "commit", "-m", "🚀 رفع المشروع"])
subprocess.run(["git", "push", "-u", "origin", "main", "--force"])

print("✅ تم رفع الملفات بنجاح إلى GitHub:", GITHUB_REPO)
