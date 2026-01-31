#!/usr/bin/env python3
"""Update existing projects with default color and icon values."""

import sys
import os
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import text
from src.core.database.postgres import get_async_postgres_engine


async def main():
    engine = get_async_postgres_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("UPDATE projects SET color = '#7c3aed' WHERE color IS NULL")
        )
        print(f"✅ Updated {result.rowcount} projects with default color")
        
        result = await conn.execute(
            text("UPDATE projects SET icon = '📁' WHERE icon IS NULL")
        )
        print(f"✅ Updated {result.rowcount} projects with default icon")
        
        # Verify
        result = await conn.execute(
            text("SELECT name, color, icon FROM projects")
        )
        projects = result.fetchall()
        print(f"\n📊 All projects:")
        for p in projects:
            print(f"  - {p[0]}: {p[2]} {p[1]}")


if __name__ == "__main__":
    asyncio.run(main())
