"""add_project_color_and_icon

Revision ID: 1f67da69fdd2
Revises: 
Create Date: 2026-01-28 17:15:36.564440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1f67da69fdd2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename table from 'project' to 'projects' if it doesn't exist
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'project')
               AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'projects')
            THEN
                ALTER TABLE project RENAME TO projects;
            END IF;
        END $$;
    """)
    
    # Add color column if it doesn't exist
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'projects' AND column_name = 'color')
            THEN
                ALTER TABLE projects ADD COLUMN color VARCHAR NOT NULL DEFAULT '#7c3aed';
            END IF;
        END $$;
    """)
    
    # Add icon column if it doesn't exist
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'projects' AND column_name = 'icon')
            THEN
                ALTER TABLE projects ADD COLUMN icon VARCHAR NOT NULL DEFAULT '📁';
            END IF;
        END $$;
    """)
    
    # Update foreign key constraint
    op.execute("""
        DO $$ 
        BEGIN
            -- Drop old constraint if exists
            IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
                      WHERE constraint_name = 'chatsession_project_id_fkey'
                      AND table_name = 'chatsession')
            THEN
                ALTER TABLE chatsession DROP CONSTRAINT chatsession_project_id_fkey;
            END IF;
            
            -- Add new constraint
            IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                          WHERE constraint_name = 'chatsession_project_id_fkey'
                          AND table_name = 'chatsession')
            THEN
                ALTER TABLE chatsession ADD CONSTRAINT chatsession_project_id_fkey 
                    FOREIGN KEY (project_id) REFERENCES projects(id);
            END IF;
        END $$;
    """)
    
    # Update existing rows with null values to have defaults
    op.execute("UPDATE projects SET color = '#7c3aed' WHERE color IS NULL;")
    op.execute("UPDATE projects SET icon = '📁' WHERE icon IS NULL;")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove color and icon columns
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS color;")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS icon;")
    
    # Rename back to project
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'projects')
            THEN
                ALTER TABLE projects RENAME TO project;
            END IF;
        END $$;
    """)
    
    # Update foreign key back
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
                      WHERE constraint_name = 'chatsession_project_id_fkey')
            THEN
                ALTER TABLE chatsession DROP CONSTRAINT chatsession_project_id_fkey;
                ALTER TABLE chatsession ADD CONSTRAINT chatsession_project_id_fkey 
                    FOREIGN KEY (project_id) REFERENCES project(id);
            END IF;
        END $$;
    """)
