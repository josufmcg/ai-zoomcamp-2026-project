"""SQLAlchemy models for the EFINGES domain.

The models are grouped by bounded area to keep each module readable:

* :mod:`app.models.property` - Community, Building, Unit, Tag, and the
  manager-to-community assignment (backlog tasks 5 and 8).
* :mod:`app.models.identity` - User, UserRole, UnitAssignment, OwnershipType
  (backlog tasks 6 and 7).
* :mod:`app.models.billing` - Bill, BillStatus, and the computed display status
  (backlog task 10).
* :mod:`app.models.maintenance` - Incidence, Comment, and the lifecycle table
  (backlog task 11).
* :mod:`app.models.governance` - Initiative, InitiativeOption, Vote (task 12).

Every name is re-exported here, so ``from app.models import Bill`` keeps
working exactly as it did when the models lived in a single file. Importing
this package also registers every table on ``Base.metadata``, which is what
Alembic autogeneration and ``create_all`` rely on.
"""

from __future__ import annotations

from app.models.billing import Bill, BillDisplayStatus, BillStatus
from app.models.columns import enum_column
from app.models.governance import Initiative, InitiativeOption, Vote
from app.models.identity import OwnershipType, UnitAssignment, User, UserRole
from app.models.maintenance import (
    INCIDENCE_TRANSITIONS,
    Comment,
    Incidence,
    IncidenceStatus,
)
from app.models.property import (
    Building,
    Community,
    ManagerAssignment,
    Tag,
    Unit,
    UnitType,
    building_tags,
    unit_tags,
)

__all__ = [
    "INCIDENCE_TRANSITIONS",
    "Bill",
    "BillDisplayStatus",
    "BillStatus",
    "Building",
    "Comment",
    "Community",
    "Incidence",
    "IncidenceStatus",
    "Initiative",
    "InitiativeOption",
    "ManagerAssignment",
    "OwnershipType",
    "Tag",
    "Unit",
    "UnitAssignment",
    "UnitType",
    "User",
    "UserRole",
    "Vote",
    "building_tags",
    "enum_column",
    "unit_tags",
]
