import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
import yaml

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def normalize_manifest_path(path):
    return str(path).replace("\\", "/").lstrip("./")

def ev(cid, value, rule, source, note):
    return {"criterion_id": cid, "value": value, "rule": rule, "source": source, "note": note}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    root = Path(__file__).resolve().parents[1]
    runs_root = root / "runs"

    metrics = read_json(run_dir / "metrics.json")
    audit = read_json(run_dir / "audit" / "audit_summary.json")
    current_manifest = read_json(run_dir / "run_manifest.json")
    catalog = yaml.safe_load((root / "config" / "asset_catalog.yaml").read_text(encoding="utf-8"))
    use_case = yaml.safe_load((root / "config" / "use_case.yaml").read_text(encoding="utf-8"))

    # Thresholds are experimental parameters and must be justified before the official run.
    completeness_min, consistency_min, validity_min = 0.98, 0.995, 0.999

    prior_manifests = []
    for manifest_path in runs_root.glob("*/run_manifest.json"):
        if manifest_path.resolve() == (run_dir / "run_manifest.json").resolve():
            continue
        try:
            prior = read_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        if prior.get("status") in {"SUCCESS", "FAILED"}:
            prior["_manifest_path"] = str(manifest_path)
            prior["_run_dir"] = str(manifest_path.parent)
            prior_manifests.append(prior)

    # REL.02: observed completion rate of previous experimental pipeline attempts.
    # It is not production/platform availability. First run has no historical evidence.
    completed_prior = prior_manifests
    availability_rate = (
        sum(1 for item in completed_prior if item.get("status") == "SUCCESS") / len(completed_prior)
        if completed_prior else None
    )

    # REL.03: reproducibility of the fact and metrics across comparable successful runs.
    current_inputs = {x["name"]: x["sha256"] for x in current_manifest.get("inputs", [])}
    current_code = current_manifest.get("code_hashes", {})
    current_fact_hash = sha256_file(run_dir / "data" / "fct_orders.csv")
    current_metrics_hash = sha256_file(run_dir / "metrics.json")
    comparable = []
    for prior in prior_manifests:
        if prior.get("status") != "SUCCESS":
            continue
        prior_inputs = {x["name"]: x["sha256"] for x in prior.get("inputs", [])}
        if prior_inputs != current_inputs or prior.get("code_hashes", {}) != current_code:
            continue
        prior_outputs = {normalize_manifest_path(x.get("path", "")): x.get("sha256") for x in prior.get("outputs", [])}

        prior_fact = prior_outputs.get("data/fct_orders.csv")
        prior_metrics = prior_outputs.get("metrics.json")
        if prior_fact and prior_metrics:
            comparable.append((prior_fact, prior_metrics))
    stability_value = (
        all(fact_hash == current_fact_hash and metrics_hash == current_metrics_hash
            for fact_hash, metrics_hash in comparable)
        if comparable else None
    )

    fact = pd.read_csv(run_dir / "data" / "fct_orders.csv", low_memory=False)
    required = use_case["context"]["fit_for_purpose"]["required_columns"]
    fit = bool(all(c in fact.columns for c in required) and fact["order_id"].is_unique
               and len(fact) == metrics["row_count"])

    owner_declared = bool(catalog["asset"]["owner"].get("name"))
    definition = bool(catalog["asset"].get("definition_documented"))
    steward_declared = bool(catalog["asset"]["steward"].get("name"))
    purpose = bool(catalog["asset"].get("intended_use_documented"))
    tolerance = bool(catalog["asset"].get("tolerance_documented"))

    evidence = [
        ev("DQ.01", metrics["completeness"]["value"], {"type":"threshold","operator":">=","threshold":completeness_min},
           "metrics.json:completeness.value", "Completude conforme regras condicionais por status."),
        ev("DQ.02", metrics["consistency"]["value"], {"type":"threshold","operator":">=","threshold":consistency_min},
           "metrics.json:consistency.value", "Consistência das comparações temporais aplicáveis."),
        ev("DQ.03", metrics["validity"]["value"], {"type":"threshold","operator":">=","threshold":validity_min},
           "metrics.json:validity.value", "Validade de status, valores monetários e notas."),
        ev("REL.01", None, {"type":"presence"}, "not_available_in_source",
           "UNKNOWN: os CSVs não contêm timestamp confiável de ingestão/publicação para medir freshness operacional."),
        ev("REL.02", availability_rate, {"type":"threshold","operator":">=","threshold":0.95},
           "runs/*/run_manifest.json:status",
           "Taxa de sucesso observada nas execuções experimentais anteriores concluídas; não é disponibilidade da plataforma Olist. UNKNOWN antes de existir histórico."),
        ev("REL.03", stability_value, {"type":"boolean","expected":True},
           "comparação de hashes de fct_orders.csv e metrics.json em execuções com mesmos inputs e hashes de código",
           "UNKNOWN sem execução anterior comparável; PASS se os hashes forem idênticos, FAIL se divergirem."),
        ev("GOV.01", owner_declared, {"type":"boolean","expected":True}, "config/asset_catalog.yaml:asset.owner",
           "Responsável declarado no catálogo experimental, não owner corporativo verificado."),
        ev("GOV.02", definition, {"type":"boolean","expected":True}, "config/asset_catalog.yaml:asset.definition_documented",
           "Definição do ativo documentada no catálogo experimental."),
        ev("GOV.03", steward_declared, {"type":"boolean","expected":True}, "config/asset_catalog.yaml:asset.steward",
           "Steward declarado no catálogo experimental, não stewardship corporativo verificado."),
        ev("PROV.01", bool(audit.get("all_expected_files_present")), {"type":"boolean","expected":True},
           "audit/audit_summary.json", "Os arquivos de origem esperados foram localizados e auditados."),
        ev("PROV.02", bool(current_manifest.get("stages")), {"type":"boolean","expected":True},
           "run_manifest.json:stages", "O manifesto registra as etapas do pipeline."),
        ev("PROV.03", (run_dir / "data" / "fct_orders.csv").exists(), {"type":"boolean","expected":True},
           "run_manifest.json + data/fct_orders.csv", "A fato foi produzida; o hash será registrado no manifesto final."),
        ev("CTX.01", purpose, {"type":"boolean","expected":True}, "config/asset_catalog.yaml:asset.intended_use",
           "Finalidade documentada pelo pesquisador."),
        ev("CTX.02", fit, {"type":"boolean","expected":True}, "fct_orders.csv + config/use_case.yaml",
           "Adequação estrutural: colunas requeridas, granularidade e contagem de linhas."),
        ev("CTX.03", tolerance, {"type":"boolean","expected":True}, "config/asset_catalog.yaml:asset.tolerance_documented",
           "Tolerância documentada; limiares experimentais explícitos."),
    ]
    payload = {
        "asset": {"asset_id": catalog["asset"]["asset_id"]},
        "context": {"context_id": use_case["context"]["context_id"],
                    "criticality": use_case["context"]["criticality"]},
        "evidence": evidence,
    }
    (run_dir / "evidence.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Evidências geradas: {run_dir / 'evidence.json'}")

if __name__ == "__main__":
    main()
