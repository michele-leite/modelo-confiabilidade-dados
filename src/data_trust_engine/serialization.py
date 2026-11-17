from dataclasses import asdict
from typing import Any, Dict
from .models import EvaluationResult

def result_to_dict(result: EvaluationResult) -> Dict[str, Any]:
    return asdict(result)
