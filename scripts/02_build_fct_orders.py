import argparse
from pathlib import Path
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--raw-dir", default="data/raw")
    args = parser.parse_args()
    raw, run_dir = Path(args.raw_dir).resolve(), Path(args.run_dir).resolve()
    out_dir = run_dir / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    orders = pd.read_csv(raw / "olist_orders_dataset.csv", low_memory=False)
    customers = pd.read_csv(raw / "olist_customers_dataset.csv", low_memory=False)
    items = pd.read_csv(raw / "olist_order_items_dataset.csv", low_memory=False)
    payments = pd.read_csv(raw / "olist_order_payments_dataset.csv", low_memory=False)
    reviews = pd.read_csv(raw / "olist_order_reviews_dataset.csv", low_memory=False)

    for col in ["order_purchase_timestamp", "order_approved_at",
                "order_delivered_carrier_date", "order_delivered_customer_date",
                "order_estimated_delivery_date"]:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    items_agg = items.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        item_price_sum=("price", "sum"),
        freight_sum=("freight_value", "sum"),
        seller_count=("seller_id", "nunique"),
        product_count=("product_id", "nunique"),
    )
    payments_agg = payments.groupby("order_id", as_index=False).agg(
        payment_total=("payment_value", "sum"),
        payment_record_count=("payment_value", "size"),
        payment_type_count=("payment_type", "nunique"),
    )
    reviews_agg = reviews.groupby("order_id", as_index=False).agg(
        review_count=("review_id", "nunique"),
        review_score_avg=("review_score", "mean"),
    )

    if not customers["customer_id"].is_unique:
        raise ValueError("customers.customer_id não é único; JOIN interrompido.")

    fct = orders.merge(
        customers[["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                   "customer_city", "customer_state"]],
        on="customer_id", how="left", validate="many_to_one"
    )
    fct = fct.merge(items_agg, on="order_id", how="left", validate="one_to_one")
    fct = fct.merge(payments_agg, on="order_id", how="left", validate="one_to_one")
    fct = fct.merge(reviews_agg, on="order_id", how="left", validate="one_to_one")

    if len(fct) != len(orders):
        raise AssertionError(f"Granularidade alterada: orders={len(orders)}, fct={len(fct)}")
    if not fct["order_id"].is_unique:
        raise AssertionError("order_id não é único na fct_orders.")

    fct["has_items"] = fct["item_count"].notna()
    fct["has_payments"] = fct["payment_record_count"].notna()
    fct["has_reviews"] = fct["review_count"].notna()
    path = out_dir / "fct_orders.csv"
    fct.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"fct_orders gerada: {path}")
    print(f"Pedidos na origem: {len(orders):,}; fato: {len(fct):,}; IDs únicos: {fct['order_id'].nunique():,}")

if __name__ == "__main__":
    main()
