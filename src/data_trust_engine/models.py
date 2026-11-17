from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"

@dataclass
class CriterionResult:
    criterion_id: str
    state: str
    score: Optional[float]
    blocker: bool
    raw_value: Any = None
    source: Optional[str] = None
    explanation: Optional[str] = None

@dataclass
class DimensionResult:
    dimension_id: str
    score: Optional[float]
    coverage: float
    status: str
    criteria: List[CriterionResult] = field(default_factory=list)

@dataclass
class EvaluationResult:
    asset_id: str
    context_id: str
    criticality: str
    trust_score: float
    coverage_score: float
    required_trust_score: float
    required_coverage_score: float
    decision_status: str
    classification: str
    dimension_results: Dict[str, DimensionResult]
    blockers: List[str]
    fail_criteria: List[str]
    unknown_criteria: List[str]
    explanation: Dict[str, Any]
