from typing import Any, Dict, List
from .models import (
    CriterionResult, DimensionResult, EvaluationResult,
    PASS, FAIL, UNKNOWN
)
from .rules import evaluate_rule
from .config import merge_overrides

class DataTrustEngine:
    def __init__(self, model_config: Dict[str, Any]):
        self.base_config = model_config

    def evaluate(self, payload: Dict[str, Any]) -> EvaluationResult:
        config = merge_overrides(self.base_config, payload)
        ev_cfg = config["evaluation"]

        asset_id = payload["asset"]["asset_id"]
        context_id = payload["context"]["context_id"]
        criticality = payload["context"]["criticality"]

        evidence_by_id = {
            item["criterion_id"]: item
            for item in payload.get("evidence", [])
        }

        dimension_results: Dict[str, DimensionResult] = {}
        blocker_fails: List[str] = []
        fail_criteria: List[str] = []
        unknown_criteria: List[str] = []

        min_dim_cov = ev_cfg["min_dimension_coverage"]

        for dim_id, dim_cfg in ev_cfg["dimensions"].items():
            criteria_results: List[CriterionResult] = []
            known_scores: List[float] = []

            for criterion in dim_cfg["criteria"]:
                cid = criterion["id"]
                evidence = evidence_by_id.get(cid)

                if evidence is None:
                    state, explanation = UNKNOWN, "Nenhuma evidência fornecida para o critério."
                    blocker = False
                    raw_value = None
                    source = None
                else:
                    rule = evidence.get("rule")
                    if not rule:
                        state, explanation = UNKNOWN, "Regra não fornecida; critério não pode ser avaliado."
                        blocker = False
                    else:
                        state, explanation = evaluate_rule(evidence.get("value"), rule)
                        blocker = bool(rule.get("blocker", False))
                    raw_value = evidence.get("value")
                    source = evidence.get("source")

                score = 1.0 if state == PASS else 0.0 if state == FAIL else None

                if score is not None:
                    known_scores.append(score)
                if state == FAIL:
                    fail_criteria.append(cid)
                    if blocker:
                        blocker_fails.append(cid)
                elif state == UNKNOWN:
                    unknown_criteria.append(cid)

                criteria_results.append(
                    CriterionResult(
                        criterion_id=cid,
                        state=state,
                        score=score,
                        blocker=blocker,
                        raw_value=raw_value,
                        source=source,
                        explanation=explanation,
                    )
                )

            total = len(criteria_results)
            known = len(known_scores)
            coverage = known / total if total else 0.0
            score = sum(known_scores) / known if known else None
            status = (
                "OBSERVABLE"
                if coverage >= min_dim_cov
                else "INSUFFICIENTLY_EVIDENCED"
            )

            dimension_results[dim_id] = DimensionResult(
                dimension_id=dim_id,
                score=score,
                coverage=coverage,
                status=status,
                criteria=criteria_results,
            )

        # Score e cobertura globais, ponderados pelas cinco dimensões avaliativas.
        trust_score = 0.0
        coverage_score = 0.0
        for dim_id, dim_cfg in ev_cfg["dimensions"].items():
            weight = dim_cfg["weight"]
            dr = dimension_results[dim_id]
            # Dimensão sem qualquer critério conhecido contribui 0 ao score observado,
            # mas sua ausência fica refletida principalmente na cobertura.
            trust_score += weight * (dr.score if dr.score is not None else 0.0)
            coverage_score += weight * dr.coverage

        profile = ev_cfg["criticality_profiles"][criticality]
        required_trust = profile["min_trust_score"]
        required_coverage = profile["min_coverage_score"]

        all_dimensions_observable = all(
            d.status == "OBSERVABLE" for d in dimension_results.values()
        )
        has_blocker = bool(blocker_fails)

        eligible = (
            not has_blocker
            and trust_score >= required_trust
            and coverage_score >= required_coverage
            and all_dimensions_observable
        )

        if has_blocker or trust_score < 0.60:
            classification = "C1"
        elif (
            trust_score < required_trust
            or coverage_score < required_coverage
            or not all_dimensions_observable
        ):
            classification = "C2"
        elif (
            trust_score >= 0.90
            and coverage_score >= 0.90
            and all_dimensions_observable
            and not has_blocker
        ):
            classification = "C4"
        else:
            classification = "C3"

        decision_status = "ELIGIBLE" if eligible else "NOT_ELIGIBLE"

        explanation = {
            "summary": {
                "trust_score": round(trust_score, 4),
                "coverage_score": round(coverage_score, 4),
                "criticality": criticality,
                "required_trust_score": required_trust,
                "required_coverage_score": required_coverage,
                "decision_status": decision_status,
                "classification": classification,
            },
            "blockers": blocker_fails,
            "fail_criteria": fail_criteria,
            "unknown_criteria": unknown_criteria,
            "insufficient_dimensions": [
                dim_id for dim_id, dr in dimension_results.items()
                if dr.status != "OBSERVABLE"
            ],
        }

        return EvaluationResult(
            asset_id=asset_id,
            context_id=context_id,
            criticality=criticality,
            trust_score=round(trust_score, 4),
            coverage_score=round(coverage_score, 4),
            required_trust_score=required_trust,
            required_coverage_score=required_coverage,
            decision_status=decision_status,
            classification=classification,
            dimension_results=dimension_results,
            blockers=blocker_fails,
            fail_criteria=fail_criteria,
            unknown_criteria=unknown_criteria,
            explanation=explanation,
        )
