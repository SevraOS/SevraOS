from typing import Optional
from mdil.schema import MetricType

class LOINCMapper:
    """
    Maps HELIOS internal metrics to standard LOINC codes.
    """
    
    # Static mapping for core vitals
    MAPPING = {
        MetricType.HEART_RATE: "8867-4",
        MetricType.SPO2: "2708-6", # Oxygen saturation in Arterial blood
        MetricType.RESPIRATORY_RATE: "9279-1",
        MetricType.SYSTOLIC_BP: "8480-6",
        MetricType.DIASTOLIC_BP: "8462-4",
        MetricType.MEAN_ARTERIAL_PRESSURE: "8478-0",
        MetricType.BODY_TEMPERATURE: "8310-5", # Body temperature
        MetricType.BLOOD_GLUCOSE: "15074-8", # Glucose [Moles/volume] in Blood
        MetricType.PULSE_RATE: "8867-4",
        MetricType.PERFUSION_INDEX: "61006-3", # Not perfectly LOINC, PI is device specific, using closest
        MetricType.RESPIRATORY_RATE_VENT: "19835-8",
        MetricType.TIDAL_VOLUME: "20104-6",
        MetricType.MINUTE_VENTILATION: "20112-9",
        MetricType.PEAK_INSPIRATORY_PRESSURE: "20077-4",
        MetricType.PEEP: "20078-2",
        MetricType.FIO2: "19994-3",
        MetricType.INFUSION_RATE: "41505-9",
        MetricType.VOLUME_INFUSED: "41506-7"
    }

    @classmethod
    def get_loinc(cls, metric: str) -> Optional[str]:
        """Return the LOINC code for a given metric."""
        # Check against the MetricType enum values
        return cls.MAPPING.get(metric)
