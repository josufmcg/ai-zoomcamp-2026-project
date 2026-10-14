"""add initiatives, options, and votes

Adds the three tables behind community voting (backlog task 12).
``initiatives`` stores the title, description, open and close dates, and the
eligible scope as a JSON document so any combination of community, building,
unit-type, and tag filters can be expressed without extra tables.
``initiative_options`` holds the two-or-more choices, and ``votes`` records one
ballot per unit: ``uq_vote_initiative_unit`` makes a second ballot for the same
unit impossible, which is what enforces the one-vote-per-unit rule under
concurrent requests.

Revision ID: 1f2a3b4c5d67
Revises: 8b9d0e1f2c34
Create Date: 2026-10-14 11:40:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f2a3b4c5d67"
down_revision: str | None = "8b9d0e1f2c34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "initiatives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("opens_at", sa.Date(), nullable=False),
        sa.Column("closes_at", sa.Date(), nullable=False),
        # Portable JSON: JSONB on PostgreSQL would be an option, but the scope
        # document is small and always read as a whole, so the standard type
        # keeps SQLite and PostgreSQL behaviour identical.
        sa.Column(
            "scope",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_initiatives_created_by_id"),
        "initiatives",
        ["created_by_id"],
        unique=False,
    )

    op.create_table(
        "initiative_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiatives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("initiative_id", "label", name="uq_initiative_option_label"),
        sa.UniqueConstraint("initiative_id", "position", name="uq_initiative_option_position"),
    )
    op.create_index(
        op.f("ix_initiative_options_initiative_id"),
        "initiative_options",
        ["initiative_id"],
        unique=False,
    )

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("voter_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("unit_id > 0", name="ck_vote_unit_positive"),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiatives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["option_id"], ["initiative_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("initiative_id", "unit_id", name="uq_vote_initiative_unit"),
    )
    op.create_index(op.f("ix_votes_initiative_id"), "votes", ["initiative_id"], unique=False)
    op.create_index(op.f("ix_votes_unit_id"), "votes", ["unit_id"], unique=False)
    op.create_index(op.f("ix_votes_voter_id"), "votes", ["voter_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_votes_voter_id"), table_name="votes")
    op.drop_index(op.f("ix_votes_unit_id"), table_name="votes")
    op.drop_index(op.f("ix_votes_initiative_id"), table_name="votes")
    op.drop_table("votes")

    op.drop_index(
        op.f("ix_initiative_options_initiative_id"),
        table_name="initiative_options",
    )
    op.drop_table("initiative_options")

    op.drop_index(op.f("ix_initiatives_created_by_id"), table_name="initiatives")
    op.drop_table("initiatives")
