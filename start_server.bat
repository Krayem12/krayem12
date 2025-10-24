@echo off
chcp 65001
echo 🚀 بدء تشغيل نظام إشارات التداول المدمج...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python غير مثبت على النظام!
    echo 💡 قم بتثبيت Python من https://python.org
    pause
    exit /b 1
)

echo 📦 تثبيت المتطلبات...
pip install -r requirements.txt

echo 🌐 تشغيل السيرفر على http://localhost:10000...
echo ⏹️  اضغط Ctrl+C لإيقاف السيرفر
echo.

python app.py

pause