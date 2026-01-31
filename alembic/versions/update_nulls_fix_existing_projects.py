"""Update existing projects with default color and icon values

Revision ID: update_nulls
Revises: 1f67da69fdd2
Create Date: 2026-01-28

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'update_nulls'
down_revision = '1f67da69fdd2'
branch_labels = None
depends_on = None


def upgrade():
    """Update existing null values with defaults."""
    op.execute("UPDATE projects SET color = '#7c3aed' WHERE color IS NULL;")
    op.execute("UPDATE projects SET icon = '📁' WHERE icon IS NULL;")
    print("✅ Updated existing projects with default values")


def downgrade():
    """No downgrade needed - we don't want to set values back to NULL."""
    pass
