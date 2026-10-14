"""add unit assignments

Adds the ``unit_assignments`` table that links residents to the units they own
or rent (backlog task 7). The ownership flag is restricted to owner or tenant:
a native enum on PostgreSQL, a ``VARCHAR`` with a ``CHECK`` constraint on
SQLite. A unit has at most one assignment (``uq_unit_assignment_unit``), while
a resident may hold many units.

Revision ID: d2d19ee792db
Revises: f2f4be9190a5
Create Date: 2026-10-14 09:44:59.860356

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2d19ee792db"
down_revision: str | None = "f2f4be9190a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The ownership enum. On PostgreSQL this is a native enum type created with the
# table and dropped explicitly in downgrade; on SQLite it becomes a VARCHAR
# with a CHECK constraint created as part of the table.
ownership_type = sa.Enum(
    "owner",
    "tenant",
    name="ownership_type",
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "unit_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("ownership_type", ownership_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unit_id", name="uq_unit_assignment_unit"),
    )
    op.create_index(
        op.f("ix_unit_assignments_unit_id"),
        "unit_assignments",
        ["unit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_unit_assignments_user_id"),
        "unit_assignments",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_unit_assignments_user_id"), table_name="unit_assignments")
    op.drop_index(op.f("ix_unit_assignments_unit_id"), table_name="unit_assignments")
    op.drop_table("unit_assignments")

    # PostgreSQL keeps the native enum type after its table is dropped, so
    # remove it explicitly. This is a no-op on SQLite, where the enum is a
    # VARCHAR with a CHECK constraint dropped with the table.
    ownership_type.drop(op.get_bind(), checkfirst=True)
