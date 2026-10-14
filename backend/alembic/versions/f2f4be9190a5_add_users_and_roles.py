"""add users and roles

Adds the ``users`` table backing authentication and role-based access (backlog
task 6). The role is restricted to administrator, manager, or resident: a
native enum on PostgreSQL, a ``VARCHAR`` with a ``CHECK`` constraint on SQLite.

Revision ID: f2f4be9190a5
Revises: 037df15570b5
Create Date: 2026-10-14 09:18:14.504325

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2f4be9190a5"
down_revision: str | None = "037df15570b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The user role enum. On PostgreSQL this is a native enum type; SQLAlchemy
# creates it when the `users` table is created and we drop it explicitly in
# downgrade. On SQLite it becomes a VARCHAR with a CHECK constraint created as
# part of the table.
user_role = sa.Enum(
    "administrator",
    "manager",
    "resident",
    name="user_role",
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def downgrade() -> None:
    op.drop_table("users")

    # PostgreSQL keeps the native enum type after its table is dropped, so
    # remove it explicitly. This is a no-op on SQLite, where the enum is a
    # VARCHAR with a CHECK constraint dropped with the table.
    user_role.drop(op.get_bind(), checkfirst=True)
