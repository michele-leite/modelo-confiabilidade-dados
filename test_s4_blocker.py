import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from data_trust_engine import DataTrustEngine, load_yaml, result_to_dict

config = load_yaml(ROOT / "config" / "model_config.yaml")

# Usa as evidências de uma execução de controle já concluída.
runs_dir = ROOT / "runs"
run_dirs = sorted(
    [p for p in runs_dir.iterdir() if p.is_dir()],
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

control_dir = next(
    p for p in run_dirs if (p / "evidence.json").exists()
)

payload = json.loads(
    (control_dir / "evidence.json").read_text(encoding="utf-8")
)

# Cenário artificial: DQ.03 falha e é marcado como bloqueador.
for evidence in payload["evidence"]:
    if evidence["criterion_id"] == "DQ.03":
        evidence["value"] = 0.0
        evidence["rule"] = {
            "type": "threshold",
            "operator": ">=",
            "threshold": 0.999,
            "blocker": True,
        }
        evidence["source"] = "S4-B: evidencia controlada"
        evidence["note"] = (
            "Falha artificial para testar o mecanismo de bloqueio; "
            "não representa uma alteração no dataset Olist."
        )
        break
else:
    raise RuntimeError("Critério DQ.03 não encontrado.")

result = DataTrustEngine(config).evaluate(payload)
output = result_to_dict(result)

output_path = ROOT / "s4_b_test_result.json"
output_path.write_text(
    json.dumps(output, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("Resultado S4-B")
print("Trust score:", output["trust_score"])
print("Coverage score:", output["coverage_score"])
print("Decisão:", output["decision_status"])
print("Classificação:", output["classification"])
print("Bloqueadores:", output["blockers"])
print("Arquivo:", output_path)