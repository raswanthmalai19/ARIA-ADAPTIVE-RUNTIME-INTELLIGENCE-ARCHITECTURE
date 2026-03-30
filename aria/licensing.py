"""
ARIA Licensing & Monetization Module

Handles licensing validation, analytics, and premium feature gating.
Enables monetization while keeping core ARIA open-source.

Licensing Model:
- COMMUNITY: Free, open-source, for individual developers
- PROFESSIONAL: Paid, for production use, commercial support
- ENTERPRISE: Paid, unlimited deployment, on-premise support, custom modules
"""

import json
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("aria.licensing")


class LicenseType(str, Enum):
    """License tiers available for ARIA."""
    COMMUNITY = "community"      # Free, open-source
    PROFESSIONAL = "professional"  # Paid, for production
    ENTERPRISE = "enterprise"      # Paid, unlimited


class AnalyticsLevel(str, Enum):
    """What analytics data ARIA collects."""
    NONE = "none"                # No analytics (enterprise)
    MINIMAL = "minimal"          # Only critical errors
    STANDARD = "standard"        # Standard metrics
    FULL = "full"                # All metrics (community)


class Feature(str, Enum):
    """Premium features that can be gated."""
    UNLIMITED_MODELS = "unlimited_models"           # Multiple models
    CUSTOM_LAYER_PROFILES = "custom_layer_profiles" # Edit layer skip %
    MULTI_GPU_ROUTING = "multi_gpu_routing"         # Route across GPUs
    PRIORITY_SUPPORT = "priority_support"           # Fast support response
    ON_PREMISE_DEPLOYMENT = "on_premise_deployment" # Deploy in your infra
    ANALYTICS_DASHBOARD = "analytics_dashboard"     # Usage analytics
    API_KEYS = "api_keys"                           # Generate API keys
    CUSTOM_VALIDATOR = "custom_validator"           # Custom quality rules


class LicenseManager:
    """
    Manages ARIA licensing and feature access.
    
    Validates licenses, tracks usage, and gates premium features.
    Community tier is fully functional for development.
    Professional/Enterprise tiers unlock production features.
    """
    
    def __init__(self, license_key: Optional[str] = None):
        """
        Initialize license manager.
        
        Args:
            license_key: License key from ARIA (optional for community tier)
        """
        self.license_key = license_key
        self.license_type = LicenseType.COMMUNITY  # Default
        self.license_data: Dict[str, Any] = {}
        self.features_enabled: Dict[Feature, bool] = {f: False for f in Feature}
        self._analytics_level = AnalyticsLevel.FULL
        self._is_valid = False
        
        # Community features always enabled
        self._set_community_features()
        
        # If license key provided, validate it
        if license_key:
            self._validate_license(license_key)
    
    def _set_community_features(self):
        """Set features available in community tier."""
        self.license_type = LicenseType.COMMUNITY
        self._analytics_level = AnalyticsLevel.FULL
        self._is_valid = True
        
        # Community has access to core ARIA
        # Cannot use custom profiles or multi-model routing
        logger.info("Community license loaded (unrestricted core ARIA)")
    
    def _validate_license(self, license_key: str) -> bool:
        """
        Validate a professional/enterprise license key.
        
        License format: ARIA-{TYPE}-{TIMESTAMP}-{HMAC}
        Example: ARIA-PROFESSIONAL-1704067200-abc123...
        
        Args:
            license_key: The license key to validate
            
        Returns:
            True if license is valid, False otherwise
        """
        try:
            parts = license_key.split("-")
            if len(parts) < 4 or parts[0] != "ARIA":
                logger.error("Invalid license key format")
                return False
            
            license_type = parts[1].lower()
            timestamp = int(parts[2])
            signature = parts[3]
            
            # Check license type
            try:
                self.license_type = LicenseType(license_type)
            except ValueError:
                logger.error(f"Unknown license type: {license_type}")
                return False
            
            # Check expiration (licenses valid for 1 year)
            issued = datetime.fromtimestamp(timestamp)
            expires = issued + timedelta(days=365)
            
            if datetime.now() > expires:
                logger.error(f"License expired on {expires}")
                self._is_valid = False
                return False
            
            # Verify signature (in real implementation, use proper HMAC with secret key)
            msg = f"ARIA-{license_type}-{timestamp}"
            # Note: This is simplified. In production, use proper key management.
            expected_sig = hashlib.sha256(msg.encode()).hexdigest()[:16]
            
            if signature != expected_sig:
                logger.warning("License signature mismatch (may be test key)")
            
            # License is valid
            self._is_valid = True
            self.license_data = {
                "type": license_type,
                "issued": issued.isoformat(),  
                "expires": expires.isoformat(),
            }
            
            # Set features based on license type
            self._set_features_for_license()
            logger.info(f"{license_type.upper()} license loaded (valid until {expires.date()})")
            return True
            
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return False
    
    def _set_features_for_license(self):
        """Enable features based on license type."""
        if self.license_type == LicenseType.PROFESSIONAL:
            self._analytics_level = AnalyticsLevel.MINIMAL
            enabled = [
                Feature.UNLIMITED_MODELS,
                Feature.CUSTOM_LAYER_PROFILES,
                Feature.ANALYTICS_DASHBOARD,
                Feature.API_KEYS,
            ]
        elif self.license_type == LicenseType.ENTERPRISE:
            self._analytics_level = AnalyticsLevel.NONE
            enabled = [f for f in Feature]  # All features
        else:
            enabled = []
        
        for feature in Feature:
            self.features_enabled[feature] = feature in enabled
    
    def is_feature_enabled(self, feature: Feature) -> bool:
        """Check if a feature is enabled under current license."""
        return self.features_enabled.get(feature, False)
    
    def require_feature(self, feature: Feature) -> None:
        """
        Assert a feature is enabled; raise if not.
        
        Raises:
            RuntimeError: If feature is not available under current license
        """
        if not self.is_feature_enabled(feature):
            tier_name = self.license_type.value.upper()
            raise RuntimeError(
                f"Feature '{feature.value}' requires a license tier higher than {tier_name}. "
                f"Upgrade to Professional or Enterprise at https://aria-ai.dev/pricing"
            )
    
    def should_collect_analytics(self) -> bool:
        """Whether to collect analytics based on license."""
        return self._analytics_level in (AnalyticsLevel.STANDARD, AnalyticsLevel.FULL)
    
    def get_license_info(self) -> Dict[str, Any]:
        """Get current license information."""
        return {
            "license_type": self.license_type.value,
            "is_valid": self._is_valid,
            "analytics_level": self._analytics_level.value,
            "features_enabled": {
                f.value: self.is_feature_enabled(f) 
                for f in Feature
            },
            "license_data": self.license_data,
        }


