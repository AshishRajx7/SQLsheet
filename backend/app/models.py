from app.db import get_connection
import time


def init_db(retries=10, delay=2):
    """
    Initialize required DB tables.
    Retries are needed because MySQL may start after backend.
    """
    for attempt in range(retries):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY,
                    name VARCHAR(255),
                    email VARCHAR(255),
                    _updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
                )
            """)

            # mysql change log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mysql_change_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_name VARCHAR(255),
                    row_id INT,
                    operation VARCHAR(20),
                    payload JSON,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            cursor.close()
            conn.close()

            print("Database initialized successfully")
            return

        except Exception as e:
            print(f"DB init failed, retrying {attempt + 1}/{retries}", e)
            time.sleep(delay)

    raise RuntimeError("Database initialization failed")
