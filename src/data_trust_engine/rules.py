from typing import Any, Dict, Tuple
from .models import PASS, FAIL, UNKNOWN

def _compare(value: Any, operator: str, target: Any) -> bool:
    if operator == ">=":
        return value >= target
    if operator == ">":
        return value > target
    if operator == "<=":
        return value <= target
    if operator == "<":
        return value < target
    if operator == "==":
        return value == target
    if operator == "!=":
        return value != target
    if operator == "in":
        return value in target
    raise ValueError(f"Operador não suportado: {operator}")

def evaluate_rule(value: Any, rule: Dict[str, Any]) -> Tuple[str, str]:
    """
    Retorna (estado, explicação).
    UNKNOWN é usado quando a evidência é ausente/insuficiente.
    """
    if value is None:
        return UNKNOWN, "Evidência ausente ou insuficiente."

    rule_type = rule["type"]

    if rule_type == "threshold":
        operator = rule["operator"]
        threshold = rule["threshold"]
        passed = _compare(value, operator, threshold)
        msg = f"Valor observado={value}; regra: valor {operator} {threshold}."
        return (PASS if passed else FAIL), msg

    if rule_type == "boolean":
        expected = rule.get("expected", True)
        passed = value is expected or value == expected
        msg = f"Valor observado={value}; esperado={expected}."
        return (PASS if passed else FAIL), msg

    if rule_type == "presence":
        passed = value not in (None, "", [], {})
        msg = "Evidência presente." if passed else "Evidência ausente."
        return (PASS if passed else FAIL), msg

    if rule_type == "categorical":
        allowed = rule.get("allowed_values", [])
        passed = value in allowed
        msg = f"Valor observado={value}; valores permitidos={allowed}."
        return (PASS if passed else FAIL), msg

    raise ValueError(f"Tipo de regra não suportado: {rule_type}")
