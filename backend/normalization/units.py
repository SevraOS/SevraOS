from typing import Tuple
from mdil.schema import Unit

class UnitConversionEngine:
    """
    Standardizes units to canonical target units.
    e.g. °F -> °C, mg/dL -> mmol/L
    """
    
    @staticmethod
    def convert(value: float, current_unit: str) -> Tuple[float, str]:
        """
        Returns (converted_value, new_unit).
        If no conversion is needed, returns original values.
        """
        # Temperature: Fahrenheit to Celsius
        if current_unit == "F":
            celsius = (value - 32.0) * 5.0 / 9.0
            return round(celsius, 2), Unit.CELSIUS.value
            
        # Glucose: mg/dL to mmol/L (Divide by 18.0182)
        if current_unit == "mg/dL":
            mmol = value / 18.0182
            return round(mmol, 2), Unit.MMOL_PER_L.value
            
        # Weight: lb to kg
        if current_unit == "lb":
            kg = value * 0.453592
            return round(kg, 2), "kg"
            
        # Fallback: No conversion required
        return value, current_unit
