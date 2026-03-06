import sqlite3
import psycopg2
import traceback
# gravity 
SQLITE_PATH = r"C:\Users\Pro\Desktop\PROJECT\Live\HR\myproject\db.sqlite3"
POSTGRES_URL = "postgres://postgres:postgres@localhost:5432/hris"

def migrate():
    sl_conn = sqlite3.connect(SQLITE_PATH)
    sl_cur = sl_conn.cursor()
    
    sl_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in sl_cur.fetchall()]
    
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()
    
    try:
        # Disable foreign key checks for the session
        pg_cur.execute("SET session_replication_role = 'replica';")
        
        for table in tables:
            print(f"Migrating table {table}...")
            
            sl_cur.execute(f"PRAGMA table_info({table})")
            columns_info = sl_cur.fetchall()
            columns = [info[1] for info in columns_info]
            
            # Check if table exists in Postgres
            pg_cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);", (table,))
            if not pg_cur.fetchone()[0]:
                print(f"  Table {table} does not exist in Postgres, skipping.")
                continue
                
            # Get actual columns in Postgres to prevent insertion errors if schemas aren't perfectly synced
            pg_cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s;", (table,))
            pg_col_info = pg_cur.fetchall()
            pg_cols = [row[0] for row in pg_col_info]
            pg_types = {row[0]: row[1] for row in pg_col_info}
            
            # Map columns
            common_cols = [c for c in columns if c in pg_cols]
            if not common_cols:
                continue
                
            cols_str_sl = ', '.join([f'"{c}"' for c in common_cols])
            sl_cur.execute(f"SELECT {cols_str_sl} FROM {table}")
            rows = sl_cur.fetchall()
            
            # Truncate Postgres table
            pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
            
            if not rows:
                print(f"  No rows in {table}.")
                continue
                
            # Convert boolean and JSON columns
            bool_cols_indices = [i for i, c in enumerate(common_cols) if pg_types[c] == 'boolean']
            json_cols_indices = [i for i, c in enumerate(common_cols) if pg_types[c] in ('json', 'jsonb')]
            
            if bool_cols_indices or json_cols_indices:
                converted_rows = []
                import json
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
                                    # Fallback: convert plain string to a JSON string or JSON array if it's comma separated
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
                
            cols_str_pg = ', '.join([f'"{c}"' for c in common_cols])
            placeholders = ', '.join(['%s' for _ in common_cols])
            insert_query = f"INSERT INTO {table} ({cols_str_pg}) VALUES ({placeholders})"
            
            pg_cur.executemany(insert_query, rows)
            print(f"  Migrated {len(rows)} rows for {table}.")
            
        pg_conn.commit()
    except Exception as e:
        pg_conn.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        raise
    finally:
        pg_cur.execute("SET session_replication_role = 'origin';")
        pg_conn.commit()
        pg_cur.close()
        pg_conn.close()
        sl_cur.close()
        sl_conn.close()
        
    print("\n--- Verification ---")
    
    # Reconnect for counting
    sl_conn = sqlite3.connect(SQLITE_PATH)
    sl_cur = sl_conn.cursor()
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cur = pg_conn.cursor()
    
    all_match = True
    for table in tables:
        pg_cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s);", (table,))
        if not pg_cur.fetchone()[0]:
            continue
            
        sl_cur.execute(f"SELECT COUNT(*) FROM {table}")
        sl_count = sl_cur.fetchone()[0]
        
        pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
        pg_count = pg_cur.fetchone()[0]
        
        status = "OK" if sl_count == pg_count else "MISMATCH"
        if status == "MISMATCH":
            all_match = False
        print(f"{table:35} SQLite: {sl_count:5} | Postgres: {pg_count:5} | {status}")
        
    if all_match:
        print("\nSUCCESS: All tables match in row counts!")
    else:
        print("\nWARNING: Some tables have mismatched counts.")

if __name__ == '__main__':
    migrate()
