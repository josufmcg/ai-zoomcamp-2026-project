"""add incidences and comments

Adds the ``incidences`` and ``comments`` tables (backlog task 11). The
incidence status is restricted to the four lifecycle stages, in order, and the
comments table stores the single conversation thread attached to each
incidence. The lifecycle *order* is enforced in the application, not by a
constraint, because it is a rule about transitions rather than about the value
a row may hold.

Revision ID: 8b9d0e1f2c34
Revises: 6a7c8e9f0b13
Create Date: 2026-10-14 11:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b9d0e1f2c34"
down_revision: str | None = "6a7c8e9f0b13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

incidence_status = sa.Enum(
    "submitted",
    "in progress",
    "resolved",
    "closed",
    name="incidence_status",
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "incidences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", incidence_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_incidences_created_by_id"),
        "incidences",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(op.f("ix_incidences_unit_id"), "incidences", ["unit_id"], unique=False)

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incidence_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incidence_id"], ["incidences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comments_author_id"), "comments", ["author_id"], unique=False)
    op.create_index(
        op.f("ix_comments_incidence_id"),
        "comments",
        ["incidence_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_comments_incidence_id"), table_name="comments")
    op.drop_index(op.f("ix_comments_author_id"), table_name="comments")
    op.drop_table("comments")

    op.drop_index(op.f("ix_incidences_unit_id"), table_name="incidences")
    op.drop_index(op.f("ix_incidences_created_by_id"), table_name="incidences")
    op.drop_table("incidences")

    # PostgreSQL keeps the native enum type after its table is dropped.
    incidence_status.drop(op.get_bind(), checkfirst=True)