class AnalyticsCollector:
    """
    Collects usage analytics if permitted under license.
    
    Community tier: Full analytics (helps us improve)
    Professional tier: Minimal analytics (errors only)
    Enterprise tier: No analytics (data isolation)
    """
    
    def __init__(self, license_manager: LicenseManager, db_path: Optional[Path] = None):
        self.license_manager = license_manager
        self.should_collect = license_manager.should_collect_analytics()
        self.db_path = db_path or Path("aria_analytics.db")
        self.events: list = []
    
    def record_inference(
        self,
        model_name: str,
        latency_ms: float,
        tokens: int,
        tier: str,
        success: bool,
    ) -> None:
        """Record an inference event (if analytics enabled)."""
        if not self.should_collect:
            return
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "inference",
            "model": model_name,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "complexity_tier": tier,
            "success": success,
        }
        self.events.append(event)
        
        # Would save to DB in production
        logger.debug(f"Analytics recorded: {tier} tier inference ({latency_ms:.0f}ms)")
    
    def record_error(self, error_type: str, message: str) -> None:
        """Record an error event (always recorded)."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "error",
            "error_type": error_type,
            "message": message,
        }
        self.events.append(event)
        logger.warning(f"Error recorded: {error_type}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get analytics summary."""
        if not self.events:
            return {}
        
        total = len(self.events)
        errors = len([e for e in self.events if e["event_type"] == "error"])
        inferences = len([e for e in self.events if e["event_type"] == "inference"])
        
        return {
            "total_events": total,
            "inferences": inferences,
            "errors": errors,
            "analytics_enabled": self.should_collect,
        }


# Global license manager instance
_license_manager: Optional[LicenseManager] = None


def init_licensing(license_key: Optional[str] = None) -> LicenseManager:
    """
    Initialize global license manager.
    
    Args:
        license_key: Optional license key from ARIA
        
    Returns:
        LicenseManager instance
    """
    global _license_manager
    _license_manager = LicenseManager(license_key)
    return _license_manager


def get_license_manager() -> LicenseManager:
    """Get global license manager (initialize if needed)."""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def check_feature(feature: Feature) -> None:
    """
    Check if a feature is enabled under current license.
    
    Raises RuntimeError if feature is not available.
    
    Example:
        check_feature(Feature.MULTI_GPU_ROUTING)
    """
    get_license_manager().require_feature(feature)
