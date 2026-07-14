"""
HELIOS OS + SEVRA AI
Tests - Migrations
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# A simple test to ensure the migration environment can load and 
# that the alembic upgrade function exists and is syntax-error free.

@pytest.mark.asyncio
async def test_migration_script_imports():
    """Verify that the initial schema script loads without errors."""
    import importlib
    initial = importlib.import_module("database.migrations.versions.001_initial_schema")
    
    assert hasattr(initial, 'upgrade')
    assert hasattr(initial, 'downgrade')
    assert initial.revision == '001_initial_schema'


