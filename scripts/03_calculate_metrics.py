import argparse
import json
from pathlib import Path
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    fct = pd.read_csv(run_dir / "data" / "fct_orders.csv", low_memory=False)

    core = ["order_id", "customer_id", "order_status", "order_purchase_timestamp"]
    core_complete = fct[core].notna().all(axis=1)
    delivered = fct["order_status"].eq("delivered")
    delivery_cols = ["order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date"]
    delivered_complete = fct[delivery_cols].notna().all(axis=1)
    complete = core_complete & (~delivered | delivered_complete)
    completeness_rate = float(complete.mean()) if len(fct) else None

    purchase = pd.to_datetime(fct["order_purchase_timestamp"], errors="coerce")
    approved = pd.to_datetime(fct["order_approved_at"], errors="coerce")
    carrier = pd.to_datetime(fct["order_delivered_carrier_date"], errors="coerce")
    delivered_at = pd.to_datetime(fct["order_delivered_customer_date"], errors="coerce")
    comparison_results = []
    for left, right in [(purchase, approved), (approved, carrier), (carrier, delivered_at)]:
        applicable = left.notna() & right.notna()
        comparison_results.extend((bool(ok), bool(app)) for ok, app in zip((left <= right).tolist(), applicable.tolist()))
    applicable = [ok for ok, is_applicable in comparison_results if is_applicable]
    consistency_rate = sum(applicable) / len(applicable) if applicable else None

    statuses = {"created", "approved", "invoiced", "processing", "shipped", "delivered", "canceled", "unavailable"}
    checks = pd.DataFrame({
        "status": fct["order_status"].isin(statuses),
        "price": fct["item_price_sum"].isna() | (fct["item_price_sum"] >= 0),
        "freight": fct["freight_sum"].isna() | (fct["freight_sum"] >= 0),
        "payment": fct["payment_total"].isna() | (fct["payment_total"] >= 0),
        "review": fct["review_score_avg"].isna() | fct["review_score_avg"].between(1, 5),
    })
    validity_rate = float(checks.to_numpy().mean()) if len(fct) else None

    metrics = {
        "dataset": "Olist",
        "fact_table": "fct_orders",
        "row_count": int(len(fct)),
        "distinct_order_id": int(fct["order_id"].nunique()),
        "order_id_unique": bool(fct["order_id"].is_unique),
        "completeness": {"value": completeness_rate, "complete_orders": int(complete.sum()),
                         "total_orders": int(len(fct)),
                         "definition": "Campos centrais obrigatórios; pedidos delivered também exigem timestamps de aprovação, transportadora e entrega."},
        "consistency": {"value": consistency_rate,
                        "applicable_timestamp_comparisons": int(len(applicable)),
                        "passed_timestamp_comparisons": int(sum(applicable)),
                        "definition": "Share de comparações temporais aplicáveis que respeitam a ordem esperada."},
        "validity": {"value": validity_rate,
                     "definition": "Share de verificações para domínio de status, valores não negativos e notas entre 1 e 5."},
        "items_missing": int(fct["item_count"].isna().sum()),
        "payments_missing": int(fct["payment_record_count"].isna().sum()),
        "reviews_missing": int(fct["review_count"].isna().sum()),
        "max_items_per_order": int(fct["item_count"].max()) if fct["item_count"].notna().any() else None,
        "max_payment_records_per_order": int(fct["payment_record_count"].max()) if fct["payment_record_count"].notna().any() else None,
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Métricas gravadas: {run_dir / 'metrics.json'}")

if __name__ == "__main__":
    main()
