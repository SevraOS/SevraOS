"""
Alembic Migration Script
Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-06-17 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Patients Table
    op.create_table(
        'patients',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('mrn', sa.String(64), unique=True, index=True, nullable=False),
        sa.Column('first_name', sa.String(128), nullable=True),
        sa.Column('last_name', sa.String(128), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(32), nullable=True),
        sa.Column('location', sa.String(128), index=True, nullable=True),
        sa.Column('metadata_payload', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Base columns
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('created_by', sa.String(128), nullable=False),
        sa.Column('updated_by', sa.String(128), nullable=False),
        sa.Column('sync_status', sa.String(16), nullable=False, index=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True)
    )

    # Vitals Table
    op.create_table(
        'vitals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('client_event_id', sa.String(36), unique=True, index=True, nullable=False),
        sa.Column('patient_id', sa.String(36), index=True, nullable=False),
        sa.Column('metric', sa.String(64), index=True, nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(32), nullable=False),
        sa.Column('loinc', sa.String(32), index=True, nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_device', sa.String(128), index=True, nullable=False),
        sa.Column('flagged', sa.Boolean(), index=True, nullable=False),
        sa.Column('metadata_payload', sa.JSON(), nullable=True),
        
        # Base columns
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('created_by', sa.String(128), nullable=False),
        sa.Column('updated_by', sa.String(128), nullable=False),
        sa.Column('sync_status', sa.String(16), nullable=False, index=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True)
    )

    # Creating composite indexes for Vitals as per Section 4
    op.create_index('ix_vitals_patient_metric_captured', 'vitals', ['patient_id', 'metric', 'captured_at'])
    op.create_index('ix_vitals_patient_captured', 'vitals', ['patient_id', 'captured_at'])
    op.create_index('ix_vitals_sync_status', 'vitals', ['sync_status', 'created_at'])

def downgrade() -> None:
    op.drop_index('ix_vitals_sync_status', table_name='vitals')
    op.drop_index('ix_vitals_patient_captured', table_name='vitals')
    op.drop_index('ix_vitals_patient_metric_captured', table_name='vitals')
    op.drop_table('vitals')
    op.drop_table('patients')
