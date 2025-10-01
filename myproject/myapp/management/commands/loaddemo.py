from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd
from myapp.services.ingest import load_csv_to_mysql_and_clickhouse
from pathlib import Path

class Command(BaseCommand):
    help = "Load demo sales data into MySQL and ClickHouse"

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR).parent / 'scripts' / 'sample_sales.csv'
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        load_csv_to_mysql_and_clickhouse(df)
        self.stdout.write(self.style.SUCCESS('Loaded demo data.'))