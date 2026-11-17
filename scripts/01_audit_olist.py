import argparse
import json
from pathlib import Path
import pandas as pd

EXPECTED_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}
PRIMARY_KEYS = {
    "orders": ["order_id"],
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "category_translation": ["product_category_name"],
}
FOREIGN_KEYS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("order_payments", "order_id", "orders", "order_id"),
    ("order_reviews", "order_id", "orders", "order_id"),
]

def load_tables(raw_dir):
    tables, missing = {}, []
    for name, filename in EXPECTED_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            missing.append(filename)
        else:
            tables[name] = pd.read_csv(path, low_memory=False)
    if missing:
        raise FileNotFoundError(f"Arquivos Olist ausentes em {raw_dir}: {', '.join(missing)}")
    return tables

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--raw-dir", default="data/raw")
    args = parser.parse_args()
    run_dir, raw_dir = Path(args.run_dir).resolve(), Path(args.raw_dir).resolve()
    out = run_dir / "audit"
    out.mkdir(parents=True, exist_ok=True)
    tables = load_tables(raw_dir)

    summary_rows, missing_rows, duplicate_rows, fk_rows, anomalies = [], [], [], [], []
    for name, df in tables.items():
        summary_rows.append({
            "table_name": name, "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "duplicate_full_rows": int(df.duplicated().sum()),
            "memory_bytes": int(df.memory_usage(deep=True).sum()),
        })
        for col in df.columns:
            count = int(df[col].isna().sum())
            missing_rows.append({
                "table_name": name, "column_name": col, "null_count": count,
                "null_pct": round(count / len(df), 6) if len(df) else None,
                "dtype": str(df[col].dtype),
            })
        for key in PRIMARY_KEYS.get(name, []):
            duplicate_rows.append({
                "table_name": name, "key_columns": key, "row_count": int(len(df)),
                "distinct_key_count": int(df[key].nunique(dropna=False)),
                "duplicate_key_rows": int(df.duplicated(key, keep=False).sum()),
                "null_key_rows": int(df[key].isna().sum()),
            })

    for child_name, child_key, parent_name, parent_key in FOREIGN_KEYS:
        child, parent = tables[child_name], tables[parent_name]
        parent_values = set(parent[parent_key].dropna().astype(str))
        nonnull = child[child_key].dropna().astype(str)
        orphan_mask = ~nonnull.isin(parent_values)
        fk_rows.append({
            "child_table": child_name, "child_column": child_key,
            "parent_table": parent_name, "parent_column": parent_key,
            "nonnull_child_values": int(len(nonnull)),
            "orphan_count": int(orphan_mask.sum()),
            "orphan_pct": round(float(orphan_mask.mean()), 6) if len(nonnull) else None,
        })

    orders = tables["orders"].copy()
    date_cols = ["order_purchase_timestamp", "order_approved_at",
                 "order_delivered_carrier_date", "order_delivered_customer_date",
                 "order_estimated_delivery_date"]
    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")
    checks = [
        ("delivered_before_carrier",
         orders["order_delivered_customer_date"].notna()
         & orders["order_delivered_carrier_date"].notna()
         & (orders["order_delivered_customer_date"] < orders["order_delivered_carrier_date"]),
         "Entrega ao cliente anterior à entrega à transportadora; investigar sem corrigir automaticamente."),
        ("delivered_before_purchase",
         orders["order_delivered_customer_date"].notna()
         & orders["order_purchase_timestamp"].notna()
         & (orders["order_delivered_customer_date"] < orders["order_purchase_timestamp"]),
         "Entrega ao cliente anterior à compra."),
    ]
    for name, mask, description in checks:
        anomalies.append({"anomaly": name, "count": int(mask.sum()), "description": description})
    valid_statuses = {"created", "approved", "invoiced", "processing", "shipped", "delivered", "canceled", "unavailable"}
    anomalies.append({
        "anomaly": "unknown_order_status",
        "count": int((~tables["orders"]["order_status"].isin(valid_statuses)).sum()),
        "description": "Status fora do domínio conhecido para este experimento."
    })

    pd.DataFrame(summary_rows).to_csv(out / "audit_summary.csv", index=False)
    pd.DataFrame(missing_rows).to_csv(out / "missing_values.csv", index=False)
    pd.DataFrame(duplicate_rows).to_csv(out / "primary_key_audit.csv", index=False)
    pd.DataFrame(fk_rows).to_csv(out / "referential_integrity.csv", index=False)
    pd.DataFrame(anomalies).to_csv(out / "anomalies.csv", index=False)
    (out / "audit_summary.json").write_text(
        json.dumps({"tables": summary_rows, "foreign_keys": fk_rows,
                    "anomalies": anomalies, "all_expected_files_present": True},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Auditoria concluída: {out}")
    print(pd.DataFrame(summary_rows)[["table_name", "row_count", "column_count"]].to_string(index=False))

if __name__ == "__main__":
    main()
