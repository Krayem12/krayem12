class ConfigValidator:
    """Configuration validation class - UPDATED FOR ALL GROUP COMBINATIONS"""
    
    @staticmethod
    def validate_config(config):
        """Validate all configuration parameters - RETURNS (errors, warnings)"""
        errors = []
        warnings = []
        
        # التحقق من الإعدادات الأساسية
        basic_errors, basic_warnings = ConfigValidator.validate_basic_config(config)
        errors.extend(basic_errors)
        warnings.extend(basic_warnings)
        
        # التحقق من إعدادات التداول
        errors.extend(ConfigValidator.validate_trading_config(config))
        
        # التحقق من إعدادات الإشعارات
        warnings.extend(ConfigValidator.validate_notification_config(config))
        
        # 🎯 MULTI-MODE: التحقق من إعدادات الاستراتيجية المتعددة
        strategy_errors, strategy_warnings = ConfigValidator.validate_multi_mode_strategy_config_dynamic(config)
        errors.extend(strategy_errors)
        warnings.extend(strategy_warnings)
        
        # 🎯 NEW: التحقق من التجميعات
        combination_errors, combination_warnings = ConfigValidator.validate_group_combinations(config)
        errors.extend(combination_errors)
        warnings.extend(combination_warnings)
        
        return errors, warnings

    @staticmethod
    def validate_group_combinations(config):
        """🎯 التحقق من صحة تجميعات المجموعات"""
        errors = []
        warnings = []
        
        trading_modes_to_check = [
            ('TRADING_MODE', config.get('TRADING_MODE')),
            ('TRADING_MODE1', config.get('TRADING_MODE1')),
            ('TRADING_MODE2', config.get('TRADING_MODE2'))
        ]
        
        valid_groups = ['GROUP1', 'GROUP2', 'GROUP3', 'GROUP4', 'GROUP5']
        
        for mode_key, mode_value in trading_modes_to_check:
            if mode_value:
                # تقسيم التوليفة إلى مجموعات
                groups = mode_value.split('_')
                
                # 🎯 التحقق من عدم وجود تكرار
                if len(groups) != len(set(groups)):
                    errors.append(f"❌ {mode_key} يحتوي على مجموعات مكررة: {mode_value}")
                
                for group in groups:
                    if group not in valid_groups:
                        errors.append(f"❌ {mode_key} يحتوي على مجموعة غير صالحة: {group}")
                    
                    # التحقق من أن المجموعة مفعلة
                    group_enabled_key = f"{group}_ENABLED"
                    if not config.get(group_enabled_key, False):
                        warnings.append(f"⚠️ {mode_key} يتطلب المجموعة {group} ولكنها غير مفعلة")
                
                # 🎯 التحقق من وجود مجموعة واحدة على الأقل
                if len(groups) == 0:
                    errors.append(f"❌ {mode_key} يجب أن يحتوي على مجموعة واحدة على الأقل")
            
        return errors, warnings

    @staticmethod
    def validate_multi_mode_strategy_config_dynamic(config):
        """🎯 Validate multi-mode strategy configuration - DYNAMIC FOR ALL COMBINATIONS"""
        errors = []
        warnings = []
        
        # 🚫 التحقق من أن القيم ليست None
        if config.get('TRADING_MODE') is None:
            errors.append("❌ TRADING_MODE مطلوب في ملف .env")
        
        if config.get('TRADING_MODE1') is None and config.get('TRADING_MODE1_ENABLED'):
            errors.append("❌ TRADING_MODE1 مطلوب في ملف .env لأن TRADING_MODE1_ENABLED=true")
        
        if config.get('TRADING_MODE2') is None and config.get('TRADING_MODE2_ENABLED'):
            errors.append("❌ TRADING_MODE2 مطلوب في ملف .env لأن TRADING_MODE2_ENABLED=true")
        
        # التحقق من أنماط التداول المحددة
        trading_modes_to_check = [
            ('TRADING_MODE', config.get('TRADING_MODE')),
            ('TRADING_MODE1', config.get('TRADING_MODE1')),
            ('TRADING_MODE2', config.get('TRADING_MODE2'))
        ]
        
        valid_groups = ['GROUP1', 'GROUP2', 'GROUP3', 'GROUP4', 'GROUP5']
        
        for mode_key, mode_value in trading_modes_to_check:
            if mode_value:
                # تقسيم التوليفة إلى مجموعات
                groups = mode_value.split('_')
                
                for group in groups:
                    if group not in valid_groups:
                        errors.append(f"❌ {mode_key} يحتوي على مجموعة غير صالحة: {group}")
                    
                    # التحقق من أن المجموعة مفعلة
                    group_enabled_key = f"{group}_ENABLED"
                    if not config.get(group_enabled_key, False):
                        errors.append(f"❌ {mode_key} يتطلب المجموعة {group} ولكنها غير مفعلة")
            
        # التحقق من GROUP1_TREND_MODE
        valid_trend_modes = ['ONLY_TREND', 'ALLOW_COUNTER_TREND']
        trend_mode = config.get('GROUP1_TREND_MODE')
        if trend_mode not in valid_trend_modes:
            errors.append(f"❌ GROUP1_TREND_MODE must be one of {valid_trend_modes}")
                
        # التحقق من أعداد التأكيدات
        if config.get('REQUIRED_CONFIRMATIONS_GROUP1', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP1 must be greater than 0")
            
        if config.get('GROUP2_ENABLED') and config.get('REQUIRED_CONFIRMATIONS_GROUP2', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP2 must be greater than 0 when GROUP2 is enabled")
            
        if config.get('GROUP3_ENABLED') and config.get('REQUIRED_CONFIRMATIONS_GROUP3', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP3 must be greater than 0 when GROUP3 is enabled")
            
        # 🆕 إضافة تحقق للمجموعتين الجديدتين
        if config.get('GROUP4_ENABLED') and config.get('REQUIRED_CONFIRMATIONS_GROUP4', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP4 must be greater than 0 when GROUP4 is enabled")
            
        if config.get('GROUP5_ENABLED') and config.get('REQUIRED_CONFIRMATIONS_GROUP5', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP5 must be greater than 0 when GROUP5 is enabled")
            
        # 🆕 التحقق من حدود الصفقات للنمط الإضافي
        if config.get('TRADING_MODE1_ENABLED'):
            max_trades_mode1 = config.get('MAX_TRADES_MODE1', 5)
            if max_trades_mode1 <= 0:
                errors.append("❌ MAX_TRADES_MODE1 must be greater than 0 when TRADING_MODE1 is enabled")
                
        if config.get('TRADING_MODE2_ENABLED'):
            max_trades_mode2 = config.get('MAX_TRADES_MODE2', 5)
            if max_trades_mode2 <= 0:
                errors.append("❌ MAX_TRADES_MODE2 must be greater than 0 when TRADING_MODE2 is enabled")
            
        return errors, warnings

    @staticmethod
    def validate_multi_mode_strategy_config(config):
        """النسخة القديمة للتوافق - استخدام النسخة الجديدة"""
        return ConfigValidator.validate_multi_mode_strategy_config_dynamic(config)
    
    @staticmethod
    def validate_basic_config(config):
        """Validate basic configuration"""
        errors = []
        warnings = []
        
        if not ConfigValidator.is_valid_bool(config.get('DEBUG')):
            errors.append("❌ DEBUG must be true or false")
            
        port = config.get('PORT', 0)
        if port <= 0 or port > 65535:
            warnings.append(f"⚠️ PORT {port} is invalid, using default 10000")
            
        if config.get('DEBUG', False):
            if config.get('TELEGRAM_ENABLED') and not config.get('TELEGRAM_BOT_TOKEN'):
                warnings.append("⚠️ TELEGRAM_BOT_TOKEN recommended when Telegram is enabled")
            if config.get('EXTERNAL_SERVER_ENABLED') and not config.get('EXTERNAL_SERVER_URL'):
                warnings.append("⚠️ EXTERNAL_SERVER_URL recommended when External Server is enabled")
        else:
            if config.get('TELEGRAM_ENABLED') and not config.get('TELEGRAM_BOT_TOKEN'):
                errors.append("❌ TELEGRAM_BOT_TOKEN required when Telegram is enabled")
            if config.get('EXTERNAL_SERVER_ENABLED') and not config.get('EXTERNAL_SERVER_URL'):
                errors.append("❌ EXTERNAL_SERVER_URL required when External Server is enabled")
        
        # 🆕 التحقق من إعداد التنظيف الموحد
        cleanup_interval = config.get('SIGNAL_CLEANUP_INTERVAL_MINUTES', 5)
        if cleanup_interval < 1 or cleanup_interval > 60:
            warnings.append("⚠️ SIGNAL_CLEANUP_INTERVAL_MINUTES should be between 1 and 60 minutes")
            
        # 🆕 التحقق من إعداد تخزين الإشارات المخالفة
        if not ConfigValidator.is_valid_bool(config.get('STORE_CONTRARIAN_SIGNALS')):
            errors.append("❌ STORE_CONTRARIAN_SIGNALS must be true or false")
            
        return errors, warnings
    
    @staticmethod
    def validate_trading_config(config):
        """Validate trading configuration"""
        errors = []
        
        if config.get('MAX_OPEN_TRADES', 0) <= 0:
            errors.append("❌ MAX_OPEN_TRADES must be greater than 0")
            
        if config.get('MAX_TRADES_PER_SYMBOL', 0) <= 0:
            errors.append("❌ MAX_TRADES_PER_SYMBOL must be greater than 0")
            
        if config.get('MAX_TRADES_PER_SYMBOL', 0) > config.get('MAX_OPEN_TRADES', 0):
            errors.append("❌ MAX_TRADES_PER_SYMBOL cannot exceed MAX_OPEN_TRADES")
            
        # 🆕 التحقق من أن أعداد التأكيدات منطقية
        if config.get('REQUIRED_CONFIRMATIONS_GROUP1', 0) > 10:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP1 cannot exceed 10")
            
        if config.get('REQUIRED_CONFIRMATIONS_GROUP2', 0) > 10:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP2 cannot exceed 10")
            
        if config.get('REQUIRED_CONFIRMATIONS_GROUP3', 0) > 10:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP3 cannot exceed 10")
            
        if config.get('REQUIRED_CONFIRMATIONS_GROUP4', 0) > 10:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP4 cannot exceed 10")
            
        if config.get('REQUIRED_CONFIRMATIONS_GROUP5', 0) > 10:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP5 cannot exceed 10")
            
        return errors
    
    @staticmethod
    def validate_notification_config(config):
        """Validate notification configuration"""
        warnings = []
        
        if (config.get('TELEGRAM_ENABLED') or config.get('EXTERNAL_SERVER_ENABLED')):
            notifications_enabled = any([
                config.get('SEND_TREND_MESSAGES'),
                config.get('SEND_ENTRY_MESSAGES'), 
                config.get('SEND_EXIT_MESSAGES'),
                config.get('SEND_GENERAL_MESSAGES')
            ])
            
            if not notifications_enabled:
                warnings.append("⚠️ All notifications are disabled but services are enabled")
                
        # 🆕 التحقق من أن هناك على الأقل نوع واحد من الإشعارات مفعل
        if config.get('TELEGRAM_ENABLED') or config.get('EXTERNAL_SERVER_ENABLED'):
            active_notifications = sum([
                config.get('SEND_TREND_MESSAGES', False),
                config.get('SEND_ENTRY_MESSAGES', False),
                config.get('SEND_EXIT_MESSAGES', False),
                config.get('SEND_CONFIRMATION_MESSAGES', False),
                config.get('SEND_GENERAL_MESSAGES', False)
            ])
            
            if active_notifications == 0:
                warnings.append("⚠️ Notification services are enabled but all message types are disabled")
                
        return warnings
    
    @staticmethod
    def is_valid_bool(value):
        """Check if value is valid boolean"""
        return value in [True, False]
    
    @staticmethod
    def format_validation_report(errors, warnings):
        """Format validation report"""
        if not errors and not warnings:
            return "✅ All configuration validations passed"
            
        report = []
        if errors:
            report.append("❌ ERRORS:")
            report.extend([f"   {error}" for error in errors])
            
        if warnings:
            report.append("⚠️ WARNINGS:")
            report.extend([f"   {warning}" for warning in warnings])
            
        return "\n".join(report)