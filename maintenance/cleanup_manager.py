import schedule
import threading
import time
import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from collections import deque

# 🛠️ الإصلاح: استيراد صحيح لـ saudi_time
try:
    from utils.time_utils import saudi_time
except ImportError:
    try:
        from ..utils.time_utils import saudi_time
    except ImportError:
        # ✅ بديل إذا فشل الاستيراد
        import pytz
        from datetime import datetime
        
        class SaudiTime:
            def __init__(self):
                self.timezone = pytz.timezone('Asia/Riyadh')
            
            def now(self):
                return datetime.now(self.timezone)
            
            def format_time(self, dt=None):
                if dt is None:
                    dt = self.now()
                return dt.strftime('%Y-%m-%d %I:%M:%S %p')
        
        saudi_time = SaudiTime()

logger = logging.getLogger(__name__)

class CleanupManager:
    """🧹 مدير التنظيف بالتوقيت السعودي"""

    def __init__(self, config, trade_manager, group_manager, notification_manager):
        self.config = config
        self.trade_manager = trade_manager
        self.group_manager = group_manager
        self.notification_manager = notification_manager
        self.scheduler_thread = None
        self.backup_history = deque(maxlen=5)
        self._error_log = deque(maxlen=1000)
        
        # 🛠️ التحقق من التهيئة
        logger.debug(f"🔧 تهيئة CleanupManager - EXTERNAL_SERVER_ENABLED: {self.config.get('EXTERNAL_SERVER_ENABLED')}")
        logger.info(f"🧹 تم تهيئة مدير التنظيف بالتوقيت السعودي - وقت التنظيف: {self.config['DAILY_CLEANUP_TIME']} 🇸🇦")

    def _handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """معالجة موحدة للأخطاء"""
        full_error = f"{error_msg}: {exception}" if exception else error_msg
        logger.error(full_error)
        self._error_log.append(full_error)

    def setup_scheduler(self) -> None:
        """إعداد الجدولة مع معالجة محسنة للأخطاء بالتوقيت السعودي"""
        if self.config['DAILY_CLEANUP_ENABLED']:
            cleanup_time = self.config['DAILY_CLEANUP_TIME']
            logger.info(f"🕐 تم جدولة التنظيف اليومي الساعة {cleanup_time} بالتوقيت السعودي 🇸🇦")

            schedule.every().day.at(cleanup_time).do(self.daily_cleanup)

            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler, 
                daemon=True,
                name="CleanupScheduler"
            )
            self.scheduler_thread.start()
        else:
            logger.info("🔕 التنظيف اليومي معطل")

    def _run_scheduler(self) -> None:
        """تشغيل المجدول مع التعافي من الأخطاء"""
        logger.info("⏰ بدء تشغيل مجدول التنظيف بالتوقيت السعودي 🇸🇦")
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except Exception as e:
                self._handle_error("❌ خطأ في المجدول", e)
                time.sleep(60)

    def daily_cleanup(self) -> bool:
        """التنظيف اليومي مع نسخ احتياطي محسن بالتوقيت السعودي"""
        current_time = saudi_time.format_time()
        logger.info("\n" + "="*50)
        logger.info(f"🧹 بدء التنظيف اليومي المحسن - التوقيت: {current_time} 🇸🇦")
        logger.info("="*50)

        try:
            # 💾 نسخ احتياطي للبيانات
            original_data = self._create_system_snapshot()
            
            # التحقق من إمكانية النسخ الاحتياطي
            if not self._check_backup_possible():
                logger.warning("⚠️ لا يمكن إنشاء نسخ احتياطي - المتابعة بدون نسخ")
                backup_success = True
            else:
                backup_success = self.backup_system_state()

            if not backup_success:
                logger.error("❌ تم إلغاء التنظيف بسبب فشل النسخ الاحتياطي")
                self._send_cleanup_notification("فشل")
                return False

            # 🧹 تنفيذ التنظيف
            self._execute_cleanup()
            logger.info("✅ تم التنظيف اليومي بنجاح")

            self._send_cleanup_notification("نجاح")
            return True

        except Exception as e:
            self._handle_error("💥 فشل التنظيف اليومي", e)
            self._send_cleanup_notification("فشل")
            return False

    def _create_system_snapshot(self) -> Dict:
        """إنشاء لقطة للنظام للنسخ الاحتياطي بالتوقيت السعودي"""
        return {
            'pending_signals': self._safe_pending_signals_snapshot(),
            'active_trades': self.trade_manager.active_trades.copy(),
            'current_trend': self.trade_manager.current_trend.copy(),
            'previous_trend': self.trade_manager.previous_trend.copy(),
            'last_reported_trend': self.trade_manager.last_reported_trend.copy(),
            'snapshot_time': saudi_time.now().isoformat(),
            'timezone': 'Asia/Riyadh 🇸🇦'
        }

    def _safe_pending_signals_snapshot(self) -> Dict:
        """إنشاء لقطة آمنة للإشارات المعلقة بالتوقيت السعودي"""
        snap = {}
        try:
            for symbol, groups in self.group_manager.pending_signals.items():
                snap[symbol] = {}
                for group_type, signals in groups.items():
                    if group_type in ['created_at', 'updated_at']:
                        snap[symbol][group_type] = groups[group_type]
                        continue
                    
                    snap[symbol][group_type] = [{
                        'hash': signal.get('hash'),
                        'signal_type': signal.get('signal_type'),
                        'classification': signal.get('classification'),
                        'timestamp': signal.get('timestamp').isoformat() if hasattr(signal.get('timestamp'), 'isoformat') else str(signal.get('timestamp')),
                        'direction': signal.get('direction'),
                        'timezone': 'Asia/Riyadh 🇸🇦'
                    } for signal in signals]
        except Exception as e:
            self._handle_error("⚠️ خطأ في إنشاء لقطة الإشارات", e)
        
        return snap

    def _execute_cleanup(self) -> None:
        """تنفيذ عملية التنظيف الفعلية"""
        try:
            # جمع الإحصائيات قبل التنظيف
            stats_before = {
                'pending_signals': len(self.group_manager.pending_signals),
                'active_trades': len(self.trade_manager.active_trades),
                'current_trend': len(self.trade_manager.current_trend)
            }

            # التنظيف
            self.group_manager.pending_signals.clear()
            self.trade_manager.active_trades.clear()
            self.trade_manager.current_trend.clear()
            self.trade_manager.previous_trend.clear()
            self.trade_manager.last_reported_trend.clear()
            
            # ✅ التحقق من وجود المتغير قبل مسحه
            if hasattr(self.trade_manager, 'symbol_trade_count'):
                self.trade_manager.symbol_trade_count.clear()

            logger.info(f"✅ تم التنظيف: {stats_before['pending_signals']} إشارة, {stats_before['active_trades']} صفقة")

        except Exception as e:
            self._handle_error("💥 خطأ في تنفيذ التنظيف", e)
            raise

    def backup_system_state(self) -> bool:
        """نسخ احتياطي محسن للنظام بالتوقيت السعودي"""
        try:
            logger.info("💾 بدء النسخ الاحتياطي بالتوقيت السعودي...")
            
            backup_data = self._create_system_snapshot()
            backup_data.update({
                "backup_version": "v2_enhanced_saudi_time",
                "system_metrics": self._get_system_metrics()
            })

            # محاولة الحفظ في ملف
            backup_success = self._save_backup_to_file(backup_data)
            
            if backup_success:
                logger.info("✅ تم النسخ الاحتياطي بنجاح")
            else:
                logger.warning("⚠️ تم النسخ في الذاكرة فقط")
                
            return True

        except Exception as e:
            self._handle_error("❌ فشل النسخ الاحتياطي", e)
            return False

    def _save_backup_to_file(self, backup_data: Dict) -> bool:
        """حفظ النسخ الاحتياطي في ملف بالتوقيت السعودي"""
        try:
            backup_dir = "system_backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            # استخدام التوقيت السعودي في اسم الملف
            backup_file = os.path.join(backup_dir, f"backup_{saudi_time.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.backup_history.append({
                'file': backup_file,
                'size': os.path.getsize(backup_file),
                'timestamp': saudi_time.now(),
                'timezone': 'Asia/Riyadh 🇸🇦'
            })
            
            return True
            
        except Exception as e:
            self._handle_error("⚠️ فشل حفظ النسخ في ملف", e)
            return False

    def _check_backup_possible(self) -> bool:
        """التحقق من إمكانية إنشاء نسخ احتياطية"""
        try:
            test_file = "backup_test.tmp"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception as e:
            self._handle_error("❌ لا يمكن إنشاء ملفات نسخ احتياطي", e)
            return False

    def _get_system_metrics(self) -> Dict:
        """الحصول على مقاييس النظام بالتوقيت السعودي"""
        return {
            'cleanup_time': saudi_time.now().isoformat(),
            'timezone': 'Asia/Riyadh 🇸🇦',
            'backup_count': len(self.backup_history),
            'error_count': len(self._error_log)
        }

    def _send_cleanup_notification(self, status: str) -> None:
        """إرسال إشعار التنظيف مع التحقق من الخدمات"""
        # 🛠️ تحقق مزدوج من الخدمات المفعلة
        if not self.notification_manager:
            logger.debug("🔕 مدير الإشعارات غير متوفر - تم تخطي إشعار التنظيف")
            return
            
        telegram_enabled = self.config.get('TELEGRAM_ENABLED', False)
        external_enabled = self.config.get('EXTERNAL_SERVER_ENABLED', False)
        
        if not (telegram_enabled or external_enabled):
            logger.debug("🔕 جميع خدمات الإشعارات معطلة - تم تخطي إشعار التنظيف")
            return
            
        if not self.notification_manager.should_send_message('general'):
            logger.debug("🔕 الرسائل العامة معطلة - تم تخطي إشعار التنظيف")
            return

        message = self._format_cleanup_message(status)
        success = self.notification_manager.send_notifications(message, 'general')
        logger.info(f"📤 إشعار التنظيف: {'✅ تم الإرسال' if success else '❌ فشل الإرسال'}")

    def _format_cleanup_message(self, status: str) -> str:
        """تنسيق رسالة التنظيف بالتوقيت السعودي"""
        timestamp = saudi_time.format_time()
        status_icon = "✅" if status == "نجاح" else "❌"

        return (
            "🧹 التنظيف اليومي التلقائي\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 📅 التاريخ: {saudi_time.now().strftime('%Y-%m-%d')}\n"
            f"┃ 🕐 الوقت: {self.config['DAILY_CLEANUP_TIME']} 🇸🇦\n"
            f"┃ {status_icon} الحالة: {status}\n"
            f"┃ 💾 النسخ الاحتياطي: {len(self.backup_history)} ملف\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp} 🇸🇦"
        )

    def get_error_log(self) -> List[str]:
        """الحصول على سجل الأخطاء"""
        return list(self._error_log)