"""Pydantic schemas for the EFINGES API, grouped by area.

Each module mirrors a model module: ``auth`` for accounts, ``property`` for
the tree, tags, and unit assignments, ``billing``, ``maintenance``, and
``governance``. Every name is re-exported here so ``from app.schemas import
UserRead`` keeps working.
"""

from __future__ import annotations

from app.schemas.auth import Token, UserCreate, UserRead, UserUpdate
from app.schemas.billing import BillCreate, BillRead
from app.schemas.governance import (
    EligibleUnitRead,
    InitiativeCreate,
    InitiativeOptionCreate,
    InitiativeOptionRead,
    InitiativeRead,
    InitiativeScope,
    VoteCast,
    VoteRead,
    VoteResult,
    VoteTally,
)
from app.schemas.maintenance import (
    CommentCreate,
    CommentRead,
    IncidenceCreate,
    IncidenceRead,
    IncidenceStatusUpdate,
)
from app.schemas.property import (
    AssignmentCreate,
    AssignmentRead,
    BuildingCreate,
    BuildingRead,
    BuildingUpdate,
    CommunityCreate,
    CommunityRead,
    CommunityUpdate,
    ManagerAssignmentCreate,
    ManagerAssignmentRead,
    MyUnitRead,
    TagCreate,
    TagRead,
    UnitCreate,
    UnitRead,
    UnitUpdate,
)

__all__ = [
    "AssignmentCreate",
    "AssignmentRead",
    "BillCreate",
    "BillRead",
    "BuildingCreate",
    "BuildingRead",
    "BuildingUpdate",
    "CommentCreate",
    "CommentRead",
    "CommunityCreate",
    "CommunityRead",
    "CommunityUpdate",
    "EligibleUnitRead",
    "IncidenceCreate",
    "IncidenceRead",
    "IncidenceStatusUpdate",
    "InitiativeCreate",
    "InitiativeOptionCreate",
    "InitiativeOptionRead",
    "InitiativeRead",
    "InitiativeScope",
    "ManagerAssignmentCreate",
    "ManagerAssignmentRead",
    "MyUnitRead",
    "TagCreate",
    "TagRead",
    "Token",
    "UnitCreate",
    "UnitRead",
    "UnitUpdate",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "VoteCast",
    "VoteRead",
    "VoteResult",
    "VoteTally",
]
