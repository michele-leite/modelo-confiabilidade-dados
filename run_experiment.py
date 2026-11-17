import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
RUNS = ROOT / "runs"
SCRIPTS = ROOT / "scripts"
EXPECTED_INPUTS = [
    "olist_orders_dataset.csv", "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv", "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv", "olist_sellers_dataset.csv",
    "olist_products_dataset.csv", "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git_value(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

def write_manifest(path, manifest):
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    missing = [name for name in EXPECTED_INPUTS if not (RAW / name).exists()]
    if missing:
        print("CSV(s) ausente(s) em data/raw/:")
        for name in missing:
            print(f" - {name}")
        print("Consulte data/raw/README.md.")
        return 2

    RUNS.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest_path, log_path = run_dir / "run_manifest.json", run_dir / "execution.log"

    inputs = [{
        "name": name, "sha256": sha256_file(RAW / name),
        "size_bytes": (RAW / name).stat().st_size
    } for name in EXPECTED_INPUTS]
    code_paths = sorted(
        list((ROOT / "scripts").glob("*.py"))
        + list((ROOT / "src" / "data_trust_engine").glob("*.py"))
        + list((ROOT / "config").glob("*.yaml"))
        + [ROOT / "run_experiment.py"]
    )
    code_hashes = {
        str(path.relative_to(ROOT)): sha256_file(path)
        for path in code_paths if path.exists()
    }
    manifest = {
        "run_id": run_id, "experiment_id": "sprint4-olist-baseline",
        "started_at": now_utc(), "finished_at": None, "status": "RUNNING",
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_worktree_dirty": bool(git_value("status", "--porcelain")),
        "python_version": sys.version, "inputs": inputs,
        "code_hashes": code_hashes,
        "stages": [], "outputs": [], "error_message": None,
    }
    write_manifest(manifest_path, manifest)
    steps = ["01_audit_olist.py", "02_build_fct_orders.py", "03_calculate_metrics.py",
             "04_build_evidence.py", "05_run_engine.py"]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        with log_path.open("w", encoding="utf-8") as log:
            for script in steps:
                stage = {"name": script, "status": "RUNNING", "started_at": now_utc()}
                manifest["stages"].append(stage)
                write_manifest(manifest_path, manifest)
                start = time.perf_counter()
                try:
                    result = subprocess.run(
                        [sys.executable, str(SCRIPTS / script), "--run-dir", str(run_dir)],
                        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
                    )
                    stage["exit_code"] = result.returncode
                    stage["duration_seconds"] = round(time.perf_counter() - start, 3)
                    stage["finished_at"] = now_utc()
                    stage["status"] = "SUCCESS" if result.returncode == 0 else "FAILED"
                    if result.returncode != 0:
                        raise RuntimeError(f"Etapa {script} terminou com código {result.returncode}; consulte {log_path}.")
                except Exception as exc:
                    if stage["status"] == "RUNNING":
                        stage["status"] = "FAILED"
                        stage["duration_seconds"] = round(time.perf_counter() - start, 3)
                        stage["finished_at"] = now_utc()
                        stage["error_message"] = str(exc)
                    raise
                finally:
                    write_manifest(manifest_path, manifest)

        outputs = []
        for path in sorted(run_dir.rglob("*")):
            if not path.is_file() or path in {manifest_path, log_path}:
                continue
            outputs.append({"path": str(path.relative_to(run_dir)),
                            "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
        manifest["outputs"] = outputs
        manifest["status"] = "SUCCESS"
    except Exception as exc:
        manifest["status"] = "FAILED"
        manifest["error_message"] = str(exc)
    finally:
        manifest["finished_at"] = now_utc()
        manifest["duration_seconds"] = round(
            (datetime.fromisoformat(manifest["finished_at"]) -
             datetime.fromisoformat(manifest["started_at"])).total_seconds(), 3)
        write_manifest(manifest_path, manifest)

    print(f"Run ID: {run_id}")
    print(f"Status: {manifest['status']}")
    print(f"Manifesto: {manifest_path}")
    print(f"Log: {log_path}")
    if manifest["status"] != "SUCCESS":
        print(manifest["error_message"])
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
