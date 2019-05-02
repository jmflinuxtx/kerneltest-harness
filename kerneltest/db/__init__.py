"""
This package contains all the database-related code, including SQLAlchemy
database models and Alembic migrations.

This application expects users to create new databases with an SQLAlchemy
script and use Alembic for database migrations only. It does not provide an
Alembic migration path from an empty database to the latest revision.
"""

from .meta import (  # noqa: F401
    Base,
    initialize,
    Session,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)
from .models import Release, TestRun, Test  # noqa: F401
