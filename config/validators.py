# config/validators.py
class ConfigValidator:
    """Configuration validation class - UPDATED FOR MULTI-MODE STRATEGY WITH GROUP2_GROUP3"""
    
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
        strategy_errors, strategy_warnings = ConfigValidator.validate_multi_mode_strategy_config(config)
        errors.extend(strategy_errors)
        warnings.extend(strategy_warnings)
        
        return errors, warnings
    
    @staticmethod
    def validate_multi_mode_strategy_config(config):
        """Validate multi-mode strategy configuration - UPDATED FOR GROUP2_GROUP3"""
        errors = []
        warnings = []
        
        # 🆕 تحديث: قائمة أنماط التداول الصالحة لتشمل GROUP2_GROUP3
        valid_modes = ['GROUP1', 'GROUP1_GROUP2', 'GROUP1_GROUP3', 'GROUP1_GROUP2_GROUP3', 
                      'GROUP2_GROUP3', 'GROUP2', 'GROUP3']  # 🆕 إضافة GROUP2_GROUP3
        
        # التحقق من TRADING_MODE الأساسي
        trading_mode = config.get('TRADING_MODE')
        if trading_mode not in valid_modes:
            errors.append(f"❌ TRADING_MODE must be one of {valid_modes}")
            
        # التحقق من TRADING_MODE1
        trading_mode1 = config.get('TRADING_MODE1')
        if trading_mode1 not in valid_modes:
            errors.append(f"❌ TRADING_MODE1 must be one of {valid_modes}")
            
        # التحقق من TRADING_MODE2
        trading_mode2 = config.get('TRADING_MODE2')
        if trading_mode2 not in valid_modes:
            errors.append(f"❌ TRADING_MODE2 must be one of {valid_modes}")
            
        # التحقق من GROUP1_TREND_MODE
        valid_trend_modes = ['ONLY_TREND', 'ALLOW_COUNTER_TREND']
        trend_mode = config.get('GROUP1_TREND_MODE')
        if trend_mode not in valid_trend_modes:
            errors.append(f"❌ GROUP1_TREND_MODE must be one of {valid_trend_modes}")
            
        # 🎯 MULTI-MODE: التحقق من أن المجموعات المطلوبة في الأنماط مفعلة
        if config.get('TRADING_MODE1_ENABLED'):
            if trading_mode1 in ['GROUP1_GROUP2', 'GROUP1_GROUP2_GROUP3']:
                if not config.get('GROUP2_ENABLED'):
                    errors.append("❌ GROUP2 must be enabled for TRADING_MODE1 with GROUP2 requirement")
                    
            if trading_mode1 in ['GROUP1_GROUP3', 'GROUP1_GROUP2_GROUP3']:
                if not config.get('GROUP3_ENABLED'):
                    errors.append("❌ GROUP3 must be enabled for TRADING_MODE1 with GROUP3 requirement")
            
            # 🆕 إضافة تحقق لـ GROUP2_GROUP3
            if trading_mode1 == 'GROUP2_GROUP3':
                if not config.get('GROUP2_ENABLED'):
                    errors.append("❌ GROUP2 must be enabled for TRADING_MODE1 with GROUP2_GROUP3 strategy")
                if not config.get('GROUP3_ENABLED'):
                    errors.append("❌ GROUP3 must be enabled for TRADING_MODE1 with GROUP2_GROUP3 strategy")
                    
        if config.get('TRADING_MODE2_ENABLED'):
            if trading_mode2 in ['GROUP1_GROUP2', 'GROUP1_GROUP2_GROUP3']:
                if not config.get('GROUP2_ENABLED'):
                    errors.append("❌ GROUP2 must be enabled for TRADING_MODE2 with GROUP2 requirement")
                    
            if trading_mode2 in ['GROUP1_GROUP3', 'GROUP1_GROUP2_GROUP3']:
                if not config.get('GROUP3_ENABLED'):
                    errors.append("❌ GROUP3 must be enabled for TRADING_MODE2 with GROUP3 requirement")
            
            # 🆕 إضافة تحقق لـ GROUP2_GROUP3
            if trading_mode2 == 'GROUP2_GROUP3':
                if not config.get('GROUP2_ENABLED'):
                    errors.append("❌ GROUP2 must be enabled for TRADING_MODE2 with GROUP2_GROUP3 strategy")
                if not config.get('GROUP3_ENABLED'):
                    errors.append("❌ GROUP3 must be enabled for TRADING_MODE2 with GROUP2_GROUP3 strategy")
                
        # التحقق من أعداد التأكيدات
        if config.get('REQUIRED_CONFIRMATIONS_GROUP1', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP1 must be greater than 0")
            
        if config.get('GROUP2_ENABLED') and config.get('REQUIRED_CONFIRMATIONS_GROUP2', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP2 must be greater than 0 when GROUP2 is enabled")
            
        if config.get('GROUP3_ENABLED') and config.get('REQUIRED_CONFIRMATIONS_GROUP3', 0) <= 0:
            errors.append("❌ REQUIRED_CONFIRMATIONS_GROUP3 must be greater than 0 when GROUP3 is enabled")
            
        return errors, warnings
    
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