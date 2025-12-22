# tests/test_group_mapper.py
"""
🧪 اختبار توحيد أسماء المجموعات
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.group_mapper import GroupMapper

def test_group_mapper():
    """اختبار شامل لـ GroupMapper"""
    
    print("🧪 اختبار GroupMapper")
    print("=" * 50)
    
    mapper = GroupMapper()
    
    test_cases = [
        # (input, direction, expected_output)
        ("group1", "buy", "group1_bullish"),
        ("group1", "sell", "group1_bearish"),
        ("GROUP1", "buy", "group1_bullish"),
        ("group1_bullish", None, "group1_bullish"),
        ("group1_bearish", None, "group1_bearish"),
        ("group2", "buy", "group2_bullish"),
        ("group3", "sell", "group3_bearish"),
        ("trend", "buy", "trend_bullish"),
        ("trend_confirm", "sell", "trend_bearish"),
        ("group1_buy", "buy", "group1_bullish"),
        ("group1_long", "buy", "group1_bullish"),
        ("1", "buy", "group1_bullish"),  # رقم فقط
        ("group", "sell", "group_bearish"),  # بدون رقم
    ]
    
    all_passed = True
    for input_name, direction, expected in test_cases:
        result = mapper.normalize_group_name(input_name, direction)
        passed = result == expected
        status = "✅" if passed else "❌"
        
        print(f"{status} '{input_name}' + '{direction}' -> '{result}' (متوقع: '{expected}')")
        
        if not passed:
            all_passed = False
    
    print("\n🧪 اختبار استخراج القاعدة والاتجاه")
    print("=" * 50)
    
    extract_tests = [
        ("group1_bullish", ("group1", "buy")),
        ("group1_bearish", ("group1", "sell")),
        ("group2_bullish", ("group2", "buy")),
        ("unknown", ("unknown", None)),
        ("trend_bullish", ("trend", "buy")),
    ]
    
    for input_name, expected in extract_tests:
        base, direction = mapper.extract_base_and_direction(input_name)
        passed = (base, direction) == expected
        status = "✅" if passed else "❌"
        
        print(f"{status} '{input_name}' -> base='{base}', direction='{direction}'")
        
        if not passed:
            all_passed = False
    
    print("\n🧪 اختبار تفعيل المجموعة")
    print("=" * 50)
    
    config = {
        "GROUP1_ENABLED": True,
        "GROUP2_ENABLED": False,
        "GROUP3_ENABLED": True,
        "TREND_ENABLED": True,
    }
    
    enable_tests = [
        ("group1_bullish", True),
        ("group2_bearish", False),
        ("group3", True),
        ("trend_bullish", True),
        ("unknown", False),
    ]
    
    for group_name, expected in enable_tests:
        result = mapper.is_group_enabled(group_name, config)
        passed = result == expected
        status = "✅" if passed else "❌"
        
        print(f"{status} '{group_name}' -> {result} (متوقع: {expected})")
        
        if not passed:
            all_passed = False
    
    print("\n🧪 اختبار صحة اسم المجموعة")
    print("=" * 50)
    
    validation_tests = [
        ("group1_bullish", (True, "صالح")),
        ("group1_bearish", (True, "صالح")),
        ("group5_bullish", (True, "صالح")),
        ("invalid_group", (False, "صيغة غير صالحة")),
        ("", (False, "اسم المجموعة فارغ")),
    ]
    
    for group_name, expected in validation_tests:
        is_valid, message = mapper.validate_group_name(group_name)
        expected_valid, expected_msg = expected
        passed = is_valid == expected_valid
        status = "✅" if passed else "❌"
        
        print(f"{status} '{group_name}' -> صالح={is_valid}, رسالة='{message}'")
        
        if not passed:
            all_passed = False
    
    print("\n🧪 اختبار إحصائيات المجموعات")
    print("=" * 50)
    
    stats = mapper.get_group_statistics(config)
    
    if stats:
        print(f"✅ تم الحصول على إحصائيات: {stats['total_groups']} مجموعة")
        print(f"   - مفعلة: {stats['enabled_groups']}")
        print(f"   - معطلة: {stats['disabled_groups']}")
        
        for group_name, group_info in stats['groups'].items():
            status = "✅ مفعلة" if group_info['enabled'] else "❌ معطلة"
            print(f"   - {group_name}: {status}")
    else:
        print("❌ فشل الحصول على إحصائيات")
        all_passed = False
    
    return all_passed

if __name__ == "__main__":
    success = test_group_mapper()
    if success:
        print("\n🎉 جميع الاختبارات نجحت!")
        sys.exit(0)
    else:
        print("\n❌ فشل بعض الاختبارات!")
        sys.exit(1)
