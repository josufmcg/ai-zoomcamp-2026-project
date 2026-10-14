"""create property hierarchy and tags

Creates the Community -> Building -> Unit hierarchy, the shared Tag table, and
the building/unit tag association tables (backlog task 5).

Revision ID: 037df15570b5
Revises:
Create Date: 2026-10-14 08:47:46.465106

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "037df15570b5"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The unit type enum. On PostgreSQL this is a native enum type; SQLAlchemy
# creates it when the `units` table is created and drops it when the table is
# dropped. On SQLite it becomes a VARCHAR with a CHECK constraint created as
# part of the table.
unit_type = sa.Enum("apartment", "garage", "storage", name="unit_type", create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "communities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("community_id", "name", name="uq_building_community_name"),
    )
    op.create_index(op.f("ix_buildings_community_id"), "buildings", ["community_id"], unique=False)
    op.create_table(
        "building_tags",
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("building_id", "tag_id"),
    )
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(length=100), nullable=False),
        sa.Column("unit_type", unit_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("building_id", "identifier", name="uq_unit_building_identifier"),
    )
    op.create_index(op.f("ix_units_building_id"), "units", ["building_id"], unique=False)
    op.create_table(
        "unit_tags",
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("unit_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("unit_tags")
    op.drop_index(op.f("ix_units_building_id"), table_name="units")
    op.drop_table("units")
    op.drop_table("building_tags")
    op.drop_index(op.f("ix_buildings_community_id"), table_name="buildings")
    op.drop_table("buildings")
    op.drop_table("tags")
    op.drop_table("communities")

    # PostgreSQL keeps the native enum type after its table is dropped, so
    # remove it explicitly. This is a no-op on SQLite, where the enum is a
    # VARCHAR with a CHECK constraint dropped with the table.
    unit_type.drop(op.get_bind(), checkfirst=True)
