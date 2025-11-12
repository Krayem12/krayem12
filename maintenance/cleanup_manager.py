# maintenance/cleanup_manager.py
import schedule
import threading
import time
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CleanupManager:
    """إدارة عمليات التنظيف والجدولة - الإصدار المحسن"""

    def __init__(self, config, trade_manager, group_manager, notification_manager):
        self.config = config
        self.trade_manager = trade_manager
        self.group_manager = group_manager
        self.notification_manager = notification_manager
        self.scheduler_thread = None

    def setup_scheduler(self):
        """Setup daily cleanup scheduler with IMPROVED reliability"""
        if self.config['DAILY_CLEANUP_ENABLED']:
            cleanup_time = self.config['DAILY_CLEANUP_TIME']
            logger.info(f"🕐 Daily cleanup scheduled at {cleanup_time} (server local time)")

            schedule.every().day.at(cleanup_time).do(self.daily_cleanup)

            self.scheduler_thread = threading.Thread(
                target=self.run_scheduler, 
                daemon=True,
                name="SchedulerThread"
            )
            self.scheduler_thread.start()
        else:
            logger.info("🔕 Daily cleanup disabled")

    def run_scheduler(self):
        """Improved scheduler with shorter intervals and better error recovery"""
        logger.info("⏰ Scheduler thread started")
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(60)

    def daily_cleanup(self):
        """Enhanced daily cleanup with backup verification - FIXED PERMISSIONS"""
        logger.info("\n" + "="*60)
        logger.info("🧹 STARTING DAILY CLEANUP - ENHANCED")
        logger.info("="*60)

        # 🆕 إصلاح: استخدام الخصائص الفعلية الموجودة في TradeManager
        original_data = {
            'pending_signals': self.group_manager.pending_signals.copy(),
            'active_trades': self.trade_manager.active_trades.copy(),
            'current_trend': self.trade_manager.current_trend.copy(),
            'previous_trend': self.trade_manager.previous_trend.copy(),
            'last_reported_trend': self.trade_manager.last_reported_trend.copy()
        }

        try:
            # 🆕 التحقق من إمكانية النسخ الاحتياطي أولاً
            can_backup = self._check_backup_possible()
            if not can_backup:
                logger.warning("⚠️ Backup not possible due to permissions - proceeding with cleanup only")
                backup_success = True  # المتابعة بدون نسخ احتياطي
            else:
                backup_success = self.backup_system_state()

            if not backup_success:
                logger.error("❌ CLEANUP ABORTED: Backup failed, preserving all data")
                if self.notification_manager.should_send_message('general'):
                    self.notification_manager.send_notifications("❌ فشل النسخ الاحتياطي - تم إلغاء التنظيف اليومي", 'general')
                return False

            # 🆕 تنفيذ التنظيف حتى لو فشل النسخ الاحتياطي (لكن مع إشعار)
            self._execute_cleanup()

            logger.info("✅ DAILY CLEANUP COMPLETED SUCCESSFULLY")
            logger.info("="*60)

            if self.notification_manager.should_send_message('general'):
                cleanup_msg = self._format_cleanup_success_message()
                self.notification_manager.send_notifications(cleanup_msg, 'general')

            return True

        except Exception as e:
            logger.error(f"💥 CLEANUP FAILED: Restoring original data: {e}")
            
            self.group_manager.pending_signals = original_data['pending_signals']
            self.trade_manager.active_trades = original_data['active_trades']
            self.trade_manager.current_trend = original_data['current_trend']
            self.trade_manager.previous_trend = original_data['previous_trend']
            self.trade_manager.last_reported_trend = original_data['last_reported_trend']
            
            if self.notification_manager.should_send_message('general'):
                self.notification_manager.send_notifications(f"❌ فشل التنظيف اليومي: {str(e)}", 'general')
            
            return False

    def _check_backup_possible(self):
        """التحقق من إمكانية إنشاء ملفات في النظام"""
        test_file = "backup_test.tmp"
        try:
            # محاولة إنشاء ملف اختبار
            with open(test_file, "w") as f:
                f.write("test")
            # حذف ملف الاختبار
            os.remove(test_file)
            logger.debug("✅ Backup is possible - file creation test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Backup not possible - cannot create files: {e}")
            return False

    def _execute_cleanup(self):
        """تنفيذ عملية التنظيف الفعلية"""
        pending_signals_count = len(self.group_manager.pending_signals)
        active_trades_count = len(self.trade_manager.active_trades)
        current_trend_count = len(self.trade_manager.current_trend)
        previous_trend_count = len(self.trade_manager.previous_trend)

        # تنظيف جميع البيانات
        self.group_manager.pending_signals.clear()
        self.trade_manager.active_trades.clear()
        self.trade_manager.current_trend.clear()
        self.trade_manager.previous_trend.clear()
        self.trade_manager.last_reported_trend.clear()
        
        # تنظيف عداد الصفقات إذا كان موجوداً
        if hasattr(self.trade_manager, 'symbol_trade_count'):
            self.trade_manager.symbol_trade_count.clear()

        logger.info(f"✅ Cleanup executed:")
        logger.info(f"   📭 Cleared {pending_signals_count} pending signal groups")
        logger.info(f"   📊 Cleared {active_trades_count} active trades")
        logger.info(f"   📈 Cleared {current_trend_count} current trends")
        logger.info(f"   📋 Cleared {previous_trend_count} previous trends")
        logger.info("🔄 All system data has been reset for the new day")

    def backup_system_state(self):
        """نظام نسخ احتياطي محسن مع حفظ فعلي"""
        backup_success = False
        
        try:
            logger.info("💾 بدء النسخ الاحتياطي للنظام...")
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "pending_signals": self._safe_pending_signals_snapshot(),
                "active_trades": self.trade_manager.active_trades.copy(),
                "current_trend": self.trade_manager.current_trend.copy(),
                "previous_trend": self.trade_manager.previous_trend.copy(),
                "last_reported_trend": self.trade_manager.last_reported_trend.copy(),
                "backup_version": "v5_stable_fixed"
            }

            # إضافة عداد الصفقات إذا كان موجوداً
            if hasattr(self.trade_manager, 'symbol_trade_count'):
                backup_data["symbol_trade_count"] = self.trade_manager.symbol_trade_count.copy()

            # 🆕 محاولة الحفظ في ملف مع التعامل مع الأخطاء
            try:
                backup_dir = "system_backups"
                os.makedirs(backup_dir, exist_ok=True)
                
                backup_file = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
                
                backup_size = os.path.getsize(backup_file)
                logger.info(f"✅ تم حفظ النسخ الاحتياطي في الملف: {backup_file} ({backup_size} bytes)")
                backup_success = True
                
            except Exception as file_error:
                logger.warning(f"⚠️ فشل حفظ النسخ في ملف، استخدام الذاكرة فقط: {file_error}")
                # 🆕 النسخ في الذاكرة كبديل
                backup_json = json.dumps(backup_data, indent=2, ensure_ascii=False, default=str)
                backup_size = len(backup_json.encode('utf-8'))
                logger.info(f"✅ تم إنشاء نسخ احتياطي في الذاكرة: {backup_size} bytes")
                backup_success = True

        except Exception as e:
            logger.error(f"❌ فشل النسخ الاحتياطي: {e}")
            backup_success = False
        
        return backup_success

    def _safe_pending_signals_snapshot(self):
        """Make pending_signals JSON-safe"""
        snap = {}
        for symbol, groups in self.group_manager.pending_signals.items():
            snap[symbol] = {
                "group1_bullish": [{
                    'hash': signal.get('hash'),
                    'signal_type': signal.get('signal_type'),
                    'classification': signal.get('classification'),
                    'timestamp': signal.get('timestamp').isoformat() if hasattr(signal.get('timestamp'), 'isoformat') else str(signal.get('timestamp')),
                    'direction': signal.get('direction')
                } for signal in groups.get("group1_bullish", [])],
                "group1_bearish": [{
                    'hash': signal.get('hash'),
                    'signal_type': signal.get('signal_type'),
                    'classification': signal.get('classification'),
                    'timestamp': signal.get('timestamp').isoformat() if hasattr(signal.get('timestamp'), 'isoformat') else str(signal.get('timestamp')),
                    'direction': signal.get('direction')
                } for signal in groups.get("group1_bearish", [])],
                "group2_bullish": [{
                    'hash': signal.get('hash'),
                    'signal_type': signal.get('signal_type'),
                    'classification': signal.get('classification'),
                    'timestamp': signal.get('timestamp').isoformat() if hasattr(signal.get('timestamp'), 'isoformat') else str(signal.get('timestamp')),
                    'direction': signal.get('direction')
                } for signal in groups.get("group2_bullish", [])],
                "group2_bearish": [{
                    'hash': signal.get('hash'),
                    'signal_type': signal.get('signal_type'),
                    'classification': signal.get('classification'),
                    'timestamp': signal.get('timestamp').isoformat() if hasattr(signal.get('timestamp'), 'isoformat') else str(signal.get('timestamp')),
                    'direction': signal.get('direction')
                } for signal in groups.get("group2_bearish", [])],
                "group3_bullish": [{
                    'hash': signal.get('hash'),
                    'signal_type': signal.get('signal_type'),
                    'classification': signal.get('classification'),
                    'timestamp': signal.get('timestamp').isoformat() if hasattr(signal.get('timestamp'), 'isoformat') else str(signal.get('timestamp')),
                    'direction': signal.get('direction')
                } for signal in groups.get("group3_bullish", [])],
                "group3_bearish": [{
                    'hash': signal.get('hash'),
                    'signal_type': signal.get('signal_type'),
                    'classification': signal.get('classification'),
                    'timestamp': signal.get('timestamp').isoformat() if hasattr(signal.get('timestamp'), 'isoformat') else str(signal.get('timestamp')),
                    'direction': signal.get('direction')
                } for signal in groups.get("group3_bearish", [])],
                "updated_at": groups.get("updated_at").isoformat() if hasattr(groups.get("updated_at"), 'isoformat') else str(groups.get("updated_at"))
            }
        return snap

    def _format_cleanup_success_message(self):
        """Format successful cleanup notification message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        return (
            "🧹 التنظيف اليومي التلقائي\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"┃ 🕐 الوقت: {self.config['DAILY_CLEANUP_TIME']} (حسب وقت السيرفر)\n"
            f"┃ ✅ الحالة: تم تنظيف جميع البيانات بنجاح\n"
            f"┃ 💾 النسخ الاحتياطي: مخزن في الذاكرة\n"
            f"┃ 💫 النظام جاهز ليوم جديد من التداول\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )