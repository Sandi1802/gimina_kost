import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'gimina_kost')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')

def init_db():
    print(f"Connecting to database {DB_NAME} on {DB_HOST}:{DB_PORT} as {DB_USER}...")
    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Reading schema_kos.sql...")
        with open('schema_kos.sql', 'r') as file:
            sql = file.read()
            
        print("Executing schema...")
        cursor.execute(sql)
        
        print("Schema successfully executed! Tables created.")

        # Seed Kamar for Jatinangor (21) and Gunung Batu (18)
        # Location 1: Jatinangor, Location 2: Gunung Batu
        cursor.execute("SELECT COUNT(*) FROM kamar")
        if cursor.fetchone()[0] == 0:
            print("Seeding rooms...")
            # Jatinangor
            for i in range(1, 22):
                cursor.execute(
                    "INSERT INTO kamar (location_id, room_number, monthly_rate) VALUES (1, %s, 1500000)",
                    (f"JTG-{i:02d}",)
                )
            # Gunung Batu
            for i in range(1, 19):
                cursor.execute(
                    "INSERT INTO kamar (location_id, room_number, monthly_rate) VALUES (2, %s, 1500000)",
                    (f"GNB-{i:02d}",)
                )
            print("Successfully seeded 21 rooms for Jatinangor and 18 rooms for Gunung Batu.")
        
        # Check if default owner exists, if not create one
        cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'owner@kos.com'")
        if cursor.fetchone()[0] == 0:
            import hashlib
            # Default password: password123
            hashed = hashlib.md5(b'password123').hexdigest()
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role_id, status)
                VALUES ('Owner Kos', 'owner@kos.com', %s, (SELECT id FROM roles WHERE name = 'Owner'), 'ACTIVE')
            ''', (hashed,))
            print("Default admin created: email=owner@kos.com | password=password123")

        cursor.close()
        conn.close()
        print("Database initialization complete.")
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == '__main__':
    init_db()
