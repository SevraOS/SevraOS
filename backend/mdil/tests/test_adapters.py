"""
HELIOS OS + SEVRA AI
MDIL Unit Tests — Adapter Tests

Tests for all 6 device adapters:
  - ECGAdapter (DAT, WFM, STA frames)
  - BPAdapter (SYS/DIA/MAP/PR)
  - SpO2Adapter (BLE binary + ASCII)
  - VentilatorAdapter (HL7 OBX segments)
  - InfusionAdapter (binary + ASCII)
  - GlucometerAdapter (mmol/L + mg/dL)

Coverage: success paths, error paths, edge cases, framing errors.
"""

from __future__ import annotations

import struct
import pytest

from mdil.adapters.ecg_adapter import ECGAdapter
from mdil.adapters.bp_adapter import BPAdapter
from mdil.adapters.spo2_adapter import SpO2Adapter
from mdil.adapters.ventilator_adapter import VentilatorAdapter
from mdil.adapters.infusion_adapter import InfusionAdapter
from mdil.adapters.glucometer_adapter import GlucometerAdapter
from mdil.base import AdapterParseError
from mdil.registry import AdapterRegistry
from mdil.schema import DeviceType, MetricType, Unit, ReadingQuality


# ── ECG Adapter Tests ─────────────────────────────────────────────────────────

