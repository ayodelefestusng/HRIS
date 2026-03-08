import os
from sqlalchemy import create_engine, text

db_uri = 'postgresql://postgres:postgres@localhost:5432/hris'
engine = create_engine(db_uri)
try:
    with engine.connect() as conn:
        query = "SELECT DATE_TRUNC('month', transaction_date) AS month, COUNT(*) AS transaction_count FROM transactions WHERE transaction_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '2 months' GROUP BY month ORDER BY month;"
        result = conn.execute(text(query))
        print('Query executed successfully')
        rows = result.fetchall()
        print(f'Rows: {len(rows)}')
        for row in rows[:5]:  # limit to 5
            print(row)
except Exception as e:
    print(f'Error: {e}')