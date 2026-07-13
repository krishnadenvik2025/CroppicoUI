import argparse, time, sqlite3
from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection, CrcCalculator
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
from sensirion_i2c_sen66.device import Sen66Device

DB_PATH = '/home/pi/croppico-api-new/sensor_data.db'
MAX_ROWS = 60  # keep only the last 60 readings (FIFO)

# For Sen66
parser = argparse.ArgumentParser()
parser.add_argument('--i2c-port', '-p', default='/dev/i2c-1')
args = parser.parse_args()
i2c_transceiver = None
sensor = None

try:
    i2c_transceiver = LinuxI2cTransceiver(args.i2c_port)
    channel = I2cChannel(
        I2cConnection(i2c_transceiver),
        slave_address=0x6B,
        crc=CrcCalculator(8, 0x31, 0xff, 0x0)
    )
    sensor = Sen66Device(channel)
    sensor.device_reset()
    time.sleep(1)
    sensor.start_continuous_measurement()
except Exception as e:
    print(f"Failed to initialize SEN66 sensor: {e}")
    
def calculate_aqi(pm25):
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]

    for Clow, Chigh, Ilow, Ihigh in breakpoints:
        if Clow <= pm25 <= Chigh:
            aqi = ((Ihigh - Ilow) / (Chigh - Clow)) * (pm25 - Clow) + Ilow
            return round(aqi)

    return 500

def read_sen66():
    if sensor is None:
        return {"error": "Sensor not initialized"}

    try:
        (mass_concentration_pm1p0, mass_concentration_pm2p5, mass_concentration_pm4p0,
         mass_concentration_pm10p0, humidity, temperature, voc_index, nox_index, co2,
        ) = sensor.read_measured_values()
        aqi = calculate_aqi(mass_concentration_pm2p5.value)
        sen_data = {
            "pm1.0": mass_concentration_pm1p0.value,
            "pm2p5": mass_concentration_pm2p5.value,
            "pm4.0": mass_concentration_pm4p0.value,
            "pm10.0": mass_concentration_pm10p0.value,
            "hum": humidity.value,
            "temp": temperature.value,
            "voc": voc_index.value,
            "nox": nox_index.value,
            "co2": co2.value,
            "aqi": aqi
        }
        return sen_data

    except Exception as e:
        print(f"Error reading SEN66: {type(e)} – {e}")
        return {"error": "Sensor read failed"}

def init_db(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS aqi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            pm2_5 REAL,
            temp REAL,
            hump REAL,
            co2 REAL,
            aqi REAL
        )
    ''')
    conn.commit()

def trim_to_last_n(conn, n=MAX_ROWS):
    # Keep only the most recent n rows (FIFO ring buffer behaviour)
    conn.execute('''
        DELETE FROM aqi
        WHERE id NOT IN (
            SELECT id FROM aqi ORDER BY id DESC LIMIT ?
        )
    ''', (n,))
    conn.commit()

conn = sqlite3.connect(DB_PATH)
init_db(conn)

try:
    while True:
        data = read_sen66()
        if "error" not in data:
            try:
                conn.execute(
                    '''INSERT INTO aqi (pm2_5, temp, hump, co2, aqi) VALUES (?,?,?,?,?)''',
                    (data['pm2p5'], data['temp'], data['hum'], data['co2'], data['aqi'])
                )
                conn.commit()
                trim_to_last_n(conn)
            except sqlite3.Error as e:
                print(f"DB write failed: {e}")
        time.sleep(60)
except KeyboardInterrupt:
    print("Stopped by user.")
finally:
    conn.close()
    print("Closing")