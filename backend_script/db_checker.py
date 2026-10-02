import sqlite3

db_path = '/home/pi/croppico-api-new/sensor_data.db'
    
def get_table_columns(conn, table_name):
    cursor = conn.execute(f'PRAGMA table_info({table_name})')
    return {row[1] for row in cursor.fetchall()}

def ensure_table_columns(conn, table_name, columns):
    existing = get_table_columns(conn, table_name)
    for name, coltype in columns.items():
        if name not in existing:
            print(f"Adding missing column '{name}' to '{table_name}'")
            conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {name} {coltype}')

def init_tables():
    ddl = [
        '''CREATE TABLE IF NOT EXISTS powerlog (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
            emeter        REAL,
            emeter_error  INTEGER DEFAULT 0
        )''',

        '''CREATE TABLE IF NOT EXISTS mqtt_queue (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            topic       TEXT NOT NULL,
            payload     TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )''',

        '''CREATE TABLE IF NOT EXISTS light_settings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            on_hour     INTEGER,
            on_min      INTEGER,
            off_hour    INTEGER,
            off_min     INTEGER
        )'''
    ]

    expected_columns = {
        'powerlog': {
            'emeter': 'REAL',
            'emeter_error': 'INTEGER'
        },
        'mqtt_queue': {
            'topic': 'TEXT',
            'payload': 'TEXT',
            'created_at': 'DATETIME'
        },
        'light_settings': {
            'modified_at': 'DATETIME',
            'on_hour': 'INTEGER',
            'on_min': 'INTEGER',
            'off_hour': 'INTEGER',
            'off_min': 'INTEGER'
        }
    }

    try:
        with sqlite3.connect(db_path) as conn:
            for stmt in ddl:
                conn.execute(stmt)
            for table_name, columns in expected_columns.items():
                ensure_table_columns(conn, table_name,columns)
            conn.commit()
        print("All DB tables ready")
        return True

    except sqlite3.Error as e:
        print(f"DB init failed: {e}")
        return False

def start_aqi_calc():
    if not init_tables():
        print("Failed to initialize database tables. AQI thread not started.")
        return None