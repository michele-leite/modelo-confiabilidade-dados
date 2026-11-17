from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_required_scripts_exist():
    expected = ["run_experiment.py", "scripts/01_audit_olist.py",
                "scripts/02_build_fct_orders.py", "scripts/03_calculate_metrics.py",
                "scripts/04_build_evidence.py", "scripts/05_run_engine.py"]
    assert all((ROOT / p).exists() for p in expected)
