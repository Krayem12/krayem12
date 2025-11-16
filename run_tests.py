#!/usr/bin/env python3
"""
🚀 برنامج تشغيل اختبارات نظام التداول الآلي - الإصدار المحسّن
"""

import unittest
import sys
import os
import argparse
import glob

def discover_all_tests():
    """اكتشاف جميع الاختبارات في المشروع"""
    print("🔍 اكتشاف جميع الاختبارات...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    test_files = []
    
    # البحث عن جميع ملفات الاختبار
    patterns = [
        "tests/unit/test_*.py",
        "tests/integration/test_*.py", 
        "tests/performance/test_*.py"
    ]
    
    for pattern in patterns:
        files = glob.glob(os.path.join(current_dir, pattern))
        test_files.extend(files)
    
    print(f"📁 تم العثور على {len(test_files)} ملف اختبار:")
    for file in test_files:
        print(f"   - {os.path.basename(file)}")
    
    return test_files

def run_all_tests():
    """تشغيل جميع الاختبارات - الإصدار المحسّن"""
    print("🧪 بدء تشغيل اختبارات نظام التداول الآلي...")
    
    test_files = discover_all_tests()
    
    if not test_files:
        print("❌ لم يتم العثور على أي ملفات اختبار!")
        return False
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # تحميل جميع الاختبارات
    for test_file in test_files:
        try:
            # تحويل مسار الملف إلى اسم وحدة
            module_name = os.path.splitext(test_file)[0].replace(os.sep, '.')
            if module_name.startswith('.'):
                module_name = module_name[1:]
            
            print(f"📦 تحميل: {module_name}")
            tests = loader.loadTestsFromName(module_name)
            suite.addTests(tests)
            
        except Exception as e:
            print(f"⚠️  خطأ في تحميل {test_file}: {e}")
    
    if suite.countTestCases() == 0:
        print("❌ لم يتم تحميل أي اختبارات!")
        return False
    
    print(f"✅ تم تحميل {suite.countTestCases()} اختبار")
    
    # تشغيل الاختبارات
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # عرض النتائج المفصلة
    print(f"\n📊 نتائج الاختبار:")
    print(f"   ✅ الاختبارات الناجحة: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ الاختبارات الفاشلة: {len(result.failures)}")
    print(f"   💥 الأخطاء: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ الاختبارات الفاشلة:")
        for test, traceback in result.failures:
            print(f"   - {test}")
            print(f"     {traceback.splitlines()[-1]}")
    
    if result.errors:
        print(f"\n💥 أخطاء الاختبار:")
        for test, traceback in result.errors:
            print(f"   - {test}")
            print(f"     {traceback.splitlines()[-1]}")
    
    return result.wasSuccessful()

def run_specific_test(test_pattern):
    """تشغيل اختبار محدد - الإصدار المحسّن"""
    print(f"🎯 تشغيل اختبار: {test_pattern}")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    try:
        loader = unittest.TestLoader()
        
        if '.' in test_pattern:
            # إذا كان اسم وحدة كامل
            suite = loader.loadTestsFromName(test_pattern)
        else:
            # إذا كان نمط اسم
            suite = loader.loadTestsFromName(f'tests.unit.{test_pattern}')
        
        if suite.countTestCases() == 0:
            # محاولة الاكتشاف
            suite = loader.discover('tests', pattern=f'*{test_pattern}*')
        
        if suite.countTestCases() == 0:
            print(f"❌ لم يتم العثور على الاختبار: {test_pattern}")
            return False
        
        print(f"✅ تم تحميل {suite.countTestCases()} اختبار")
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()
    
    except Exception as e:
        print(f"❌ خطأ في تشغيل الاختبار: {e}")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='تشغيل اختبارات نظام التداول')
    parser.add_argument('--test', help='تشغيل اختبار محدد (مثال: test_signal_processor)')
    parser.add_argument('--list', action='store_true', help='عرض جميع الاختبارات المتاحة')
    
    args = parser.parse_args()
    
    if args.list:
        discover_all_tests()
        sys.exit(0)
    
    if args.test:
        success = run_specific_test(args.test)
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)