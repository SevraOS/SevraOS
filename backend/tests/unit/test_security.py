"""Tests for JWT and RBAC security framework."""

import pytest
from jose import jwt

from core.exceptions.base import AuthorizationException, TokenExpiredException, TokenInvalidException
from core.security.jwt import JWTManager, TokenPair
from core.security.rbac import Permission, RBACChecker, Role


class TestJWTManager:
    """JWT token creation and validation tests."""

    def setup_method(self) -> None:
        self.manager = JWTManager()

    def test_create_token_pair_returns_two_tokens(self) -> None:
        pair = self.manager.create_token_pair(
            user_id="user-001",
            roles=[Role.CLINICIAN],
            facility_id="FACILITY-001",
        )
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "Bearer"
        assert pair.expires_in == 900  # 15 minutes

    def test_decode_valid_access_token(self) -> None:
        pair = self.manager.create_token_pair(
            user_id="user-001",
            roles=[Role.NURSE],
        )
        payload = self.manager.decode_token(pair.access_token)
        assert payload.sub == "user-001"
        assert payload.token_type == "access"
        assert Role.NURSE in payload.roles

    def test_decode_invalid_token_raises(self) -> None:
        with pytest.raises(TokenInvalidException):
            self.manager.decode_token("this.is.invalid")

    def test_refresh_token_is_different_from_access_token(self) -> None:
        pair = self.manager.create_token_pair(user_id="user-001", roles=[Role.ADMIN])
        assert pair.access_token != pair.refresh_token

    def test_decode_refresh_token_rejects_access_token(self) -> None:
        pair = self.manager.create_token_pair(user_id="user-001", roles=[Role.ADMIN])
        with pytest.raises(TokenInvalidException):
            self.manager.decode_refresh_token(pair.access_token)

    def test_token_contains_facility_id(self) -> None:
        pair = self.manager.create_token_pair(
            user_id="user-001",
            roles=[Role.CLINICIAN],
            facility_id="FACILITY-XYZ",
        )
        payload = self.manager.decode_token(pair.access_token)
        assert payload.facility_id == "FACILITY-XYZ"


class TestRBACChecker:
    """RBAC permission checking tests."""

    def test_admin_has_all_permissions(self) -> None:
        assert RBACChecker.has_permission([Role.ADMIN], Permission.READ_PATIENT_VITALS)
        assert RBACChecker.has_permission([Role.ADMIN], Permission.MANAGE_USERS)
        assert RBACChecker.has_permission([Role.ADMIN], Permission.READ_AUDIT_LOGS)

    def test_clinician_can_read_vitals(self) -> None:
        assert RBACChecker.has_permission([Role.CLINICIAN], Permission.READ_PATIENT_VITALS)

    def test_clinician_cannot_manage_users(self) -> None:
        assert not RBACChecker.has_permission([Role.CLINICIAN], Permission.MANAGE_USERS)

    def test_nurse_can_acknowledge_alerts(self) -> None:
        assert RBACChecker.has_permission([Role.NURSE], Permission.ACKNOWLEDGE_ALERTS)

    def test_nurse_cannot_register_devices(self) -> None:
        assert not RBACChecker.has_permission([Role.NURSE], Permission.REGISTER_DEVICE)

    def test_auditor_can_read_audit_logs(self) -> None:
        assert RBACChecker.has_permission([Role.AUDITOR], Permission.READ_AUDIT_LOGS)

    def test_auditor_cannot_write_clinical_notes(self) -> None:
        assert not RBACChecker.has_permission([Role.AUDITOR], Permission.WRITE_CLINICAL_NOTES)

    def test_device_operator_can_register_device(self) -> None:
        assert RBACChecker.has_permission([Role.DEVICE_OPERATOR], Permission.REGISTER_DEVICE)

    def test_device_operator_cannot_read_patient_vitals(self) -> None:
        assert not RBACChecker.has_permission(
            [Role.DEVICE_OPERATOR], Permission.READ_PATIENT_VITALS
        )

    def test_unknown_role_is_ignored(self) -> None:
        perms = RBACChecker.get_permissions_for_roles(["unknown_role"])
        assert len(perms) == 0

    def test_multiple_roles_union_permissions(self) -> None:
        # Nurse + Auditor should grant both sets
        assert RBACChecker.has_permission(
            [Role.NURSE, Role.AUDITOR], Permission.ACKNOWLEDGE_ALERTS
        )
        assert RBACChecker.has_permission(
            [Role.NURSE, Role.AUDITOR], Permission.READ_AUDIT_LOGS
        )
