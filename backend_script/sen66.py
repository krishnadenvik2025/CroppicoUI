import argparse, sqlite3, time, threading, requests
from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection, CrcCalculator
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
from sensirion_i2c_sen66.device import Sen66Device
from datetime import datetime

db_path = '/home/pi/croppico-api-new/sensor_data.db'
interval = 60 *5
API_KEY = '9f6287775e5e7cbc01e8281c41f81354'
cords = {'lat':12.93693, 'lon':80.23578}
BASE_URL = 'https://api.openweathermap.org/data/2.5/air_pollution'

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument('--i2c-port', '-p', default='/dev/i2c-1')
_args, _unknown = _parser.parse_known_args()
i2c_transceiver = None
sensor = None

def init_sensor():
    global sensor, i2c_transceiver
    try:
        i2c_transceiver = LinuxI2cTransceiver(_args.i2c_port)
        channel = I2cChannel( I2cConnection(i2c_transceiver),
            slave_address=0x6B,
            crc=CrcCalculator(8, 0x31, 0xff, 0x0))
        sensor = Sen66Device(channel)
        sensor.device_reset()
        time.sleep(1)
        sensor.start_continuous_measurement()
        print("SEN66 sensor initialized")
        return True
    except Exception as e:
        print(f"Failed to initialize SEN66 sensor: {e}")
        sensor = None
        return False
    
def get_table_columns(conn, table_name):
    cursor = conn.execute(f'PRAGMA table_info({table_name})')
    return {row[1] for row in cursor.fetchall()}

def ensure_table_columns(conn, table_name, columns):
    existing = get_table_columns(conn, table_name)
    for name, coltype in columns.items():
        if name not in existing:
            conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {name} {coltype}')

def init_tables():
    ddl=['''CREATE TABLE IF NOT EXISTS indoor_aqi (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            pm2_5     REAL,
            temp      REAL,
            hump      REAL,
            co2       REAL,
            aqi       INTEGER,
            voc       REAL,
            nox       REAL,
            pm10     REAL
        )''',
        '''CREATE TABLE IF NOT EXISTS outdoor_aqi (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            aqi       INTEGER,
            temp      REAL,
            hum       REAL,
            co2       REAL,
            voc       REAL,
            pm2p5     REAL,
            no2       REAL,
            so2       REAL,
            o3        REAL,
            pm10      REAL,
            nh3       REAL
        )''',
        '''CREATE TABLE IF NOT EXISTS powerlog (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
            emeter          REAL,
            emeter_error    INTEGER DEFAULT 0
        )''',
        '''CREATE TABLE IF NOT EXISTS esg_summary (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            received_date       DATETIME DEFAULT CURRENT_TIMESTAMP,
            growcycle_id        INTEGER,
            start_date          DATETIME,
            end_date            DATETIME,
            water_saved         REAL,
            miles_saved         REAL,
            plastic_avoided     REAL,
            total_yeild         REAL,
            power_saved         REAL,
            cum_water_saved     REAL,
            cum_miles_saved     REAL,
            cum_plastic_avoided REAL,
            cum_total_yeild     REAL,
            cum_power_saved     REAL
        )''',
        '''CREATE TABLE IF NOT EXISTS mqtt_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            topic           TEXT NOT NULL,
            payload         TEXT NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS light_settings(
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            modified_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            on_hour         INTEGER,
            on_min          INTEGER,
            off_hour        INTEGER,
            off_min         INTEGER
        )''']
    try:
        with sqlite3.connect(db_path) as conn:
            for stmt in ddl:
                conn.execute(stmt)
            ensure_table_columns(conn, 'indoor_aqi', {'pm2_5': 'REAL',
                'temp': 'REAL','hump': 'REAL','co2': 'REAL',
                'aqi': 'INTEGER','voc': 'REAL'})
            ensure_table_columns(conn, 'outdoor_aqi', {'aqi': 'INTEGER',
                'temp': 'REAL','hum': 'REAL','co2': 'REAL',
                'voc': 'REAL','pm2p5': 'REAL',"no2": 'REAL',"so2": 'REAL','o3': 'REAL'})
        print("All DB tables ready")
        return True
    except sqlite3.Error as e:
        print(f"DB init failed: {e}")
        return False

def calculate_pm25_aqi(pm25):
    pm25 = max(0.0, pm25)
    breakpoints = [(0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500)]
    for Clow, Chigh, Ilow, Ihigh in breakpoints:
        if pm25 <= Chigh:
            return round(((Ihigh - Ilow) / (Chigh - Clow)) * (pm25 - Clow) + Ilow)
    return 500

def calculate_iaq(pm25, voc_index, co2):
    pm25_score = calculate_pm25_aqi(pm25)
    voc_score = min(500, max(0, int(voc_index)))

    if co2 <= 600: co2_score = 0
    elif co2 <= 800: co2_score = 50
    elif co2 <= 1000: co2_score = 100
    elif co2 <= 1500: co2_score = 200
    elif co2 <= 2000:co2_score = 300
    elif co2 <= 5000:co2_score = 400
    else: co2_score = 500

    score = (pm25_score * 0.60 + voc_score * 0.20 + co2_score * 0.20)
    return round(score)

