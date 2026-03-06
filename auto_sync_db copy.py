#!/usr/bin/env python3
# vsc copilot
"""
Automated Database Comparison and Synchronization Script
Compares SQLite to PostgreSQL, cleans PostgreSQL, syncs data, and verifies
"""

import sqlite3
import psycopg2
import json
import traceback
from datetime import datetime
from collections import defaultdict

# --- CONFIGURATION ---
SQLITE_PATH = r"C:\Users\Pro\Desktop\PROJECT\Live\HR\myproject\db.sqlite3"
POSTGRES_URL = "postgres://postgres:postgres@localhost:5432/hris"

class AutoDBSyncer:
    def __init__(self, sqlite_path, postgres_url):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.sl_conn = None
        self.pg_conn = None
        self.sl_cur = None
        self.pg_cur = None
        
    def connect(self):
        """Connect to both databases"""
        try:
            self.sl_conn = sqlite3.connect(self.sqlite_path)
            self.sl_conn.row_factory = sqlite3.Row
            self.sl_cur = self.sl_conn.cursor()
            
            self.pg_conn = psycopg2.connect(self.postgres_url)
            self.pg_cur = self.pg_conn.cursor()
            print("✓ Connected to both databases")
            return True
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
            
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
        pk_cols = [col[1] for col in columns if col[5] == 1]
        return pk_cols if pk_cols else ['id']
        
    def step_1_compare_before_sync(self):
        """Step 1: Compare databases before synchronization"""
        print("\n" + "="*90)
        print("STEP 1: COMPARING DATABASES (BEFORE SYNCHRONIZATION)")
        print("="*90 + "\n")
        
        tables = self.get_tables()
        comparison_results = {}
        total_sl_rows = 0
        total_pg_rows = 0
        tables_with_issues = 0
        
        for table in tables:
            self.pg_cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);",
                (table,)
            )
            
            if not self.pg_cur.fetchone()[0]:
                print(f"  ⚠ {table:50} PG TABLE MISSING")
                tables_with_issues += 1
                continue
                
            # Get SQLite count
            self.sl_cur.execute(f"SELECT COUNT(*) FROM {table}")
            sl_count = self.sl_cur.fetchone()[0]
            
            # Get PostgreSQL count
            self.pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            pg_count = self.pg_cur.fetchone()[0]
            
            total_sl_rows += sl_count
            total_pg_rows += pg_count
            
            if sl_count == pg_count:
                status = "✓"
            else:
                status = "⚠"
                tables_with_issues += 1
                
            print(f"  {status} {table:45} SQLite: {sl_count:6} | PG: {pg_count:6}")
            comparison_results[table] = {'sl': sl_count, 'pg': pg_count}
            
        print(f"\n  {'─'*90}")
        print(f"  {'':<45} Total: {total_sl_rows:6} | {total_pg_rows:6}")
        print(f"\n  Summary: {len(tables)} tables, {tables_with_issues} with issues")
        print(f"  SQLite total rows: {total_sl_rows}")
        print(f"  PostgreSQL total rows: {total_pg_rows}")
        
        return comparison_results, total_sl_rows, total_pg_rows
        
    def step_2_delete_postgres_data(self):
        """Step 2: Delete all data from PostgreSQL (clean slate)"""
        print("\n" + "="*90)
        print("STEP 2: CLEANING POSTGRESQL DATABASE")
        print("="*90 + "\n")
        
        tables = self.get_tables()
        
        try:
            self.pg_cur.execute("SET session_replication_role = 'replica';")
            
            for table in tables:
                self.pg_cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);",
                    (table,)
                )
                if not self.pg_cur.fetchone()[0]:
                    continue
                    
                self.pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
                print(f"  ✓ Truncated {table}")
                
            self.pg_conn.commit()
            print("\n✓ PostgreSQL database cleaned successfully")
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"✗ Error cleaning PostgreSQL: {e}")
            return False
        finally:
            self.pg_cur.execute("SET session_replication_role = 'origin';")
            self.pg_conn.commit()
            
    def step_3_synchronize_data(self):
        """Step 3: Synchronize data from SQLite to PostgreSQL"""
        print("\n" + "="*90)
        print("STEP 3: SYNCHRONIZING DATA (SQLite → PostgreSQL)")
        print("="*90 + "\n")
        
        tables = self.get_tables()
        total_rows_synced = 0
        
        try:
            self.pg_cur.execute("SET session_replication_role = 'replica';")
            
            for table in tables:
                self.pg_cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);",
                    (table,)
                )
                if not self.pg_cur.fetchone()[0]:
                    print(f"  ⚠ {table:50} PG table missing, skipping")
                    continue
                    
                # Get column info
                self.sl_cur.execute(f"PRAGMA table_info({table})")
                columns_info = self.sl_cur.fetchall()
                columns = [info[1] for info in columns_info]
                
                # Get PG column info
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
                    
                # Fetch data from SQLite
                cols_str = ', '.join([f'"{c}"' for c in common_cols])
                self.sl_cur.execute(f"SELECT {cols_str} FROM {table}")
                rows = self.sl_cur.fetchall()
                
                if not rows:
                    print(f"  ◦ {table:50} No rows to sync")
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
                total_rows_synced += len(rows)
                print(f"  ✓ {table:45} Synced {len(rows):6} rows")
                
            self.pg_conn.commit()
            print(f"\n✓ Data synchronization completed")
            print(f"  Total rows synchronized: {total_rows_synced}")
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            print(f"✗ Error during synchronization: {e}")
            traceback.print_exc()
            return False
        finally:
            self.pg_cur.execute("SET session_replication_role = 'origin';")
            self.pg_conn.commit()
            
    def step_4_verify_sync(self):
        """Step 4: Verify that data was synced correctly"""
        print("\n" + "="*90)
        print("STEP 4: VERIFYING SYNCHRONIZATION")
        print("="*90 + "\n")
        
        tables = self.get_tables()
        all_match = True
        total_sl_rows = 0
        total_pg_rows = 0
        perfect_tables = 0
        
        print(f"  {'Table':<45} | {'SQLite':-^10} | {'PostgreSQL':-^10} | Status")
        print(f"  {'-'*90}")
        
        for table in tables:
            self.pg_cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);",
                (table,)
            )
            if not self.pg_cur.fetchone()[0]:
                print(f"  {table:<45} | Table not in PostgreSQL")
                continue
                
            self.sl_cur.execute(f"SELECT COUNT(*) FROM {table}")
            sl_count = self.sl_cur.fetchone()[0]
            
            self.pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            pg_count = self.pg_cur.fetchone()[0]
            
            total_sl_rows += sl_count
            total_pg_rows += pg_count
            
            if sl_count == pg_count:
                status = "✓ MATCH"
                perfect_tables += 1
            else:
                status = f"✗ MISMATCH (diff: {abs(sl_count - pg_count)})"
                all_match = False
                
            print(f"  {table:<45} | {sl_count:^10} | {pg_count:^10} | {status}")
            
        print(f"  {'-'*90}")
        print(f"  {'TOTAL':<45} | {total_sl_rows:^10} | {total_pg_rows:^10} |")
        
        print(f"\n  Summary:")
        print(f"    Tables checked: {len(tables)}")
        print(f"    Perfect matches: {perfect_tables}")
        print(f"    Mismatches: {len(tables) - perfect_tables}")
        print(f"    Total SQLite rows: {total_sl_rows}")
        print(f"    Total PostgreSQL rows: {total_pg_rows}")
        
        if all_match:
            print(f"\n  ✓✓✓ SUCCESS! All tables match perfectly! ✓✓✓")
            return True
        else:
            print(f"\n  ⚠ WARNING: Some tables have mismatched row counts")
            return False
            
    def run_full_sync(self):
        """Run complete synchronization workflow"""
        print(f"\n{'='*90}")
        print(f"  DATABASE SYNCHRONIZATION WORKFLOW")
        print(f"  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*90}")
        
        # Step 1: Compare before
        if not self.connect():
            return False
            
        before_results, before_sl, before_pg = self.step_1_compare_before_sync()
        
        # Step 2: Clean PostgreSQL
        if not self.step_2_delete_postgres_data():
            self.disconnect()
            return False
            
        # Step 3: Synchronize
        if not self.step_3_synchronize_data():
            self.disconnect()
            return False
            
        # Step 4: Verify
        success = self.step_4_verify_sync()
        
        self.disconnect()
        
        # Final summary
        print(f"\n{'='*90}")
        print(f"  WORKFLOW COMPLETE")
        print(f"  End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*90}\n")
        
        return success

def main():
    print("\n" + "█"*90)
    print("█" + " "*88 + "█")
    print("█" + "  SQLITE ↔ POSTGRESQL DATABASE SYNCHRONIZER".center(88) + "█")
    print("█" + "  Automated Comparison, Cleaning, and Verification".center(88) + "█")
    print("█" + " "*88 + "█")
    print("█"*90 + "\n")
    
    syncer = AutoDBSyncer(SQLITE_PATH, POSTGRES_URL)
    success = syncer.run_full_sync()
    
    if success:
        print("\n" + "🎉 "*45)
        print("All databases are now synchronized and verified!")
        print("🎉 "*45 + "\n")
    else:
        print("\n" + "⚠ "*45)
        print("Synchronization completed but with warnings.")
        print("⚠ "*45 + "\n")

if __name__ == '__main__':
    main()
