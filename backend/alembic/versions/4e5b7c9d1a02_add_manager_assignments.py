"""add manager community assignments

Adds the ``manager_assignments`` table that gives a manager write access to a
community (backlog task 8). Administrators have global scope and are never
stored here. The ``uq_manager_assignment_pair`` constraint stops the same
manager-community pair being recorded twice.

Revision ID: 4e5b7c9d1a02
Revises: d2d19ee792db
Create Date: 2026-10-14 11:10:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e5b7c9d1a02"
down_revision: str | None = "d2d19ee792db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manager_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manager_id", sa.Integer(), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manager_id", "community_id", name="uq_manager_assignment_pair"),
    )
    op.create_index(
        op.f("ix_manager_assignments_community_id"),
        "manager_assignments",
        ["community_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_manager_assignments_manager_id"),
        "manager_assignments",
        ["manager_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_manager_assignments_manager_id"),
        table_name="manager_assignments",
    )
    op.drop_index(
        op.f("ix_manager_assignments_community_id"),
        table_name="manager_assignments",
    )
    op.drop_table("manager_assignments")
