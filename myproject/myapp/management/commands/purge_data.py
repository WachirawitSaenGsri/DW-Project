from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from myapp.models import Order, MenuItem, Customer   # แก้ app ให้ตรงโปรเจกต์คุณ
from myapp.services.ch_client import get_client

#docker compose exec web python manage.py purge_data --all
class Command(BaseCommand):
    help = "Purge MySQL & ClickHouse data. Use --before YYYY-MM-DD for partial delete, or --all."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Delete ALL data.")
        parser.add_argument("--before", type=str, help="Delete data before date (YYYY-MM-DD).")

    def handle(self, *args, **opts):
        ch = get_client()

        if opts["all"]:
            # MySQL
            Order.objects.all().delete()
            MenuItem.objects.all().delete()
            Customer.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("MySQL cleared."))

            # ClickHouse
            ch.command("TRUNCATE TABLE analytics.fact_sales")
            self.stdout.write(self.style.SUCCESS("ClickHouse truncated."))
            return

        if opts["before"]:
            cutoff = timezone.make_aware(datetime.strptime(opts["before"], "%Y-%m-%d"))
            # MySQL
            Order.objects.filter(order_ts__lt=cutoff).delete()
            self.stdout.write(self.style.SUCCESS(f"MySQL: deleted records before {cutoff}"))

            # ClickHouse
            ch.command(f"""
                ALTER TABLE analytics.fact_sales
                DELETE WHERE order_ts < toDateTime('{cutoff.strftime("%Y-%m-%d %H:%M:%S")}');
            """)
            self.stdout.write(self.style.SUCCESS("ClickHouse: delete mutation submitted."))
            return

        self.stdout.write(self.style.ERROR("Specify --all or --before YYYY-MM-DD"))
