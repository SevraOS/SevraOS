"""
HELIOS OS + SEVRA AI
FHIR R4 Models (Section 3)
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class FHIRMeta(BaseModel):
    versionId: Optional[str] = None
    lastUpdated: Optional[datetime] = None

class CodeableConcept(BaseModel):
    coding: List[Dict[str, str]]
    text: Optional[str] = None

class Reference(BaseModel):
    reference: str
    display: Optional[str] = None

class Identifier(BaseModel):
    use: Optional[str] = None
    system: Optional[str] = None
    value: str

class Quantity(BaseModel):
    value: float
    unit: str
    system: str = "http://unitsofmeasure.org"
    code: str

# --- FHIR Resources ---

class Patient(BaseModel):
    resourceType: str = "Patient"
    id: Optional[str] = None
    identifier: List[Identifier]
    active: bool = True
    name: List[Dict[str, Any]]
    gender: str
    birthDate: str

class Observation(BaseModel):
    """Represents a vital sign or prediction."""
    resourceType: str = "Observation"
    id: Optional[str] = None
    status: str = "final"
    category: List[CodeableConcept]
    code: CodeableConcept
    subject: Reference
    effectiveDateTime: datetime
    valueQuantity: Optional[Quantity] = None
    valueCodeableConcept: Optional[CodeableConcept] = None
    device: Optional[Reference] = None
    
class Device(BaseModel):
    resourceType: str = "Device"
    id: Optional[str] = None
    identifier: List[Identifier]
    status: str = "active"
    manufacturer: str
    modelNumber: str

class Encounter(BaseModel):
    resourceType: str = "Encounter"
    id: Optional[str] = None
    status: str = "in-progress"
    class_: CodeableConcept = Field(alias="class")
    subject: Reference

class Practitioner(BaseModel):
    resourceType: str = "Practitioner"
    id: Optional[str] = None
    identifier: List[Identifier]
    name: List[Dict[str, Any]]

class CarePlan(BaseModel):
    resourceType: str = "CarePlan"
    id: Optional[str] = None
    status: str = "active"
    intent: str = "plan"
    subject: Reference

class Condition(BaseModel):
    resourceType: str = "Condition"
    id: Optional[str] = None
    clinicalStatus: CodeableConcept
    verificationStatus: CodeableConcept
    subject: Reference

class MedicationRequest(BaseModel):
    resourceType: str = "MedicationRequest"
    id: Optional[str] = None
    status: str = "active"
    intent: str = "order"
    medicationCodeableConcept: CodeableConcept
    subject: Reference

class DiagnosticReport(BaseModel):
    resourceType: str = "DiagnosticReport"
    id: Optional[str] = None
    status: str = "final"
    code: CodeableConcept
    subject: Reference
    result: Optional[List[Reference]] = None
