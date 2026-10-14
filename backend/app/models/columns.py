"""Shared helpers for model columns.

The restricted value sets of the domain (unit type, user role, ownership type,
bill status, incidence status) are all persisted the same way: a native enum on
PostgreSQL and a ``VARCHAR`` with a ``CHECK`` constraint on SQLite, driven by
the Python enum so a value can never drift from the code. This module keeps
that definition in one place instead of repeating it on every column.
"""

from __future__ import annotations

from enum import Enum as PythonEnum
from typing import Any, TypeVar

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import mapped_column

EnumType = TypeVar("EnumType", bound=PythonEnum)


def enum_column(enum_cls: type[EnumType], name: str, **kwargs: Any):
    """Return a ``mapped_column`` for a restricted-value enum.

    ``name`` is the database type name (PostgreSQL) and the base of the
    constraint name (SQLite). ``values_callable`` makes SQLAlchemy persist the
    enum *value* (``"apartment"``) rather than its member name (``APARTMENT``),
    so stored rows read the same as the API payloads. ``validate_strings``
    rejects unknown strings at the ORM boundary, and ``create_constraint``
    adds the ``CHECK`` constraint that rejects them at the database boundary
    too.
    """
    return mapped_column(
        SQLAlchemyEnum(
            enum_cls,
            name=name,
            native_enum=True,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda cls: [member.value for member in cls],
        ),
        nullable=False,
        **kwargs,
    )
