"""Quality services namespace.

Consolidates the five quality / validation / repair services into one
sub-package so they're easier to locate and reason about. Re-exports the
original public classes unchanged for backwards compatibility.
"""

from app.services.quality.prompt import PromptQualityService
from app.services.quality.readiness import ProductionReadinessService
from app.services.quality.repair import RepairSuggestionService
from app.services.quality.review import ReviewQualityService
from app.services.quality.validation import ProjectValidationService

__all__ = [
    "PromptQualityService",
    "ProductionReadinessService",
    "RepairSuggestionService",
    "ReviewQualityService",
    "ProjectValidationService",
]
