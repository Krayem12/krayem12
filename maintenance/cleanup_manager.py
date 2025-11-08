import schedule
import threading
import time
import os
import json
from datetime import datetime

class CleanupManager:
    """إدارة عمليات التنظيف والجدولة"""

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
            print(f"🕐 Daily cleanup scheduled at {cleanup_time} (server local time)")

            schedule.every().day.at(cleanup_time).do(self.daily_cleanup)

            self.scheduler_thread = threading.Thread(
                target=self.run_scheduler, 
                daemon=True,
                name="SchedulerThread"
            )
            self.scheduler_thread.start()
        else:
            print("🔕 Daily cleanup disabled")

    def run_scheduler(self):
        """Improved scheduler with shorter intervals and better error recovery"""
        print("⏰ Scheduler thread started")
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(60)

    def daily_cleanup(self):
        """Enhanced daily cleanup with backup verification"""
        print("\n" + "="*60)
        print("🧹 STARTING DAILY CLEANUP - ENHANCED")
        print("="*60)

        original_data = {
            'pending_signals': self.group_manager.pending_signals.copy(),
            'active_trades': self.trade_manager.active_trades.copy(),
            'symbol_trends': self.trade_manager.symbol_trends.copy(),
            'signal_history': self.trade_manager.signal_history.copy()
        }

        try:
            backup_success = self.backup_system_state()
            if not backup_success:
                print("❌ CLEANUP ABORTED: Backup failed, preserving all data")
                if self.notification_manager.should_send_message('general'):
                    self.notification_manager.send_notifications("❌ فشل النسخ الاحتياطي - تم إلغاء التنظيف اليومي", 'general')
                return False

            pending_signals_count = len(self.group_manager.pending_signals)
            active_trades_count = len([t for t in self.trade_manager.active_trades.values() if t['status'] == 'OPEN'])
            symbol_trends_count = len(self.trade_manager.symbol_trends)
            signal_history_count = len(self.trade_manager.signal_history)

            self.group_manager.pending_signals.clear()
            self.trade_manager.active_trades.clear()
            self.trade_manager.symbol_trends.clear()
            self.trade_manager.signal_history.clear()

            self.trade_manager.last_cleanup = datetime.now()

            print("✅ DAILY CLEANUP COMPLETED SUCCESSFULLY:")
            print(f"   📭 Cleared {pending_signals_count} pending signal groups")
            print(f"   📊 Cleared {active_trades_count} active trades")
            print(f"   📈 Cleared {symbol_trends_count} symbol trends")
            print(f"   📋 Cleared {signal_history_count} signal history records")
            print("🔄 All system data has been reset for the new day")
            print("="*60)

            if self.notification_manager.should_send_message('general'):
                cleanup_msg = self._format_cleanup_message(
                    pending_signals_count,
                    active_trades_count,
                    symbol_trends_count,
                    signal_history_count
                )
                self.notification_manager.send_notifications(cleanup_msg, 'general')

            return True

        except Exception as e:
            print(f"💥 CLEANUP FAILED: Restoring original data: {e}")
            
            self.group_manager.pending_signals = original_data['pending_signals']
            self.trade_manager.active_trades = original_data['active_trades']
            self.trade_manager.symbol_trends = original_data['symbol_trends']
            self.trade_manager.signal_history = original_data['signal_history']
            
            if self.notification_manager.should_send_message('general'):
                self.notification_manager.send_notifications(f"❌ فشل التنظيف اليومي: {str(e)}", 'general')
            
            return False

    def backup_system_state(self):
        """Enhanced backup system with proper error handling"""
        backup_success = False
        backup_file = None
        
        try:
            print("💾 Starting system backup...")
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "pending_signals": self._safe_pending_signals_snapshot(),
                "active_trades": self.trade_manager.active_trades.copy(),
                "symbol_trends": self.trade_manager.symbol_trends.copy(),
                "signal_history": [
                    {
                        "timestamp": (s['timestamp'].isoformat() if isinstance(s.get('timestamp'), datetime) else str(s.get('timestamp'))),
                        "signal": s.get('signal'),
                        "ticker": s.get('ticker')
                    } for s in self.trade_manager.signal_history[-500:]
                ],
                "backup_version": "v4_modular_group3"
            }

            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            file_name = f"{backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_file = file_name

            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
                backup_success = True
                print(f"✅ Backup saved: {file_name}")
            else:
                print("❌ Backup file verification failed")

        except Exception as e:
            print(f"❌ Backup Failed: {e}")
            if backup_file and os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except:
                    pass
        
        return backup_success

    def _safe_pending_signals_snapshot(self):
        """Make pending_signals JSON-safe (sets converted to lists)"""
        snap = {}
        for k, v in self.group_manager.pending_signals.items():
            snap[k] = {
                "unique_signals": list(v.get("unique_signals", [])),
                "signals_data": v.get("signals_data", []),
                "created_at": (v.get("created_at").isoformat() if isinstance(v.get("created_at"), datetime) else str(v.get("created_at"))),
                "updated_at": (v.get("updated_at").isoformat() if isinstance(v.get("updated_at"), datetime) else str(v.get("updated_at"))),
                "group_type": v.get("group_type")
            }
        return snap

    def _format_cleanup_message(self, signals_count, trades_count, trends_count, history_count):
        """Format daily cleanup notification message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

        return (
            "🧹 التنظيف اليومي التلقائي\n"
            "┏━━━━━━━━━━━━━━━━━━━━\n"
            f"┃ 📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"┃ 🕐 الوقت: {self.config['DAILY_CLEANUP_TIME']} (حسب وقت السيرفر)\n"
            f"┃ 📊 الإحصائيات:\n"
            f"┃   • مجموعات الإشارات: {signals_count}\n"
            f"┃   • الصفقات النشطة: {trades_count}\n"
            f"┃   • اتجاهات الرموز: {trends_count}\n"
            f"┃   • سجل الإشارات: {history_count}\n"
            f"┃ 🔄 الحالة: تم تنظيف جميع البيانات بنجاح\n"
            f"┃ 💫 النظام جاهز ليوم جديد من التداول\n"
            "┗━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {timestamp}"
        )