"""
Libralex Information System
database/seed_admin.py
Run AFTER schema.sql:  python database/seed_admin.py
"""
import getpass, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass
import bcrypt
from database.db_connection import get_connection

def main():
    print("=" * 55)
    print("  Libralex v2.0 — Initial Admin Account Setup")
    print("=" * 55)
    username  = input("Admin username  [admin]: ").strip() or "admin"
    full_name = input("Admin full name [System Administrator]: ").strip() or "System Administrator"
    email     = input("Admin email     [admin@libralex.edu]: ").strip() or "admin@libralex.edu"
    while True:
        password = getpass.getpass("Admin password (min 8 chars, upper, digit, symbol): ")
        confirm  = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("  ✗  Passwords do not match.\n"); continue
        if len(password) < 8:
            print("  ✗  Password too short.\n"); continue
        break
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO users (username, password_hash, email, role, full_name, is_active)
               VALUES (%s, %s, %s, 'admin', %s, 1)
               ON DUPLICATE KEY UPDATE
                   password_hash = VALUES(password_hash),
                   email = VALUES(email),
                   full_name = VALUES(full_name),
                   is_active = 1""",
            (username, pw_hash, email, full_name),
        )
        conn.commit()
        print(f"\n  ✓  Admin account '{username}' ready.  Run: python main.py\n")
    except Exception as exc:
        conn.rollback(); print(f"\n  ✗  {exc}\n"); sys.exit(1)
    finally:
        cursor.close(); conn.close()

if __name__ == "__main__":
    main()