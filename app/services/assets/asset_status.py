from enum import Enum

class AssetStatus(str, Enum):
    PENDING = "pending"
    GENERATED = "generated"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DELETED = "deleted"
