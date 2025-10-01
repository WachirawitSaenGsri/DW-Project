import os
import clickhouse_connect

_client = None

def get_client():
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            port=int(os.getenv("CLICKHOUSE_PORT", 8123)),
            username=os.getenv("CLICKHOUSE_USER", "app_user"),
            password=os.getenv("CLICKHOUSE_PASSWORD", "StrongP@ss!"),
            database=os.getenv("CLICKHOUSE_DB", "analytics"),
        )
    return _client
