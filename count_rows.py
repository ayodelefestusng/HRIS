import os
import django
from django.conf import settings
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

def count_rows():
    cursor = connection.cursor()
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    tables = cursor.fetchall()
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT count(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"{table_name}: {count}")

if __name__ == "__main__":
    count_rows()