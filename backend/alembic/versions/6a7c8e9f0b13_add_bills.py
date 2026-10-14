"""add bills

Adds the ``bills`` table (backlog task 10). A bill stores a manual charge for
one unit with ``NUMERIC(12, 2)`` money, an issue date, a due date, and a status
restricted to pending or paid: a native enum on PostgreSQL, a ``VARCHAR`` with
a ``CHECK`` constraint on SQLite. ``overdue`` is never stored, so no status
value is added for it.

Revision ID: 6a7c8e9f0b13
Revises: 4e5b7c9d1a02
Create Date: 2026-10-14 11:20:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a7c8e9f0b13"
down_revision: str | None = "4e5b7c9d1a02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Stored bill status. On PostgreSQL this is a native enum created with the
# table and dropped explicitly in downgrade; on SQLite it becomes a VARCHAR
# with a CHECK constraint created as part of the table.
bill_status = sa.Enum(
    "pending",
    "paid",
    name="bill_status",
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", bill_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bills_unit_id"), "bills", ["unit_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bills_unit_id"), table_name="bills")
    op.drop_table("bills")

    # PostgreSQL keeps the native enum type after its table is dropped, so
    # remove it explicitly. This is a no-op on SQLite.
    bill_status.drop(op.get_bind(), checkfirst=True)