def read_sen66():
    if sensor is None:
        with sqlite3.connect(db_path) as conn:
            conn.execute('INSERT INTO indoor_aqi (pm2_5, temp, hump, co2, aqi, voc, pm10) VALUES (?,?,?,?,?,?)',
                        (0,0,0,0,0,0,0))
            conn.close()
        return {"error": "Sensor not initialized"}
    try:
        (mass_concentration_pm1p0, mass_concentration_pm2p5, mass_concentration_pm4p0,
         mass_concentration_pm10p0, humidity, temperature, voc_index, nox_index, co2) = sensor.read_measured_values()
        aqi = calculate_iaq(mass_concentration_pm2p5.value, voc_index.value, co2.value)
        return {"pm2p5": mass_concentration_pm2p5.value, "pm10":mass_concentration_pm10p0.value,"hum": humidity.value, "temp": temperature.value,
            "voc": voc_index.value,"nox":nox_index, "co2": co2.value, "aqi": aqi}
    except Exception as e:
        print(f"Error reading SEN66: {type(e)} - {e}")
        return {"error": "Sensor read failed"}

def fetch_outdoor_aqi():
    try:
        url = f"{BASE_URL}?lat={cords['lat']}&lon={cords['lon']}&appid={API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        all_data = data.get("list", [{}])[0]
        comp = all_data.get("components", {})
        sub_indices = []
        breakpoints = {"pm2_5": [(0, 30, 0, 50), (30, 60, 50, 100),(60, 90, 100, 200),
                (90, 120, 200, 300),(120, 250, 300, 400), (250, 500, 400, 500)],
            "pm10": [(0, 50, 0, 50), (50, 100, 50, 100),(100, 250, 100, 200), 
                (250, 350, 200, 300),(350, 430, 300, 400), (430, 600, 400, 500)],
            "no2": [(0, 40, 0, 50), (40, 80, 50, 100),(80, 180, 100, 200), 
                (180, 280, 200, 300), (280, 400, 300, 400), (400, 500, 400, 500)],
            "so2": [(0, 40, 0, 50), (40, 80, 50, 100), (80, 380, 100, 200),
                (380, 800, 200, 300), (800, 1600, 300, 400), (1600, 2500, 400, 500)],
            "o3": [(0, 50, 0, 50), (50, 100, 50, 100),(100, 168, 100, 200),
                   (168, 208, 200, 300),(208, 748, 300, 400), (748, 1000, 400, 500)]}

        for pollutant, ranges in breakpoints.items():
            concentration = comp.get(pollutant)
            if concentration is None:
                continue
            concentration = float(concentration)

            for c_low, c_high, i_low, i_high in ranges:
                if c_low <= concentration <= c_high:
                    sub_aqi = (((i_high - i_low) / (c_high - c_low))* (concentration - c_low)+ i_low)
                    sub_indices.append(round(sub_aqi))
                    break
                else:
                    if concentration > ranges[-1][1]:
                        sub_indices.append(500)

        if not sub_indices:
            print("Unable to calculate AQI: No valid pollutant data")
            return False
        aqi = min(max(sub_indices), 500)

        with sqlite3.connect(db_path) as conn:
            conn.execute(""" INSERT INTO outdoor_aqi ( aqi, temp, hum, co2, voc,
            pm2p5, no2, so2, o3, pm10, nh3 )VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
            ( aqi, None, None, comp.get("co"), None, comp.get("pm2_5"), comp.get("no2"),
            comp.get("so2"), comp.get("o3"), comp.get("pm10"), comp.get("nh3")))
        conn.close()

        print(f"Outdoor AQI data stored successfully. AQI: {aqi}")
        return True

    except Exception as e:
        print(f"Error getting/storing outdoor AQI: {e}")
        return False

def filter_data(stop_event):
    alpha, pre = 0.2, None
    while not stop_event.is_set():
        if sensor is None:
            if not init_sensor():
                stop_event.wait(60)
                continue
        stop_event.wait(30)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mode FROM oaq")
            row = cursor.fetchone()
            mode = row[0]
        if mode == "api":
            with sqlite3.connect(db_path) as conn:
                cur=conn.cursor()
                cur.execute('''SELECT timestamp FROM outdoor_aqi ORDER BY id DESC LIMIT 1''')
                last_update = cur.fetchone()
                print("last updated.....  ",last_update)
                if last_update:
                    print("check time")
                    time_code = datetime.strptime(last_update[0],"%Y-%m-%d %H:%M:%S").timestamp()
                    if time_code < int(time.time()) - 21630 :
                        fetch_outdoor_aqi()
                else:
                    print("not avaliable....")
                    fetch_outdoor_aqi()
        
        data = read_sen66()
        if "error" not in data and data['aqi'] == 500 and data['voc'] in [0,None]:
            time.sleep(100)
            data = read_sen66()
        if "error" not in data:
            pre = data['aqi'] if pre is None else alpha * data['aqi'] + (1 - alpha) * pre
            try:
                with sqlite3.connect(db_path) as conn:
                    conn.execute(
                        'INSERT INTO indoor_aqi (pm2_5, temp, hump, co2, aqi, voc, pm10) VALUES (?,?,?,?,?,?,?)',
                        (data['pm2p5'], data['temp'], data['hum'], data['co2'], round(pre), data['voc'], data['pm10'])
                    )
                conn.close()
                print(f"Successfully inserted data: {data}")
            except sqlite3.Error as e:
                print(f"DB write failed: {e}")
        stop_event.wait(interval)

def start_aqi_calc():
    if not init_tables():
        print("Failed to initialize database tables. AQI thread not started.")
        return None
    stop_event = threading.Event()
    thread = threading.Thread(target=filter_data, args=(stop_event,), daemon=True)
    thread.start()
    return stop_event