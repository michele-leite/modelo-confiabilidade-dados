from copy import deepcopy
from pathlib import Path
from typing import Any, Dict
import yaml

def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def merge_overrides(config: Dict[str, Any], evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica apenas overrides explicitamente suportados pelo contrato.
    """
    cfg = deepcopy(config)
    overrides = evaluation.get("overrides") or {}
    ev = cfg["evaluation"]

    if "min_dimension_coverage" in overrides:
        ev["min_dimension_coverage"] = overrides["min_dimension_coverage"]

    for dim_id, weight in (overrides.get("dimension_weights") or {}).items():
        if dim_id not in ev["dimensions"]:
            raise ValueError(f"Dimensão inválida em override: {dim_id}")
        ev["dimensions"][dim_id]["weight"] = weight

    for crit, vals in (overrides.get("criticality_thresholds") or {}).items():
        if crit not in ev["criticality_profiles"]:
            raise ValueError(f"Criticidade inválida em override: {crit}")
        ev["criticality_profiles"][crit].update(vals)

    total_weight = sum(d["weight"] for d in ev["dimensions"].values())
    if abs(total_weight - 1.0) > 1e-9:
        raise ValueError(f"Pesos das dimensões devem somar 1.0; soma atual={total_weight}")

    return cfg
