CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.dim_menu (
  sku String,
  name String,
  category String
) ENGINE = MergeTree ORDER BY sku;

CREATE TABLE IF NOT EXISTS analytics.fact_sales (
  order_id String,
  order_ts DateTime,
  sku String,
  qty Int32,
  gross_amount Decimal(18,2),
  discount Decimal(18,2),
  net_amount Decimal(18,2)
) ENGINE = MergeTree
ORDER BY (order_ts, sku)
PARTITION BY toYYYYMM(order_ts);