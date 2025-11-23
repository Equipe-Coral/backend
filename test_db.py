import psycopg2
import sys

DB_HOST = "127.0.0.1"
DB_PORT = "5433"  # Changed to 5433
DB_NAME = "coral_db"
DB_USER = "coral_user"
DB_PASS = "senha123"

print(f"Attempting connection to {DB_HOST}:{DB_PORT}...")

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {repr(e)}")
