from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_trust_engine import DataTrustEngine, load_yaml

def test_engine_can_evaluate_unknown_evidence():
    config = load_yaml(ROOT / "config" / "model_config.yaml")
    payload = {
        "asset": {"asset_id": "test.asset"},
        "context": {"context_id": "test-context", "criticality": "II"},
        "evidence": [{"criterion_id": "DQ.01", "value": None,
                      "rule": {"type": "presence"}, "source": "test"}],
    }
    result = DataTrustEngine(config).evaluate(payload)
    assert result.asset_id == "test.asset"
    assert result.classification in {"C1", "C2", "C3", "C4"}
    assert "DQ.01" in result.unknown_criteria
