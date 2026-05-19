"""
Libralex Information System
database/db_connection.py

MySQL connection factory.
Edit DB_CONFIG below to match your MySQL Workbench setup.
"""

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "",
    "database": "libralex_db",
    "charset":  "utf8mb4",
    "use_pure": True,
}



def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        raise ConnectionError(
            f"Could not connect to MySQL database '{DB_CONFIG['database']}' "
            f"at {DB_CONFIG['host']}:{DB_CONFIG['port']}.\n\nDetails: {e}"
        )


def test_connection() -> dict:
    try:
        conn = get_connection()
        conn.close()
        return {
            "success": True,
            "message": f"Connected to '{DB_CONFIG['database']}' on {DB_CONFIG['host']}.",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}
