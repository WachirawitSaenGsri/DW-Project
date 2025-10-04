# DW-Project

รันตามนี้

docker compose build

docker compose up -d

docker compose exec clickhouse clickhouse-client -q "CREATE USER app_user IDENTIFIED WITH plaintext_password BY 'StrongP@ss!' HOST ANY;"

docker compose exec clickhouse clickhouse-client -q "GRANT SELECT, INSERT, CREATE, ALTER ON analytics.* TO app_user;"

docker compose exec clickhouse clickhouse-client -q "ALTER USER app_user IDENTIFIED WITH plaintext_password BY 'StrongP@ss!' HOST ANY;"

docker compose exec clickhouse clickhouse-client -q "GRANT SELECT, INSERT, CREATE, ALTER ON analytics.* TO app_user;"

docker compose exec clickhouse clickhouse-client -q "GRANT SELECT, INSERT ON analytics.* TO app_user"

docker compose exec clickhouse clickhouse-client -q "GRANT TRUNCATE ON analytics.* TO app_user"

docker compose exec clickhouse clickhouse-client -q "GRANT ALTER ON analytics.* TO app_user"

docker compose exec web bash -lc "python manage.py makemigrations"

docker compose exec web bash -lc "python manage.py migrate"

docker compose exec web bash -lc "python manage.py createsuperuser" 

docker compose exec clickhouse clickhouse-client -q "
CREATE TABLE IF NOT EXISTS analytics.fact_sales
(
  order_id String,
  order_ts DateTime,
  sku String,
  qty Int32,
  gross_amount Decimal(12,2),
  discount Decimal(12,2),
  net_amount Decimal(12,2)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(order_ts)
ORDER BY (order_ts, sku)
SETTINGS index_granularity = 8192;
"

docker compose exec clickhouse clickhouse-client -q "
ALTER TABLE analytics.fact_sales
ADD COLUMN IF NOT EXISTS channel LowCardinality(String) DEFAULT '';
"

ไฟล์ข้อมูลทดลองอยู่ในไฟล์ scripts 
