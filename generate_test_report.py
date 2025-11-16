#!/usr/bin/env python3
"""
📊 مولد تقارير اختبارات نظام التداول
"""

import unittest
import sys
import os
import datetime
import json

def generate_test_report():
    """إنشاء تقرير مفصل عن الاختبارات"""
    print("📊 إنشاء تقرير الاختبارات...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    # اكتشاف وتشغيل الاختبارات
    loader = unittest.TestLoader()
    start_dir = os.path.join(current_dir, 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    # جمع البيانات للتقرير
    report_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'total_tests': result.testsRun,
        'passed': result.testsRun - len(result.failures) - len(result.errors),
        'failed': len(result.failures),
        'errors': len(result.errors),
        'test_modules': [],
        'details': {
            'failures': [],
            'errors': []
        }
    }
    
    # إضافة تفاصيل الإخفاقات
    for test, traceback in result.failures:
        report_data['details']['failures'].append({
            'test': str(test),
            'error': traceback.splitlines()[-1] if traceback else 'Unknown'
        })
    
    # إضافة تفاصيل الأخطاء
    for test, traceback in result.errors:
        report_data['details']['errors'].append({
            'test': str(test),
            'error': traceback.splitlines()[-1] if traceback else 'Unknown'
        })
    
    # حفظ التقرير
    report_file = os.path.join(current_dir, 'test_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    # عرض التقرير
    print("\n" + "="*50)
    print("📊 تقرير اختبارات نظام التداول الآلي")
    print("="*50)
    print(f"📅 التاريخ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🧪 إجمالي الاختبارات: {report_data['total_tests']}")
    print(f"✅ الناجحة: {report_data['passed']}")
    print(f"❌ الفاشلة: {report_data['failed']}")
    print(f"💥 الأخطاء: {report_data['errors']}")
    print(f"📈 نسبة النجاح: {(report_data['passed']/report_data['total_tests']*100):.1f}%" if report_data['total_tests'] > 0 else "0%")
    print(f"💾 التقرير مفصل: {report_file}")
    print("="*50)
    
    return report_data

if __name__ == '__main__':
    generate_test_report()