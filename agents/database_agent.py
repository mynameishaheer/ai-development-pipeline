"""
Database Agent for AI Development Pipeline
Handles database schema design, migrations, query optimization, and data integrity
"""

from pathlib import Path
from typing import Dict, List, Optional

from agents.base_agent import BaseAgent
from utils.constants import AgentType


class DatabaseAgent(BaseAgent):
    """
    Database Design and Management Agent

    Responsibilities:
    - Design database schemas from PRD requirements
    - Generate SQLAlchemy models
    - Create Alembic migration scripts
    - Optimize slow queries
    - Validate data integrity constraints
    - Create database seed data
    - Generate ER diagrams (text-based)
    """

    def __init__(self, agent_id: Optional[str] = None):
        """Initialize Database Agent"""
        super().__init__(
            agent_type=AgentType.DATABASE,
            agent_id=agent_id
        )
        self.logger.info("Database Agent initialized")

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [
            "Design database schemas from PRD",
            "Generate SQLAlchemy models",
            "Create Alembic migrations",
            "Optimize database queries",
            "Validate data integrity",
            "Create seed data",
            "Generate ER diagrams",
            "Support PostgreSQL and SQLite",
        ]

    async def execute_task(self, task: Dict) -> Dict:
        """
        Execute a database task

        Args:
            task: Task dictionary with task details

        Returns:
            Result dictionary
        """
        task_type = task.get("task_type", "design_schema")

        handlers = {
            "design_schema": self.design_schema,
            "create_migrations": self.create_migrations,
            "optimize_queries": self.optimize_queries,
            "create_seed_data": self.create_seed_data,
            "validate_integrity": self.validate_integrity,
        }

        handler = handlers.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")

        return await handler(task)

    # ==========================================
    # SCHEMA DESIGN
    # ==========================================

    async def design_schema(self, task: Dict) -> Dict:
        """
        Design database schema from PRD requirements

        Creates:
        - SQLAlchemy model classes
        - Relationship definitions
        - Indexes and constraints
        - Database configuration

        Args:
            task: Task with 'prd_path' and 'project_path'

        Returns:
            Result with generated schema files
        """
        prd_path = task.get("prd_path", "")
        project_path = task.get("project_path", "")
        db_type = task.get("db_type", "postgresql")

        await self.log_action("design_schema", "started", {
            "project": project_path,
            "db_type": db_type
        })

        # Read PRD content
        prd_content = ""
        if prd_path and Path(prd_path).exists():
            with open(prd_path, "r") as f:
                prd_content = f.read()[:8000]

        prompt = f"""
You are an expert database architect designing a production-grade database schema.

Database Type: {db_type}
Project Path: {project_path}

PRD Requirements:
{prd_content if prd_content else "Create a general-purpose schema based on the project structure."}

Your tasks:

1. **Analyze requirements** and identify all entities, relationships, and constraints

2. **Create `src/database/models.py`** with SQLAlchemy models:
   ```python
   from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Numeric
   from sqlalchemy.orm import relationship, DeclarativeBase
   from sqlalchemy.sql import func
   import uuid

   class Base(DeclarativeBase):
       pass

   # Add all model classes here with:
   # - Primary keys (UUID preferred)
   # - Timestamps (created_at, updated_at)
   # - Proper relationships with back_populates
   # - Indexes on frequently queried columns
   # - Unique constraints where needed
   # - Nullable/non-nullable as appropriate
   ```

3. **Create `src/database/database.py`** with connection setup:
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   import os
   from .models import Base

   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
   engine = create_engine(DATABASE_URL)
   SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

   def get_db():
       db = SessionLocal()
       try:
           yield db
       finally:
           db.close()

   def create_tables():
       Base.metadata.create_all(bind=engine)
   ```

4. **Create `src/database/__init__.py`** to export models

5. **Create `docs/DATABASE_SCHEMA.md`** documenting:
   - All tables with column descriptions
   - Relationships (ERD in text format)
   - Indexes and their purpose
   - Key constraints

Ensure all models:
- Use UUID primary keys (not auto-increment integers)
- Have created_at and updated_at timestamps with server defaults
- Include proper docstrings
- Have appropriate indexes for foreign keys
- Use Enum types where applicable
- Follow naming conventions (snake_case for columns, PascalCase for classes)
"""

        try:
            result = await self.call_claude_code(
                prompt=prompt,
                project_path=project_path,
                allowed_tools=["Write", "Edit", "Read", "Bash"]
            )

            # Check that models file was created
            models_path = Path(project_path) / "src" / "database" / "models.py"
            schema_doc = Path(project_path) / "docs" / "DATABASE_SCHEMA.md"

            files_created = []
            if models_path.exists():
                files_created.append(str(models_path))
            if schema_doc.exists():
                files_created.append(str(schema_doc))

            await self.log_action("design_schema", "completed", {
                "files_created": files_created
            })

            await self.send_status_update("schema_designed", {
                "project": project_path,
                "files": files_created
            })

            return {
                "success": True,
                "files_created": files_created,
                "db_type": db_type,
                "message": "Database schema designed successfully"
            }

        except Exception as e:
            await self.log_action("design_schema", "failed", {"error": str(e)})
            raise

    # ==========================================
    # MIGRATIONS
    # ==========================================

    async def create_migrations(self, task: Dict) -> Dict:
        """
        Set up Alembic and create initial migration

        Args:
            task: Task with 'project_path'

        Returns:
            Result with migration files
        """
        project_path = task.get("project_path", "")

        await self.log_action("create_migrations", "started", {"project": project_path})

        prompt = f"""
Set up Alembic migrations for the SQLAlchemy project.

Project path: {project_path}

Steps:

1. **Install Alembic** (if not already installed):
   Run: pip install alembic 2>/dev/null || echo "Already installed"

2. **Initialize Alembic** (if alembic/ directory doesn't exist):
   Run: alembic init alembic

3. **Update `alembic/env.py`** to import the models:
   ```python
   from src.database.models import Base
   target_metadata = Base.metadata
   ```
   Also update the database URL to use the DATABASE_URL environment variable.

4. **Create initial migration**:
   Run: alembic revision --autogenerate -m "initial_schema"

5. **Create `scripts/migrate.sh`**:
   ```bash
   #!/bin/bash
   echo "Running database migrations..."
   alembic upgrade head
   echo "Migrations complete!"
   ```
   Make it executable: chmod +x scripts/migrate.sh

6. **Create `scripts/rollback.sh`**:
   ```bash
   #!/bin/bash
   echo "Rolling back last migration..."
   alembic downgrade -1
   echo "Rollback complete!"
   ```
   Make it executable: chmod +x scripts/rollback.sh

7. **Create `docs/MIGRATIONS.md`** documenting:
   - How to run migrations
   - How to create new migrations
   - How to rollback
   - Migration history

Only run alembic commands if the models file exists at src/database/models.py.
If it doesn't exist, create placeholder migration files manually.
"""

        try:
            result = await self.call_claude_code(
                prompt=prompt,
                project_path=project_path,
                allowed_tools=["Write", "Edit", "Bash", "Read"]
            )

            # Check for created files
            alembic_dir = Path(project_path) / "alembic"
            migrations_doc = Path(project_path) / "docs" / "MIGRATIONS.md"

            await self.log_action("create_migrations", "completed", {
                "alembic_initialized": alembic_dir.exists(),
                "docs_created": migrations_doc.exists()
            })

            return {
                "success": True,
                "alembic_initialized": alembic_dir.exists(),
                "message": "Migrations set up successfully"
            }

        except Exception as e:
            await self.log_action("create_migrations", "failed", {"error": str(e)})
            raise

    # ==========================================
    # QUERY OPTIMIZATION
    # ==========================================

    async def optimize_queries(self, task: Dict) -> Dict:
        """
        Analyze and optimize slow database queries

        Args:
            task: Task with 'project_path' and optional 'slow_queries'

        Returns:
            Optimization report
        """
        project_path = task.get("project_path", "")
        slow_queries = task.get("slow_queries", [])

        await self.log_action("optimize_queries", "started", {"project": project_path})

        queries_text = ""
        if slow_queries:
            queries_text = "\n\nSlow queries to optimize:\n" + "\n".join(
                [f"- {q}" for q in slow_queries]
            )

        prompt = f"""
Analyze the database models and optimize query performance.

Project path: {project_path}
{queries_text}

Tasks:

1. **Read the models file** (src/database/models.py) and analyze the schema

2. **Identify optimization opportunities**:
   - Missing indexes on foreign keys or frequently filtered columns
   - N+1 query patterns in the codebase
   - Large table scans that could use indexes
   - Missing composite indexes for common query patterns

3. **Create `src/database/indexes.py`** with index definitions:
   ```python
   from sqlalchemy import Index
   from .models import Base, YourModel

   # Add performance indexes
   Index('ix_table_column', YourModel.column)
   Index('ix_table_composite', YourModel.col1, YourModel.col2)
   ```

4. **Create a migration** for the new indexes:
   Run: alembic revision --autogenerate -m "add_performance_indexes"

5. **Create `docs/QUERY_OPTIMIZATION.md`** with:
   - Index strategy explanation
   - Common query patterns and how to use them efficiently
   - Caching recommendations
   - Query examples using SQLAlchemy ORM

If models.py doesn't exist, create the optimization guide based on best practices.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Bash", "Read"]
        )

        await self.log_action("optimize_queries", "completed", {})

        return {
            "success": True,
            "message": "Query optimization analysis complete",
            "details": result.get("stdout", "")[:500]
        }

    # ==========================================
    # SEED DATA
    # ==========================================

    async def create_seed_data(self, task: Dict) -> Dict:
        """
        Create database seed data for development and testing

        Args:
            task: Task with 'project_path'

        Returns:
            Result with seed files
        """
        project_path = task.get("project_path", "")

        await self.log_action("create_seed_data", "started", {"project": project_path})

        prompt = f"""
