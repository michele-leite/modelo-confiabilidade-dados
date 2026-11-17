import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_trust_engine import DataTrustEngine, load_yaml, result_to_dict

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    config = load_yaml(ROOT / "config" / "model_config.yaml")
    payload = json.loads((run_dir / "evidence.json").read_text(encoding="utf-8"))
    result = DataTrustEngine(config).evaluate(payload)
    output = result_to_dict(result)
    path = run_dir / "data_trust_result.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = output["explanation"]["summary"]
    print("Resultado Data Trust")
    print(f"Trust score: {summary['trust_score']}")
    print(f"Coverage score: {summary['coverage_score']}")
    print(f"Classificação: {summary['classification']}")
    print(f"Decisão: {summary['decision_status']}")
    print(f"Resultado salvo em: {path}")

if __name__ == "__main__":
    main()
