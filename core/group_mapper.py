# core/group_mapper.py
"""
📦 GroupMapper - موحد أسماء المجموعات
========================================
يحل مشكلة عدم الاتساق بين:
- group1 vs group1_bullish
- group1 vs GROUP1
- group1_buy vs group1_bullish
"""

import logging
import re
from typing import Dict, Optional, Tuple, List
from collections import defaultdict

logger = logging.getLogger(__name__)

class GroupMapper:
    """🎯 موحد أسماء المجموعات لجميع المكونات"""
    
    # القاموس الرئيسي للتعيين
    GROUP_MAPPINGS = {
        # الصيغ الأساسية
        'group1': {'buy': 'group1_bullish', 'sell': 'group1_bearish'},
        'group2': {'buy': 'group2_bullish', 'sell': 'group2_bearish'},
        'group3': {'buy': 'group3_bullish', 'sell': 'group3_bearish'},
        'group4': {'buy': 'group4_bullish', 'sell': 'group4_bearish'},
        'group5': {'buy': 'group5_bullish', 'sell': 'group5_bearish'},
        
        # حالات خاصة
        'trend': {'buy': 'trend_bullish', 'sell': 'trend_bearish'},
        'trend_confirm': {'buy': 'trend_bullish', 'sell': 'trend_bearish'},
    }
    
    # قاموس عكسي للبحث السريع
    REVERSE_MAPPINGS = {}
    
    def __init__(self):
        """تهيئة الماب العكسي"""
        self._build_reverse_mappings()
    
    def _build_reverse_mappings(self):
        """بناء الماب العكسي للبحث السريع"""
        self.REVERSE_MAPPINGS = {}
        for base, directions in self.GROUP_MAPPINGS.items():
            for direction, full_name in directions.items():
                self.REVERSE_MAPPINGS[full_name] = (base, direction)
    
    def normalize_group_name(self, group_input: str, direction: str = None) -> str:
        """
        تحويل أي صيغة group إلى الصيغة الموحدة
        
        Args:
            group_input: الإدخال (group1, GROUP1, group1_bullish, etc.)
            direction: 'buy' أو 'sell' (مطلوب إذا كان group_input بدون اتجاه)
        
        Returns:
            الصيغة الموحدة (group1_bullish, group1_bearish, etc.)
        """
        try:
            if not group_input or group_input == 'UNKNOWN':
                return "unknown"
            
            input_lower = group_input.lower().strip()
            
            # إذا كانت الصيغة مكتملة بالفعل
            if '_bullish' in input_lower or '_bearish' in input_lower:
                return self._normalize_existing_group(input_lower)
            
            # إذا كانت بدون اتجاه، نحتاج direction
            if not direction:
                logger.warning(f"⚠️ Group بدون اتجاه: {group_input}")
                return input_lower
            
            # توحيد القاعدة
            base_normalized = self._normalize_base_name(input_lower)
            
            # البحث في الماب
            if base_normalized in self.GROUP_MAPPINGS:
                return self.GROUP_MAPPINGS[base_normalized].get(direction, input_lower)
            
            # الصيغة الافتراضية
            return f"{base_normalized}_{'bullish' if direction == 'buy' else 'bearish'}"
            
        except Exception as e:
            logger.error(f"💥 خطأ في توحيد اسم المجموعة: {group_input} -> {e}")
            return group_input if group_input else "unknown"
    
    def _normalize_existing_group(self, group_name: str) -> str:
        """توحيد مجموعة موجودة بالفعل (تحتوي على _bullish/_bearish)"""
        # تحقق من الصيغة
        if group_name.endswith('_bullish'):
            base = group_name.replace('_bullish', '')
            return f"{self._normalize_base_name(base)}_bullish"
        elif group_name.endswith('_bearish'):
            base = group_name.replace('_bearish', '')
            return f"{self._normalize_base_name(base)}_bearish"
        else:
            return group_name
    
    def _normalize_base_name(self, base_name: str) -> str:
        """توحيد اسم القاعدة"""
        if not base_name:
            return "unknown"
        
        name = base_name.lower().strip()
        
        # إزالة أي underscores زائدة
        name = name.strip('_')
        
        # تحويل GROUP1 إلى group1
        if name.startswith('group'):
            match = re.match(r'group(\d+)', name)
            if match:
                return f"group{match.group(1)}"
        
        # إذا كان رقم فقط، أضف group
        if name.isdigit():
            return f"group{name}"
        
        # حالات خاصة
        special_cases = {
            'trend': 'trend',
            'trend_confirm': 'trend',
            'entry_bullish': 'group1',
            'entry_bearish': 'group1',
            'entry_bullish1': 'group2',
            'entry_bearish1': 'group2',
        }
        
        if name in special_cases:
            return special_cases[name]
        
        return name
    
    def extract_base_and_direction(self, full_name: str) -> Tuple[str, Optional[str]]:
        """
        استخراج القاعدة والاتجاه من الاسم الكامل
        
        Returns:
            (base_name, direction) أو (base_name, None) إذا لم يكن هناك اتجاه
        """
        if not full_name:
            return "unknown", None
        
        name_lower = full_name.lower()
        
        # البحث في الماب العكسي أولاً
        if name_lower in self.REVERSE_MAPPINGS:
            return self.REVERSE_MAPPINGS[name_lower]
        
        # التحقق يدوياً
        if name_lower.endswith('_bullish'):
            return name_lower.replace('_bullish', ''), 'buy'
        elif name_lower.endswith('_bearish'):
            return name_lower.replace('_bearish', ''), 'sell'
        else:
            return name_lower, None
    
    def is_group_enabled(self, group_name: str, config: Dict) -> bool:
        """
        التحقق من تفعيل المجموعة بناءً على الإعدادات
        
        يدعم جميع الصيغ: group1, GROUP1, group1_bullish, etc.
        """
        try:
            # استخراج القاعدة
            base_name, _ = self.extract_base_and_direction(group_name)
            
            # البحث عن مفتاح التفعيل
            config_key = f"{base_name.upper()}_ENABLED"
            
            enabled = config.get(config_key, False)
            
            if not enabled:
                logger.debug(f"🔍 المجموعة {group_name} (base: {base_name}) معطلة - {config_key}={enabled}")
            
            return bool(enabled)
            
        except Exception as e:
            logger.error(f"💥 خطأ في التحقق من تفعيل المجموعة {group_name}: {e}")
            return False
    
    def get_all_group_variations(self, base_name: str) -> Dict[str, str]:
        """الحصول على جميع أشكال المجموعة"""
        base_normalized = self._normalize_base_name(base_name)
        
        return {
            'bullish': f"{base_normalized}_bullish",
            'bearish': f"{base_normalized}_bearish",
            'buy': f"{base_normalized}_bullish",
            'sell': f"{base_normalized}_bearish",
            'long': f"{base_normalized}_bullish",
            'short': f"{base_normalized}_bearish",
            'base': base_normalized
        }
    
    def validate_group_name(self, group_name: str) -> Tuple[bool, str]:
        """
        التحقق من صحة اسم المجموعة
        
        Returns:
            (is_valid, error_message)
        """
        if not group_name:
            return False, "اسم المجموعة فارغ"
        
        name_lower = group_name.lower()
        
        # قائمة المجموعات المعروفة
        known_groups = [
            'group1', 'group2', 'group3', 'group4', 'group5',
            'trend', 'trend_bullish', 'trend_bearish'
        ]
        
        # التحقق من الصيغة
        pattern = r'^(group[1-5]|trend)(_(bullish|bearish))?$'
        if not re.match(pattern, name_lower):
            return False, f"صيغة غير صالحة: {group_name}"
        
        return True, "صالح"
    
    def get_group_statistics(self, config: Dict) -> Dict:
        """الحصول على إحصائيات المجموعات"""
        stats = {
            'total_groups': 0,
            'enabled_groups': 0,
            'disabled_groups': 0,
            'groups': {}
        }
        
        for group_num in range(1, 6):
            group_key = f'group{group_num}'
            variations = self.get_all_group_variations(group_key)
            
            enabled = self.is_group_enabled(group_key, config)
            
            stats['groups'][group_key] = {
                'enabled': enabled,
                'variations': variations,
                'config_key': f"{group_key.upper()}_ENABLED"
            }
            
            stats['total_groups'] += 1
            if enabled:
                stats['enabled_groups'] += 1
            else:
                stats['disabled_groups'] += 1
        
        # المجموعات الخاصة
        special_groups = ['trend']
        for group in special_groups:
            enabled = self.is_group_enabled(group, config)
            stats['groups'][group] = {
                'enabled': enabled,
                'variations': self.get_all_group_variations(group),
                'config_key': f"{group.upper()}_ENABLED"
            }
        
        return stats