Create database seed data for development and testing purposes.

Project path: {project_path}

Tasks:

1. **Read the models** (src/database/models.py) to understand the data structure

2. **Create `scripts/seed_db.py`**:
   ```python
   #!/usr/bin/env python
   \"\"\"Seed database with initial development data\"\"\"
   import sys
   import os
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

   from src.database.database import SessionLocal, create_tables
   from src.database.models import *  # Import all models

   def seed():
       create_tables()
       db = SessionLocal()
       try:
           # Add realistic seed data for each model
           # Use Faker-like data that makes sense for the domain
           # ...
           db.commit()
           print("✅ Database seeded successfully!")
       except Exception as e:
           db.rollback()
           print(f"❌ Seeding failed: {{e}}")
           raise
       finally:
           db.close()

   if __name__ == "__main__":
       seed()
   ```

3. **Create `tests/fixtures.py`** with pytest fixtures:
   ```python
   import pytest
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   from src.database.models import Base

   @pytest.fixture
   def test_db():
       engine = create_engine("sqlite:///:memory:")
       Base.metadata.create_all(engine)
       SessionLocal = sessionmaker(bind=engine)
       db = SessionLocal()
       yield db
       db.close()
       Base.metadata.drop_all(engine)
   ```

Make the seed data realistic and domain-appropriate based on the models.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Edit", "Read"]
        )

        seed_script = Path(project_path) / "scripts" / "seed_db.py"

        await self.log_action("create_seed_data", "completed", {
            "seed_script_created": seed_script.exists()
        })

        return {
            "success": True,
            "seed_script": str(seed_script) if seed_script.exists() else None,
            "message": "Seed data created successfully"
        }

    # ==========================================
    # DATA INTEGRITY
    # ==========================================

    async def validate_integrity(self, task: Dict) -> Dict:
        """
        Validate database integrity constraints and relationships

        Args:
            task: Task with 'project_path'

        Returns:
            Integrity validation report
        """
        project_path = task.get("project_path", "")

        await self.log_action("validate_integrity", "started", {"project": project_path})

        prompt = f"""
Validate database integrity for the project at {project_path}.

Tasks:

1. **Read and analyze** src/database/models.py

2. **Create `tests/test_database_integrity.py`** that validates:
   - All foreign key relationships are valid
   - Required fields have NOT NULL constraints
   - Unique constraints are properly defined
   - Cascade deletes are correctly configured
   - All many-to-many relationships work correctly

3. **Check for common integrity issues**:
   - Orphaned records potential (missing cascade rules)
   - Missing NOT NULL where required
   - Missing UNIQUE constraints on email, username fields
   - Missing indexes on foreign keys
   - Circular foreign key references

4. **Create `docs/DATA_INTEGRITY.md`** documenting:
   - Integrity constraints in place
   - Validation rules
   - Any known data quality issues
   - Recommendations for improvement

Run any tests if the database is available.
"""

        result = await self.call_claude_code(
            prompt=prompt,
            project_path=project_path,
            allowed_tools=["Write", "Read", "Bash"]
        )

        await self.log_action("validate_integrity", "completed", {})

        return {
            "success": True,
            "message": "Integrity validation complete",
            "details": result.get("stdout", "")[:500]
        }

    # ==========================================
    # FULL SETUP WORKFLOW
    # ==========================================

    async def setup_database_for_project(
        self,
        project_path: str,
        prd_path: str,
        db_type: str = "postgresql"
    ) -> Dict:
        """
        Complete database setup workflow:
        1. Design schema from PRD
        2. Create migrations
        3. Create seed data

        Args:
            project_path: Path to project
            prd_path: Path to PRD document
            db_type: Database type (postgresql, sqlite)

        Returns:
            Complete setup result
        """
        await self.log_action("setup_database", "started", {
            "project": project_path,
            "db_type": db_type
        })

        results = {}

        # Step 1: Design schema
        schema_result = await self.design_schema({
            "task_type": "design_schema",
            "project_path": project_path,
            "prd_path": prd_path,
            "db_type": db_type,
        })
        results["schema"] = schema_result

        # Step 2: Create migrations
        migration_result = await self.create_migrations({
            "task_type": "create_migrations",
            "project_path": project_path,
        })
        results["migrations"] = migration_result

        # Step 3: Create seed data
        seed_result = await self.create_seed_data({
            "task_type": "create_seed_data",
            "project_path": project_path,
        })
        results["seed_data"] = seed_result

        await self.log_action("setup_database", "completed", {
            "steps_completed": len(results)
        })

        return {
            "success": True,
            "results": results,
            "message": "Database setup complete"
        }


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

async def setup_database(
    project_path: str,
    prd_path: str,
    db_type: str = "postgresql"
) -> Dict:
    """
    Quick function to set up a database for a project

    Args:
        project_path: Project directory path
        prd_path: Path to PRD document
        db_type: Database type

    Returns:
        Setup result
    """
    db_agent = DatabaseAgent()
    return await db_agent.setup_database_for_project(project_path, prd_path, db_type)


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    import asyncio

    async def test_database_agent():
        """Test Database Agent"""
        agent = DatabaseAgent()
        print(f"Database Agent: {agent}")
        print(f"Capabilities: {agent.get_capabilities()}")
        print("Database Agent initialized successfully!")

    asyncio.run(test_database_agent())
