# vsc copilot

import sqlite3
import psycopg2
import json
import traceback
from collections import defaultdict
from datetime import datetime
import pandas as pd

# --- CONFIGURATION ---
SQLITE_PATH = r"C:\Users\Pro\Desktop\PROJECT\Live\HR\myproject\db.sqlite3"
POSTGRES_URL = "postgres://postgres:postgres@localhost:5432/hris"

class DBComparator:
    def __init__(self, sqlite_path, postgres_url):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.sl_conn = None
        self.pg_conn = None
        self.sl_cur = None
        self.pg_cur = None
        self.report = []
        
    def connect(self):
        """Connect to both databases"""
        try:
            self.sl_conn = sqlite3.connect(self.sqlite_path)
            self.sl_conn.row_factory = sqlite3.Row
            self.sl_cur = self.sl_conn.cursor()
            
            self.pg_conn = psycopg2.connect(self.postgres_url)
            self.pg_cur = self.pg_conn.cursor()
            print("✓ Connected to both databases")
        except Exception as e:
            print(f"✗ Connection error: {e}")
            raise
            
    def disconnect(self):
        """Disconnect from both databases"""
        if self.sl_cur:
            self.sl_cur.close()
        if self.sl_conn:
            self.sl_conn.close()
        if self.pg_cur:
            self.pg_cur.close()
        if self.pg_conn:
            self.pg_conn.close()
            
    def get_tables(self):
        """Get all tables from SQLite"""
        self.sl_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [row[0] for row in self.sl_cur.fetchall()]
        
    def get_primary_key(self, table):
        """Get primary key column(s) for a table"""
        self.sl_cur.execute(f"PRAGMA table_info({table})")
        columns = self.sl_cur.fetchall()
        pk_cols = [col[1] for col in columns if col[5] == 1]  # pk flag is at index 5
        return pk_cols if pk_cols else ['id']
        
    def normalize_value(self, value, col_type):
        """Normalize values for comparison"""
        if value is None:
            return None
        if col_type in ('json', 'jsonb'):
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except:
                    return value
            return value
        if col_type == 'boolean':
            return bool(value)
        return value
        
    def compare_table(self, table):
        """Compare a single table between SQLite and PostgreSQL"""
        print(f"\n{'='*80}")
        print(f"Comparing table: {table}")
        print(f"{'='*80}")
        
        try:
            # Get column info from SQLite
            self.sl_cur.execute(f"PRAGMA table_info({table})")
            sl_columns_info = self.sl_cur.fetchall()
            sl_columns = [col[1] for col in sl_columns_info]
            
            # Check if table exists in PostgreSQL
            self.pg_cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);",
                (table,)
            )
            if not self.pg_cur.fetchone()[0]:
                print(f"  ⚠ Table {table} does not exist in PostgreSQL")
                self.report.append(f"TABLE_MISSING_PG: {table}")
                return
                
            # Get column info from PostgreSQL
            self.pg_cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s;",
                (table,)
            )
            pg_col_info = self.pg_cur.fetchall()
            pg_columns = {row[0]: row[1] for row in pg_col_info}
            
            # Find common columns
            common_cols = [c for c in sl_columns if c in pg_columns]
            if not common_cols:
                print(f"  ⚠ No common columns found")
                return
                
            # Get primary key
            pk_cols = self.get_primary_key(table)
            
            # Fetch all rows from SQLite
            cols_str = ', '.join([f'"{c}"' for c in common_cols])
            self.sl_cur.execute(f"SELECT {cols_str} FROM {table}")
            sl_rows = self.sl_cur.fetchall()
            
            # Fetch all rows from PostgreSQL
            cols_str_pg = ', '.join([f'"{c}"' for c in common_cols])
            self.pg_cur.execute(f"SELECT {cols_str_pg} FROM {table}")
            pg_rows = self.pg_cur.fetchall()
            
            # Convert to dictionaries for easier comparison
            sl_data = {tuple(row[pk] for pk in pk_cols): dict(zip(common_cols, row)) for row in sl_rows}
            pg_data = {tuple(row[i] for i, col in enumerate(common_cols) if col in pk_cols): 
                      {col: row[i] for i, col in enumerate(common_cols)} for row in pg_rows}
            
            # Build proper comparison dict for PG
            pg_data_by_pk = {}
            self.pg_cur.execute(f"SELECT {cols_str_pg} FROM {table}")
            pg_rows = self.pg_cur.fetchall()
            for row in pg_rows:
                row_dict = dict(zip(common_cols, row))
                pk_key = tuple(row_dict[pk] for pk in pk_cols)
                pg_data_by_pk[pk_key] = row_dict
            
            # Count records
            print(f"  SQLite records: {len(sl_data)}")
            print(f"  PostgreSQL records: {len(pg_data_by_pk)}")
            
            # Find differences
            missing_in_pg = set(sl_data.keys()) - set(pg_data_by_pk.keys())
            extra_in_pg = set(pg_data_by_pk.keys()) - set(sl_data.keys())
            common_keys = set(sl_data.keys()) & set(pg_data_by_pk.keys())
            
            mismatched = []
            for pk_key in common_keys:
                sl_row = sl_data[pk_key]
                pg_row = pg_data_by_pk[pk_key]
                
                diffs = {}
                for col in common_cols:
                    sl_val = sl_row.get(col)
                    pg_val = pg_row.get(col)
                    
                    # Normalize for comparison
                    col_type = pg_columns.get(col, 'text')
                    sl_normalized = self.normalize_value(sl_val, col_type)
                    pg_normalized = self.normalize_value(pg_val, col_type)
                    
                    if sl_normalized != pg_normalized:
                        diffs[col] = {
                            'sqlite': sl_val,
                            'postgres': pg_val
                        }
                
                if diffs:
                    mismatched.append({
                        'pk': pk_key,
                        'differences': diffs
                    })
                    
            # Print results
            print(f"\n  Results:")
            print(f"    ✓ Matching records: {len(common_keys) - len(mismatched)}")
            print(f"    ⚠ Mismatched records: {len(mismatched)}")
            print(f"    ✗ Missing in PostgreSQL: {len(missing_in_pg)}")
            print(f"    ✗ Extra in PostgreSQL: {len(extra_in_pg)}")
            
            # Detailed report
            if missing_in_pg:
                print(f"\n  Missing in PostgreSQL ({len(missing_in_pg)} records):")
                for i, pk in enumerate(list(missing_in_pg)[:5]):
                    print(f"    - {pk}")
                if len(missing_in_pg) > 5:
                    print(f"    ... and {len(missing_in_pg) - 5} more")
                    
            if extra_in_pg:
                print(f"\n  Extra in PostgreSQL ({len(extra_in_pg)} records):")
                for i, pk in enumerate(list(extra_in_pg)[:5]):
                    print(f"    - {pk}")
                if len(extra_in_pg) > 5:
                    print(f"    ... and {len(extra_in_pg) - 5} more")
                    
            if mismatched:
                print(f"\n  Mismatched records ({len(mismatched)} total):")
                for i, mismatch in enumerate(mismatched[:3]):
                    print(f"    PK: {mismatch['pk']}")
                    for col, values in mismatch['differences'].items():
                        print(f"      {col}: SQLite={values['sqlite']} | PG={values['postgres']}")
                if len(mismatched) > 3:
                    print(f"    ... and {len(mismatched) - 3} more")
                    
            return {
                'table': table,
                'sl_count': len(sl_data),
                'pg_count': len(pg_data_by_pk),
                'matching': len(common_keys) - len(mismatched),
                'mismatched': len(mismatched),
                'missing_in_pg': missing_in_pg,
                'extra_in_pg': extra_in_pg,
                'mismatched_details': mismatched
            }
            
        except Exception as e:
            print(f"  ✗ Error comparing {table}: {e}")
            traceback.print_exc()
            return None
            
    def compare_all(self):
        """Compare all tables"""
        self.connect()
        tables = self.get_tables()
        
        print(f"\n{'='*80}")
        print(f"Starting comparison at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tables to compare: {len(tables)}")
        print(f"{'='*80}")
        
        results = {}
        for table in tables:
            result = self.compare_table(table)
            if result:
                results[table] = result
                
        self.disconnect()
        return results
        
    def synchronize(self, delete_postgres_first=True):
        """Synchronize SQLite to PostgreSQL"""
        print(f"\n{'='*80}")
        print(f"Starting synchronization at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        self.connect()
        
        try:
            self.pg_cur.execute("SET session_replication_role = 'replica';")
            
            tables = self.get_tables()
            
            for table in tables:
                print(f"Processing {table}...")
                
                # Check if table exists in PG
                self.pg_cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);",
                    (table,)
                )
                if not self.pg_cur.fetchone()[0]:
                    print(f"  ⚠ Table {table} does not exist in PostgreSQL, skipping")
                    continue
                    
                if delete_postgres_first:
                    self.pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
                    print(f"  ✓ Truncated {table}")
                    
                # Get columns info
                self.sl_cur.execute(f"PRAGMA table_info({table})")
                columns_info = self.sl_cur.fetchall()
                columns = [info[1] for info in columns_info]
                
                # Get PG columns
                self.pg_cur.execute(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s;",
                    (table,)
                )
                pg_col_info = self.pg_cur.fetchall()
                pg_cols = [row[0] for row in pg_col_info]
                pg_types = {row[0]: row[1] for row in pg_col_info}
                
                # Find common columns
                common_cols = [c for c in columns if c in pg_cols]
                if not common_cols:
                    continue
                    
                # Fetch SQLite data
                cols_str = ', '.join([f'"{c}"' for c in common_cols])
                self.sl_cur.execute(f"SELECT {cols_str} FROM {table}")
                rows = self.sl_cur.fetchall()
                
                if not rows:
                    print(f"  ◦ No rows in {table}")
                    continue
                    
                # Convert data types
                bool_cols_indices = [i for i, c in enumerate(common_cols) if pg_types[c] == 'boolean']
                json_cols_indices = [i for i, c in enumerate(common_cols) if pg_types[c] in ('json', 'jsonb')]
                
                if bool_cols_indices or json_cols_indices:
                    converted_rows = []
                    for row in rows:
                        new_row = list(row)
                        for i in bool_cols_indices:
                            if new_row[i] is not None:
                                new_row[i] = bool(new_row[i])
                        for i in json_cols_indices:
                            val = new_row[i]
                            if val is not None:
                                if isinstance(val, str):
                                    try:
                                        json.loads(val)
                                    except json.JSONDecodeError:
                                        if ',' in val:
                                            val = json.dumps([x.strip() for x in val.split(',')])
                                        else:
                                            val = json.dumps(val)
                                    new_row[i] = val
                                elif isinstance(val, (list, dict)):
                                    new_row[i] = json.dumps(val)
                                else:
                                    new_row[i] = json.dumps(val)
                        converted_rows.append(tuple(new_row))
                    rows = converted_rows
                    
                # Insert data
                cols_str_pg = ', '.join([f'"{c}"' for c in common_cols])
                placeholders = ', '.join(['%s' for _ in common_cols])
                insert_query = f"INSERT INTO {table} ({cols_str_pg}) VALUES ({placeholders})"
                
                self.pg_cur.executemany(insert_query, rows)
                print(f"  ✓ Inserted {len(rows)} rows")
                
            self.pg_conn.commit()
            print("\n✓ Synchronization completed successfully")
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"✗ Error during synchronization: {e}")
            traceback.print_exc()
            raise
        finally:
            self.pg_cur.execute("SET session_replication_role = 'origin';")
            self.pg_conn.commit()
            self.disconnect()
            
    def create_comparison_report(self, results):
        """Create a detailed comparison report"""
        print(f"\n{'='*80}")
        print(f"COMPARISON REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        total_tables = len(results)
        perfect_match = 0
        issues = 0
        
        for table, result in results.items():
            if result['sl_count'] == result['pg_count'] and not result['mismatched']:
                status = "✓ MATCH"
                perfect_match += 1
            else:
                status = "⚠ MISMATCH"
                issues += 1
                
            print(f"{table:40} SL:{result['sl_count']:6} | PG:{result['pg_count']:6} | {status}")
            
        print(f"\n{'='*80}")
        print(f"Summary:")
        print(f"  Total tables: {total_tables}")
        print(f"  Perfect matches: {perfect_match}")
        print(f"  With issues: {issues}")
        print(f"{'='*80}\n")
        
        if issues > 0:
            print("TABLES WITH ISSUES:")
            for table, result in results.items():
                if result['sl_count'] != result['pg_count'] or result['mismatched']:
                    print(f"\n  {table}:")
                    if result['missing_in_pg']:
                        print(f"    - Missing in PostgreSQL: {len(result['missing_in_pg'])} records")
                    if result['extra_in_pg']:
                        print(f"    - Extra in PostgreSQL: {len(result['extra_in_pg'])} records")
                    if result['mismatched']:
                        print(f"    - Mismatched values: {len(result['mismatched'])} records")

def main():
    comparator = DBComparator(SQLITE_PATH, POSTGRES_URL)
    
    print("\n" + "="*80)
    print("DATABASE COMPARISON AND HARMONIZATION TOOL")
    print("="*80 + "\n")
    
    while True:
        print("\nOptions:")
        print("  1. Compare databases (detailed comparison)")
        print("  2. Synchronize (SQLite → PostgreSQL)")
        print("  3. Clean PostgreSQL and sync")
        print("  4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            results = comparator.compare_all()
            comparator.create_comparison_report(results)
            
        elif choice == '2':
            confirm = input("\nSynchronize WITHOUT deleting PostgreSQL data? (y/n): ").strip().lower()
            if confirm == 'y':
                comparator.synchronize(delete_postgres_first=False)
                
        elif choice == '3':
            confirm = input("\n⚠ This will DELETE all data in PostgreSQL tables! Continue? (y/n): ").strip().lower()
            if confirm == 'y':
                comparator.synchronize(delete_postgres_first=True)
                print("\n✓ Synchronization complete. Now comparing...")
                results = comparator.compare_all()
                comparator.create_comparison_report(results)
                
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid option. Please select 1-4.")

if __name__ == '__main__':
    main()
