import os
import yaml
import structlog
from typing import Dict, Any, Tuple
from mdil.schema import RawReading

logger = structlog.get_logger(__name__)

class RangeValidator:
    def __init__(self, config_path: str = None):
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), "config", "ranges.yaml")
        self.config_path = config_path
        self.ranges: Dict[str, Dict[str, float]] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load or reload physiological ranges from YAML."""
        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)
                self.ranges = data.get("ranges", {})
            logger.info("range_validator_config_loaded", path=self.config_path)
        except Exception as e:
            logger.error("range_validator_config_error", error=str(e))
            self.ranges = {}

    def is_within_range(self, metric: str, value: float) -> Tuple[bool, str]:
        """
        Check if a value is within the physiological range.
        Returns (is_valid, reason).
        """
        metric_range = self.ranges.get(metric)
        if not metric_range:
            # If no range defined, assume valid
            return True, "valid"
        
        min_val = metric_range.get("min")
        max_val = metric_range.get("max")
        
        if min_val is not None and value < min_val:
            return False, f"Value {value} below minimum {min_val}"
        
        if max_val is not None and value > max_val:
            return False, f"Value {value} above maximum {max_val}"
            
        return True, "valid"