class TestECGAdapter:
    @pytest.fixture(autouse=True)
    def adapter(self) -> ECGAdapter:
        return ECGAdapter(device_id="ECG-TEST-001")

    def test_dat_frame_produces_two_readings(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("DAT|72|0.84|II")
        assert len(readings) == 2

    def test_dat_frame_heart_rate_reading(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("DAT|72|0.84|II")
        hr = next(r for r in readings if r.metric == MetricType.HEART_RATE)
        assert hr.value == 72.0
        assert hr.unit == Unit.BPM
        assert hr.device_type == DeviceType.ECG
        assert hr.quality == ReadingQuality.GOOD

    def test_dat_frame_lead_amplitude_reading(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("DAT|72|0.84|II")
        lead = next(r for r in readings if r.metric == MetricType.ECG_LEAD_II)
        assert lead.value == 0.84
        assert lead.unit == Unit.MV

    def test_dat_frame_lead_i(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("DAT|65|0.72|I")
        lead = next(r for r in readings if r.metric == MetricType.ECG_LEAD_I)
        assert lead.value == 0.72

    def test_dat_frame_lead_iii(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("DAT|80|0.90|III")
        lead = next(r for r in readings if r.metric == MetricType.ECG_LEAD_III)
        assert lead.value == 0.90

    def test_dat_frame_unknown_lead_uses_waveform_metric(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("DAT|72|0.84|V1")
        lead = next(r for r in readings if r.metric == MetricType.ECG_WAVEFORM)
        assert lead.unit == Unit.MV

    def test_dat_frame_bytes_input(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse(b"DAT|72|0.84|II")
        assert len(readings) == 2

    def test_dat_frame_missing_fields_raises(self, adapter: ECGAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("DAT|72|0.84")

    def test_dat_frame_invalid_hr_raises(self, adapter: ECGAdapter) -> None:
        with pytest.raises(AdapterParseError, match="heart_rate"):
            adapter.parse("DAT|abc|0.84|II")

    def test_dat_frame_invalid_amplitude_raises(self, adapter: ECGAdapter) -> None:
        with pytest.raises(AdapterParseError, match="amplitude"):
            adapter.parse("DAT|72|xyz|II")

    def test_dat_frame_invalid_lead_raises(self, adapter: ECGAdapter) -> None:
        with pytest.raises(AdapterParseError, match="lead"):
            adapter.parse("DAT|72|0.84|INVALID_LEAD")

    def test_wfm_frame_returns_single_reading(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("WFM|II|500|0.12,0.14,0.95,1.02,0.87")
        assert len(readings) == 1
        assert readings[0].metric == MetricType.ECG_WAVEFORM

    def test_wfm_frame_value_is_list_of_floats(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("WFM|II|500|0.12,0.14,0.95")
        assert isinstance(readings[0].value, list)
        assert readings[0].value == [0.12, 0.14, 0.95]

    def test_wfm_frame_sampling_rate(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("WFM|II|500|0.12,0.14,0.95")
        assert readings[0].sampling_rate_hz == 500.0

    def test_wfm_empty_samples_returns_empty(self, adapter: ECGAdapter) -> None:
        readings = adapter.parse("WFM|II|500|")
        assert readings == []

    def test_wfm_invalid_samples_raises(self, adapter: ECGAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("WFM|II|500|a,b,c")

    def test_sta_ok_returns_empty(self, adapter: ECGAdapter) -> None:
        assert adapter.parse("STA|OK") == []

    def test_sta_connected_returns_empty(self, adapter: ECGAdapter) -> None:
        assert adapter.parse("STA|CONNECTED") == []

    def test_unknown_frame_type_raises(self, adapter: ECGAdapter) -> None:
        with pytest.raises(AdapterParseError, match="Unknown ECG frame type"):
            adapter.parse("XXX|123")

    def test_empty_frame_returns_empty(self, adapter: ECGAdapter) -> None:
        assert adapter.parse("") == []
        assert adapter.parse(b"") == []

    def test_non_ascii_bytes_raises(self, adapter: ECGAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse(bytes([0xFF, 0xFE]))

    def test_parse_safe_success(self, adapter: ECGAdapter) -> None:
        readings, error = adapter.parse_safe("DAT|72|0.84|II")
        assert error is None
        assert len(readings) == 2

    def test_parse_safe_failure_returns_error(self, adapter: ECGAdapter) -> None:
        readings, error = adapter.parse_safe("MALFORMED")
        assert readings == []
        assert isinstance(error, AdapterParseError)

    def test_stats_track_parse_count(self, adapter: ECGAdapter) -> None:
        adapter.parse_safe("DAT|72|0.84|II")
        adapter.parse_safe("DAT|80|0.90|I")
        assert adapter.stats["parse_count"] == 2

    def test_stats_track_error_count(self, adapter: ECGAdapter) -> None:
        adapter.parse_safe("INVALID")
        assert adapter.stats["error_count"] == 1

    def test_raw_payload_preserved(self, adapter: ECGAdapter) -> None:
        raw = "DAT|72|0.84|II"
        readings = adapter.parse(raw)
        for r in readings:
            assert r.raw_payload == raw


# ── BP Adapter Tests ──────────────────────────────────────────────────────────

class TestBPAdapter:
    @pytest.fixture(autouse=True)
    def adapter(self) -> BPAdapter:
        return BPAdapter(device_id="BP-TEST-001")

    def test_full_frame_three_readings(self, adapter: BPAdapter) -> None:
        readings = adapter.parse("SYS=120 DIA=80 MAP=93")
        assert len(readings) == 3

    def test_frame_with_pr_four_readings(self, adapter: BPAdapter) -> None:
        readings = adapter.parse("SYS=120 DIA=80 MAP=93 PR=72")
        assert len(readings) == 4

    def test_systolic_value(self, adapter: BPAdapter) -> None:
        readings = adapter.parse("SYS=120 DIA=80 MAP=93")
        sys_r = next(r for r in readings if r.metric == MetricType.SYSTOLIC_BP)
        assert sys_r.value == 120.0
        assert sys_r.unit == Unit.MMHG

    def test_diastolic_value(self, adapter: BPAdapter) -> None:
        readings = adapter.parse("SYS=120 DIA=80 MAP=93")
        dia_r = next(r for r in readings if r.metric == MetricType.DIASTOLIC_BP)
        assert dia_r.value == 80.0

    def test_map_value(self, adapter: BPAdapter) -> None:
        readings = adapter.parse("SYS=120 DIA=80 MAP=93")
        map_r = next(r for r in readings if r.metric == MetricType.MEAN_ARTERIAL_PRESSURE)
        assert map_r.value == 93.0

    def test_pr_value(self, adapter: BPAdapter) -> None:
        readings = adapter.parse("SYS=120 DIA=80 MAP=93 PR=72")
        pr_r = next(r for r in readings if r.metric == MetricType.HEART_RATE)
        assert pr_r.value == 72.0
        assert pr_r.unit == Unit.BPM

    def test_bytes_input(self, adapter: BPAdapter) -> None:
        readings = adapter.parse(b"SYS=120 DIA=80 MAP=93")
        assert len(readings) == 3

    def test_lowercase_keys(self, adapter: BPAdapter) -> None:
        readings = adapter.parse("sys=120 dia=80 map=93")
        assert len(readings) == 3

    def test_missing_sys_raises(self, adapter: BPAdapter) -> None:
        with pytest.raises(AdapterParseError, match="missing"):
            adapter.parse("DIA=80 MAP=93")

    def test_missing_dia_raises(self, adapter: BPAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("SYS=120 MAP=93")

    def test_missing_map_raises(self, adapter: BPAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("SYS=120 DIA=80")

    def test_sys_out_of_range_raises(self, adapter: BPAdapter) -> None:
        with pytest.raises(AdapterParseError, match="physiological"):
            adapter.parse("SYS=350 DIA=80 MAP=93")

    def test_dia_out_of_range_raises(self, adapter: BPAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("SYS=120 DIA=5 MAP=93")

    def test_empty_frame_returns_empty(self, adapter: BPAdapter) -> None:
        assert adapter.parse("") == []


# ── SpO2 Adapter Tests ────────────────────────────────────────────────────────

class TestSpO2Adapter:
    @pytest.fixture
    def adapter(self) -> SpO2Adapter:
        return SpO2Adapter(device_id="SPO2-TEST-001")

    @pytest.fixture
    def ble_adapter(self) -> SpO2Adapter:
        return SpO2Adapter(device_id="SPO2-TEST-BLE", config={"mode": "ble"})

    @pytest.fixture
    def ascii_adapter(self) -> SpO2Adapter:
        return SpO2Adapter(device_id="SPO2-TEST-ASCII", config={"mode": "ascii"})

    def test_ble_binary_spo2_only(self, ble_adapter: SpO2Adapter) -> None:
        payload = bytes([0x02, 98])  # sensor contact, spo2=98
        readings = ble_adapter.parse(payload)
        assert len(readings) == 1
        spo2_r = readings[0]
        assert spo2_r.metric == MetricType.SPO2
        assert spo2_r.value == 98

    def test_ble_binary_with_8bit_hr(self, ble_adapter: SpO2Adapter) -> None:
        payload = bytes([0x02, 98, 72])  # sensor contact, spo2=98, hr=72
        readings = ble_adapter.parse(payload)
        assert len(readings) == 2
        hr_r = next(r for r in readings if r.metric == MetricType.HEART_RATE)
        assert hr_r.value == 72

    def test_ble_binary_with_16bit_hr(self, ble_adapter: SpO2Adapter) -> None:
        hr = 120
        payload = bytes([0x03, 98]) + struct.pack("<H", hr)  # 16-bit HR flag set
        readings = ble_adapter.parse(payload)
        hr_r = next(r for r in readings if r.metric == MetricType.HEART_RATE)
        assert hr_r.value == 120

    def test_ble_sensor_no_contact_is_marginal(self, ble_adapter: SpO2Adapter) -> None:
        payload = bytes([0x00, 97])  # flags=0 (no sensor contact)
        readings = ble_adapter.parse(payload)
        assert readings[0].quality == ReadingQuality.MARGINAL

    def test_ble_sensor_contact_is_good(self, ble_adapter: SpO2Adapter) -> None:
        payload = bytes([0x02, 97])  # sensor contact bit set
        readings = ble_adapter.parse(payload)
        assert readings[0].quality == ReadingQuality.GOOD

    def test_ble_spo2_out_of_range_raises(self, ble_adapter: SpO2Adapter) -> None:
        payload = bytes([0x02, 30])  # 30% is impossible
        with pytest.raises(AdapterParseError):
            ble_adapter.parse(payload)

    def test_ble_payload_too_short_raises(self, ble_adapter: SpO2Adapter) -> None:
        with pytest.raises(AdapterParseError, match="too short"):
            ble_adapter.parse(bytes([0x02]))

    def test_ascii_basic_spo2(self, ascii_adapter: SpO2Adapter) -> None:
        readings = ascii_adapter.parse("SPO2=98 PR=72 SQ=good")
        spo2_r = next(r for r in readings if r.metric == MetricType.SPO2)
        assert spo2_r.value == 98.0
        assert spo2_r.quality == ReadingQuality.GOOD

    def test_ascii_with_pr(self, ascii_adapter: SpO2Adapter) -> None:
        readings = ascii_adapter.parse("SPO2=96 PR=68")
        assert len(readings) == 2

    def test_ascii_missing_spo2_raises(self, ascii_adapter: SpO2Adapter) -> None:
        with pytest.raises(AdapterParseError):
            ascii_adapter.parse("PR=72 SQ=good")

    def test_auto_mode_bytes_uses_ble(self, adapter: SpO2Adapter) -> None:
        payload = bytes([0x02, 98])
        readings = adapter.parse(payload)
        assert readings[0].metric == MetricType.SPO2

    def test_auto_mode_string_uses_ascii(self, adapter: SpO2Adapter) -> None:
        readings = adapter.parse("SPO2=98")
        assert readings[0].metric == MetricType.SPO2


# ── Ventilator Adapter Tests ──────────────────────────────────────────────────

class TestVentilatorAdapter:
    @pytest.fixture
    def adapter(self) -> VentilatorAdapter:
        return VentilatorAdapter(device_id="VENT-TEST-001")

    @pytest.fixture
    def hl7_message(self) -> str:
        return (
            "MSH|^~\\&|VENT|ICU|HELIOS|FAC|20240101120000||ORU^R01|1|P|2.5\r"
            "PID|1||PAT-001\r"
            "OBR|1|||VENT-METRICS\r"
            "OBX|1|NM|9279-1^Respiratory Rate^LN||18|breaths/min\r"
            "OBX|2|NM|76222-9^Tidal Volume^LN||500|mL\r"
            "OBX|3|NM|76003-3^PEEP^LN||5|cmH2O\r"
        )

    def test_hl7_message_parses_obx_segments(
        self, adapter: VentilatorAdapter, hl7_message: str
    ) -> None:
        readings = adapter.parse(hl7_message)
        assert len(readings) == 3

    def test_respiratory_rate_extracted(
        self, adapter: VentilatorAdapter, hl7_message: str
    ) -> None:
        readings = adapter.parse(hl7_message)
        rr = next(r for r in readings if r.metric == MetricType.RESPIRATORY_RATE)
        assert rr.value == 18.0
        assert rr.unit == Unit.BREATHS_PER_MIN

    def test_tidal_volume_extracted(
        self, adapter: VentilatorAdapter, hl7_message: str
    ) -> None:
        readings = adapter.parse(hl7_message)
        tv = next(r for r in readings if r.metric == MetricType.TIDAL_VOLUME)
        assert tv.value == 500.0
        assert tv.unit == Unit.ML

    def test_peep_extracted(
        self, adapter: VentilatorAdapter, hl7_message: str
    ) -> None:
        readings = adapter.parse(hl7_message)
        peep = next(
            r for r in readings
            if r.metric == MetricType.POSITIVE_END_EXPIRATORY_PRESSURE
        )
        assert peep.value == 5.0

    def test_no_msh_raises(self, adapter: VentilatorAdapter) -> None:
        with pytest.raises(AdapterParseError, match="MSH"):
            adapter.parse("OBX|1|NM|9279-1||18|breaths/min\r")

    def test_empty_message_returns_empty(self, adapter: VentilatorAdapter) -> None:
        assert adapter.parse("") == []

    def test_unknown_obx_code_skipped(self, adapter: VentilatorAdapter) -> None:
        msg = (
            "MSH|^~\\&|VENT|ICU|HELIOS|FAC|20240101120000||ORU^R01|1|P|2.5\r"
            "OBX|1|NM|UNKNOWN-CODE^Unknown^LN||100|units\r"
        )
        readings = adapter.parse(msg)
        assert readings == []

    def test_bytes_input(self, adapter: VentilatorAdapter, hl7_message: str) -> None:
        readings = adapter.parse(hl7_message.encode("ascii"))
        assert len(readings) == 3


# ── Infusion Adapter Tests ────────────────────────────────────────────────────

class TestInfusionAdapter:
    @pytest.fixture
    def adapter(self) -> InfusionAdapter:
        return InfusionAdapter(device_id="INF-TEST-001")

    @pytest.fixture
    def binary_adapter(self) -> InfusionAdapter:
        return InfusionAdapter(device_id="INF-BIN-001", config={"mode": "binary"})

    @pytest.fixture
    def ascii_adapter(self) -> InfusionAdapter:
        return InfusionAdapter(device_id="INF-ASCII-001", config={"mode": "ascii"})

    def _make_binary_frame(
        self,
        seq: int = 1,
        flow: float = 125.5,
        vol_del: float = 250.0,
        vol_rem: float = 250.0,
    ) -> bytes:
        flow_raw = int(flow * 100)
        vol_del_raw = int(vol_del * 10)
        vol_rem_raw = int(vol_rem * 10)
        header = b"\xAA\xBB"
        body = struct.pack("<HIII", seq, flow_raw, vol_del_raw, vol_rem_raw)
        return header + body

    def test_binary_produces_three_readings(self, binary_adapter: InfusionAdapter) -> None:
        frame = self._make_binary_frame()
        readings = binary_adapter.parse(frame)
        assert len(readings) == 3

    def test_binary_flow_rate(self, binary_adapter: InfusionAdapter) -> None:
        frame = self._make_binary_frame(flow=125.5)
        readings = binary_adapter.parse(frame)
        flow_r = next(r for r in readings if r.metric == MetricType.INFUSION_FLOW_RATE)
        assert flow_r.value == pytest.approx(125.5, rel=1e-3)
        assert flow_r.unit == Unit.ML_PER_HOUR

    def test_binary_volume_delivered(self, binary_adapter: InfusionAdapter) -> None:
        frame = self._make_binary_frame(vol_del=250.0)
        readings = binary_adapter.parse(frame)
        vd = next(r for r in readings if r.metric == MetricType.INFUSION_VOLUME_DELIVERED)
        assert vd.value == pytest.approx(250.0, rel=1e-2)

    def test_binary_invalid_magic_raises(self, binary_adapter: InfusionAdapter) -> None:
        frame = bytes([0x00, 0x00]) + struct.pack("<HIII", 1, 10000, 2500, 2500)
        with pytest.raises(AdapterParseError, match="magic"):
            binary_adapter.parse(frame)

    def test_binary_too_short_raises(self, binary_adapter: InfusionAdapter) -> None:
        with pytest.raises(AdapterParseError, match="too short"):
            binary_adapter.parse(b"\xAA\xBB\x01\x00")

    def test_auto_detect_binary_from_magic(self, adapter: InfusionAdapter) -> None:
        frame = self._make_binary_frame()
        readings = adapter.parse(frame)
        assert len(readings) == 3

    def test_ascii_full_frame(self, ascii_adapter: InfusionAdapter) -> None:
        readings = ascii_adapter.parse(
            "FLOW=125.50 VD=125.5 VR=374.5 DRUG=Morphine CONC=1.0 UNIT=mg/mL"
        )
        metrics = {r.metric for r in readings}
        assert MetricType.INFUSION_FLOW_RATE in metrics
        assert MetricType.INFUSION_VOLUME_DELIVERED in metrics
        assert MetricType.INFUSION_VOLUME_REMAINING in metrics
        assert MetricType.INFUSION_DRUG_NAME in metrics
        assert MetricType.INFUSION_CONCENTRATION in metrics

    def test_ascii_missing_flow_raises(self, ascii_adapter: InfusionAdapter) -> None:
        with pytest.raises(AdapterParseError, match="FLOW"):
            ascii_adapter.parse("VD=100 VR=400")

    def test_ascii_flow_out_of_range_raises(self, ascii_adapter: InfusionAdapter) -> None:
        with pytest.raises(AdapterParseError):
            ascii_adapter.parse("FLOW=99999 VD=100 VR=400")


# ── Glucometer Adapter Tests ──────────────────────────────────────────────────

class TestGlucometerAdapter:
    @pytest.fixture
    def adapter(self) -> GlucometerAdapter:
        return GlucometerAdapter(device_id="GLU-TEST-001")

    def test_mmol_frame(self, adapter: GlucometerAdapter) -> None:
        readings = adapter.parse("GLU=7.2 UNIT=mmol/L MID=before_meal SN=00234")
        assert len(readings) == 1
        r = readings[0]
        assert r.metric == MetricType.BLOOD_GLUCOSE
        assert r.value == 7.2
        assert r.unit == Unit.MMOL_PER_L

    def test_mgdl_frame(self, adapter: GlucometerAdapter) -> None:
        readings = adapter.parse("GLU=130 UNIT=mg/dL MID=after_meal")
        r = readings[0]
        assert r.value == 130.0
        assert r.unit == Unit.MG_PER_DL

    def test_compact_format(self, adapter: GlucometerAdapter) -> None:
        readings = adapter.parse("G=7.4 U=mmol/L")
        assert readings[0].value == 7.4

    def test_meal_timing_in_metadata(self, adapter: GlucometerAdapter) -> None:
        readings = adapter.parse("GLU=7.2 UNIT=mmol/L MID=before_meal")
        assert readings[0].metadata.get("meal_timing") == "pre-meal"

    def test_serial_number_in_metadata(self, adapter: GlucometerAdapter) -> None:
        readings = adapter.parse("GLU=7.2 UNIT=mmol/L SN=00234")
        assert readings[0].metadata.get("device_serial") == "00234"

    def test_mmol_out_of_range_raises(self, adapter: GlucometerAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("GLU=50.0 UNIT=mmol/L")

    def test_mgdl_out_of_range_raises(self, adapter: GlucometerAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("GLU=700 UNIT=mg/dL")

    def test_missing_glu_raises(self, adapter: GlucometerAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("UNIT=mmol/L MID=fasting")

    def test_non_numeric_glu_raises(self, adapter: GlucometerAdapter) -> None:
        with pytest.raises(AdapterParseError):
            adapter.parse("GLU=abc UNIT=mmol/L")

    def test_bytes_input(self, adapter: GlucometerAdapter) -> None:
        readings = adapter.parse(b"GLU=7.2 UNIT=mmol/L")
        assert readings[0].value == 7.2

    def test_empty_returns_empty(self, adapter: GlucometerAdapter) -> None:
        assert adapter.parse("") == []


# ── Registry Integration Tests ────────────────────────────────────────────────

class TestAdapterRegistry:
    def setup_method(self) -> None:
        """Clear registry before each test."""
        AdapterRegistry.clear()

    def teardown_method(self) -> None:
        """Restore registry after each test."""
        AdapterRegistry.clear()
        # Re-discover adapters
        from mdil.registry import get_registry
        r = get_registry()
        r._discovered = False

    def test_auto_discover_registers_all_adapters(self) -> None:
        from mdil.registry import AdapterRegistry
        registry = AdapterRegistry()
        registry.auto_discover()
        registered = AdapterRegistry.all_registered()
        assert "ecg" in registered
        assert "blood_pressure" in registered
        assert "spo2" in registered
        assert "ventilator" in registered
        assert "infusion_pump" in registered
        assert "glucometer" in registered

    def test_create_ecg_adapter(self) -> None:
        from mdil.registry import AdapterRegistry
        registry = AdapterRegistry()
        registry.auto_discover()
        adapter = registry.create("ecg", device_id="ECG-001")
        assert isinstance(adapter, ECGAdapter)

    def test_unknown_device_type_raises(self) -> None:
        from mdil.registry import AdapterRegistry, AdapterNotFoundError
        registry = AdapterRegistry()
        registry.auto_discover()
        with pytest.raises(AdapterNotFoundError):
            registry.create("unknown_device_xyz", device_id="X-001")
