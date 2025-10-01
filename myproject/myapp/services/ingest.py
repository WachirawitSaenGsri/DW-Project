import decimal
from datetime import datetime
import pandas as pd
from django.db import transaction
from ..models import Customer, MenuItem, Order, OrderItem
from .ch_client import get_client

REQUIRED_COLS = [
    "order_id","order_ts","sku","menu_name","category",
    "qty","unit_price","discount","customer_id","customer_name","channel"
]

def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV columns missing: {missing}")

def _ensure_channel_column(ch):
    """เพิ่มคอลัมน์ channel ใน ClickHouse ถ้าไม่มีก่อนหน้า"""
    try:
        cols = ch.query_df("DESCRIBE TABLE analytics.fact_sales")['name'].tolist()
    except Exception:
        cols = []
    if 'channel' not in cols:
        try:
            ch.command("ALTER TABLE analytics.fact_sales ADD COLUMN IF NOT EXISTS channel LowCardinality(String) DEFAULT ''")
        except Exception:
            pass

def _parse_ts(val) -> datetime:
    """
    แปลง timestamp จาก CSV ให้เป็น datetime แบบ naive ที่อิง UTC เดิม
    - ถ้าใน CSV มี timezone ติดมา เช่น +07:00 จะถูกแปลงเป็น UTC แล้วตัด tzinfo ออก
      (กันปัญหาที่ไดร์เวอร์/ฐานมองต่าง timezone)
    - ถ้าไม่มี timezone ก็ปล่อยเป็นตามที่ระบุ (ถือว่าเวลา local)
    """
    ts = pd.to_datetime(val, errors='coerce', utc=False)
    if pd.isna(ts):
        raise ValueError(f"Invalid order_ts: {val}")

    # ถ้าเป็น tz-aware → แปลงเป็น UTC แล้วทำให้เป็น naive
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)

    # pandas.Timestamp -> python datetime
    return ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts

@transaction.atomic
def load_csv_to_mysql_and_clickhouse(df: pd.DataFrame):
    validate_columns(df)
    ch = get_client()
    _ensure_channel_column(ch)

    # --- MySQL upsert ---
    for _, r in df.iterrows():
        menu, _ = MenuItem.objects.get_or_create(
            sku=str(r['sku']),
            defaults={
                'name': r.get('menu_name',''),
                'category': r.get('category',''),
                'price': decimal.Decimal(str(r.get('unit_price',0)))
            }
        )
        # update meta ถ้าเปลี่ยนชื่อ/หมวด
        updates = {}
        if r.get('menu_name') and menu.name != r.get('menu_name'):
            updates['name'] = r.get('menu_name')
        if r.get('category') and menu.category != r.get('category'):
            updates['category'] = r.get('category')
        if updates:
            for k,v in updates.items():
                setattr(menu, k, v)
            menu.save(update_fields=list(updates.keys()))

        cust = None
        if pd.notna(r.get('customer_id')):
            cust, _ = Customer.objects.get_or_create(
                customer_id=str(r['customer_id']),
                defaults={'name': r.get('customer_name','')}
            )

        order, _ = Order.objects.get_or_create(
            order_id=str(r['order_id']),
            defaults={
                'order_ts': _parse_ts(r['order_ts']),
                'channel': r.get('channel','') or '',
                'customer': cust
            }
        )

        OrderItem.objects.create(
            order=order,
            menu_item=menu,
            qty=int(r['qty']),
            unit_price=decimal.Decimal(str(r['unit_price'])),
            discount=decimal.Decimal(str(r.get('discount',0)))
        )

    # --- ClickHouse bulk insert ---
    rows = []
    for _, r in df.iterrows():
        qty = int(r['qty'])
        unit_price = decimal.Decimal(str(r['unit_price']))
        discount = decimal.Decimal(str(r.get('discount',0)))
        gross = unit_price * qty
        net = gross - discount
        rows.append([
            str(r['order_id']),
            _parse_ts(r['order_ts']),
            str(r['sku']),
            qty,
            float(gross),
            float(discount),
            float(net),
            str(r.get('channel','') or ''),
        ])
    ch.insert(
        'analytics.fact_sales',
        rows,
        column_names=[
            'order_id','order_ts','sku','qty',
            'gross_amount','discount','net_amount','channel'
        ]
    )
