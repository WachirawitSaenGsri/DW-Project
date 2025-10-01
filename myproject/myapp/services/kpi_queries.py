from .ch_client import get_client
import pandas as pd
from django.conf import settings

def _fact_has_channel_column(ch) -> bool:
    """ตรวจว่าตาราง analytics.fact_sales มีคอลัมน์ channel หรือไม่"""
    try:
        desc = ch.query("DESCRIBE TABLE analytics.fact_sales")
        cols = [row[0] for row in desc.result_rows]
        return 'channel' in cols
    except Exception:
        return False


def kpi(top_limit=10, start=None, end=None, channel=None):
    """
    คืนค่า:
    - top_df:     sku, total_qty, revenue
    - hour_df:    hr, rev, orders, aov
    - day_df:     d, rev
    - channel_df: channel, rev  (มีเมื่อ fact มีคอลัมน์ channel)
    - day_cum_df: d, rev, cum_rev (สะสม)
    """
    ch = get_client()

    # ใช้ TIME_ZONE จาก Django (เช่น 'Asia/Bangkok')
    TZ = getattr(settings, "TIME_ZONE", "Asia/Bangkok")
    tz_col = f"toTimeZone(order_ts, '{TZ}')"   # ใช้เวลาท้องถิ่นในการกรอง/สรุป

    where = []
    params = {}

    # กรองช่วงเวลาโดยเทียบใน timezone เดียวกัน
    if start:
        where.append(f"{tz_col} >= toDateTime(%(start)s, '{TZ}')")
        params["start"] = str(start) + " 00:00:00"
    if end:
        where.append(f"{tz_col} <  toDateTime(%(end)s, '{TZ}') + INTERVAL 1 DAY")
        params["end"] = str(end)

    # กรอง channel เฉพาะเมื่อมีคอลัมน์จริง
    if channel and _fact_has_channel_column(ch):
        where.append("channel = %(ch)s")
        params["ch"] = channel

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    # Top menu
    top_sql = f"""
      SELECT sku, SUM(qty) AS total_qty, SUM(net_amount) AS revenue
      FROM analytics.fact_sales
      {where_sql}
      GROUP BY sku
      ORDER BY total_qty DESC
      LIMIT {{limit}}
    """.replace("{limit}", str(top_limit))

    # รายได้ + จำนวนบิลต่อ "ชั่วโมงท้องถิ่น"
    by_hour_sql = f"""
      SELECT
        toHour({tz_col})              AS hr,
        SUM(net_amount)               AS rev,
        uniqExact(order_id)           AS orders
      FROM analytics.fact_sales
      {where_sql}
      GROUP BY hr
      ORDER BY hr
    """

    # รายได้รายวัน (ท้องถิ่น)
    by_day_sql = f"""
      SELECT toDate({tz_col}) AS d, SUM(net_amount) AS rev
      FROM analytics.fact_sales
      {where_sql}
      GROUP BY d
      ORDER BY d
    """

    top_df  = ch.query_df(top_sql, params)
    hour_df = ch.query_df(by_hour_sql, params)
    day_df  = ch.query_df(by_day_sql, params)

    # เติม AOV = rev / orders (กันหารศูนย์)
    if 'orders' in hour_df.columns and len(hour_df):
        hour_df['aov'] = hour_df.apply(
            lambda r: (float(r['rev']) / r['orders']) if r['orders'] else 0.0, axis=1
        )

    # รายได้สะสมต่อวัน
    day_cum_df = day_df.copy()
    if len(day_cum_df):
        day_cum_df['cum_rev'] = day_cum_df['rev'].cumsum()

    # รายได้ตามช่องทาง (ถ้ามีคอลัมน์ channel)
    channel_df = pd.DataFrame(columns=['channel', 'rev'])
    if _fact_has_channel_column(ch):
        ch_sql = f"""
          SELECT channel, SUM(net_amount) AS rev
          FROM analytics.fact_sales
          {where_sql}
          GROUP BY channel
          HAVING channel != ''
          ORDER BY rev DESC
        """
        channel_df = ch.query_df(ch_sql, params)

    return top_df, hour_df, day_df, channel_df, day_cum_df
