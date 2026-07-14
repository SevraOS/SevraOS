import collections
import statistics
import structlog
from typing import Dict, Tuple

logger = structlog.get_logger(__name__)

class OutlierEngine:
    """
    Statistical Outlier Engine using rolling window Z-scores.
    Tracks state per device and per metric.
    """
    
    def __init__(self, window_size: int = 30, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        # Map: device_id -> metric -> deque of recent values
        self._history: Dict[str, Dict[str, collections.deque]] = collections.defaultdict(
            lambda: collections.defaultdict(lambda: collections.deque(maxlen=self.window_size))
        )
        
    def check_outlier(self, device_id: str, metric: str, value: float) -> Tuple[bool, str]:
        """
        Returns (is_outlier, reason).
        Always updates the rolling window with the new value.
        """
        history = self._history[device_id][metric]
        
        # We need a minimum number of samples to compute meaningful statistics
        if len(history) < 5:
            history.append(value)
            return False, "Not enough data"
            
        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0.0
        
        # Append new value after calculating stats to avoid it biasing its own check
        history.append(value)
        
        if stdev == 0.0:
            # If all previous values were identical, any deviation is technically an outlier,
            # but realistically we just wait for more variance.
            return False, "Zero variance"
            
        z_score = abs(value - mean) / stdev
        
        if z_score > self.z_threshold:
            logger.debug(
                "statistical_outlier_detected",
                device_id=device_id,
                metric=metric,
                value=value,
                z_score=z_score
            )
            return True, f"Z-score {z_score:.2f} > {self.z_threshold}"
            
        return False, "valid"
