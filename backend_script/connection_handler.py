import time, json, socket, sqlite3, requests, baselogger
import paho.mqtt.client as mqtt
from constants import Peripherals

logToFile = False
db_path = "/home/pi/croppico-api-new/sensor_data.db"

def check_internet(timeout=3):
    test_servers = [("1.1.1.1", 53),("8.8.8.8", 53),("9.9.9.9", 53)]
    print("checking internet...")

    for host, port in test_servers:
        try:
            socket.setdefaulttimeout(timeout)
            with socket.create_connection((host, port), timeout):
                print("internet is available")
                return True
        except OSError:
            continue
    print("internet is not available")
    return False

def getOAQdetails():
    default = {"mode": None, "device_id": None}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM oaq")
        row = cursor.fetchone()
        conn.close()
        print(f"OAQ details fetched: {dict(row) if row else None}")
        if row:
            return {"mode": row["mode"], "device_id": row["device_id"]}
        return default
    except Exception as e:
        print(f"getOAQdetails error: {e}")
        return default

class ConnectionHandler:
    def __init__(self, device_id):
        self.client = mqtt.Client()
        self.device_id = device_id
        self.OAQdetails = getOAQdetails()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        if logToFile:
            self.logger = baselogger.get_logger('Connection Handler')
            self.logger.info("Initiated")
        self.connect()

    def re_init_logger(self):
        if logToFile:
            self.logger.removeHandler(self.logger.handlers[0])
            self.logger = baselogger.get_logger('Connection Handler')

    def on_connect(self, client, userdata, flags, rc):
        if logToFile: self.logger.info("Connected with MQTT broker")
        if rc == 0:
            self.client.connected_flag = True  # set flag
            print("Connected OK")
            self.client.subscribe("server/" + self.device_id + "/#")
            self.client.subscribe(topic="croppico/" + self.device_id + "/EndBatch")
            self.client.subscribe(topic="croppico/" + self.device_id + "/StartBatch")
            self.client.subscribe(topic="croppico/" + self.device_id + "/oaq")
            if self.OAQdetails and self.OAQdetails.get('mode') == "sensor" and self.OAQdetails.get('device_id'):
                self.client.subscribe(topic="croppico/" + self.OAQdetails['device_id'] + "/oaq")
#            self.client.subscribe("server/0000000032d7ed1a/#")

    def on_message(self, client, userdata, msg):
        if logToFile: self.logger.info("Received payload %s" % msg)
        return msg
    
    def publish_pending(self):
        # if not self.client.is_connected():
        #     return
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(""" SELECT id, topic, payload FROM mqtt_queue ORDER BY id""")
        rows = cur.fetchall()

        for row in rows:
            time.sleep(0.5)
            msg_id, topic, payload = row
            result = self.client.publish(topic, payload)
            result.wait_for_publish()
            if result.rc == 0:
                cur.execute("DELETE FROM mqtt_queue WHERE id=?", (msg_id,))
                conn.commit()
            else:
                break
        conn.close()

    def queue_message(self,topic, payload):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""INSERT INTO mqtt_queue(topic, payload) VALUES (?, ?)""", (topic, payload))
        conn.commit()
        conn.close()

    def publish(self, dtype, data):
        try:
            if check_internet():
                self.publish_pending()
                if logToFile: self.logger.info("Publishing %s %s" % (dtype, data))
                self.client.publish(topic="croppico/" + self.device_id + "/" + dtype, payload=data)
            else:
                self.queue_message(topic="croppico/" + self.device_id + "/" + dtype, payload=data)
                if logToFile:self.logger.info("Offline. Message stored in queue.")
        except Exception as e:
            self.queue_message(topic="croppico/" + self.device_id + "/" + dtype, payload=data)
            if logToFile:self.logger.error(e)
            pass

    def connect(self):
        try:
            self.client.username_pw_set(username="homie", password="a'M5xu+N3RJ*_#")
            #self.client.connect_async("ec2-65-0-156-233.ap-south-1.compute.amazonaws.com", 1883, 60)
            self.client.connect_async("ec2-13-234-159-78.ap-south-1.compute.amazonaws.com", 1883, 60)
            self.client.publish(topic="croppico/" + self.device_id + "/connection",
                                payload=json.dumps({"time": int(time.time())}))
            self.client.subscribe("server/" + self.device_id + "/#")
            self.client.loop_start()
        except Exception as e:
            if logToFile:self.logger.error(e)
            time.sleep(5)
            self.connect()
