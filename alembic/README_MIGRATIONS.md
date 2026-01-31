# Database Migrations with Alembic

This project now uses Alembic for database migrations.

## Quick Start

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (after modifying models)
alembic revision --autogenerate -m "description of changes"

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show history
alembic history --verbose
```

## Initial Setup (Already Done)

The project has been initialized with:
- `alembic init alembic` - Created alembic structure
- Configured `alembic/env.py` to use SQLModel metadata
- Configured to use PostgreSQL with environment variables from `.env`
- Created first migration for project color/icon fields

## Migration Files

Migrations are in `alembic/versions/`. Each migration has:
- `upgrade()` - Apply the changes
- `downgrade()` - Revert the changes

## Important Notes

- **Never delete migration files** - They are version controlled
- **Always run migrations on deployment** - Add `alembic upgrade head` to your deploy script
- **Test migrations** - Run upgrade/downgrade locally before deploying
- **Autogenerate is not perfect** - Always review generated migrations before applying

## Current Migrations

1. `1f67da69fdd2_add_project_color_and_icon.py` - Added color and icon columns to projects table
