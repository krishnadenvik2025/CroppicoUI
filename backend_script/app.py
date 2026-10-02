from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import db_checker
from slave_controller_esg import SlaveController
from datetime import datetime, timedelta
import subprocess, re, sqlite3, json, socket, constants, os, time, requests

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024
CORS(app)
device_id = constants.getserial()
master_version = 1.99

db_path = '/home/pi/croppico-api-new/sensor_data.db'
WPA_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"
slave = SlaveController(device_id)

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "Not Connected"

def connect_open_wifi(ssid, interface="wlan0"):
    try:
        conf_block = f'\nnetwork={{\n\tssid="{ssid}"\n\tkey_mgmt=NONE\n}}\n'

        append_cmd = f"echo '{conf_block}' | sudo tee -a {WPA_CONF} > /dev/null"
        subprocess.run(append_cmd, shell=True, check=True)

        subprocess.run(["sudo", "wpa_cli", "-i", interface, "reconfigure"],
                        capture_output=True, text=True, timeout=15)
        time.sleep(2)
        list_out = subprocess.run(
            ["sudo", "wpa_cli", "-i", interface, "list_networks"],
            capture_output=True, text=True, timeout=15).stdout

        net_id = None
        for line in list_out.strip().split("\n")[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1] == ssid:
                net_id = parts[0]

        if net_id is None:
            print(f"Could not find network id for '{ssid}' after reconfigure.")
            return False

        subprocess.run(["sudo", "wpa_cli", "-i", interface, "select_network", net_id],
                        capture_output=True, text=True, timeout=15)
        time.sleep(6)

        status = subprocess.run(
            ["sudo", "wpa_cli", "-i", interface, "status"],
            capture_output=True, text=True, timeout=15).stdout

        return f"ssid={ssid}" in status and "wpa_state=COMPLETED" in status

    except subprocess.CalledProcessError as e:
        print("Error connecting to open WiFi:", e)
        return False
    except subprocess.TimeoutExpired:
        print("Timed out connecting to open WiFi.")
        return False

def get_wifi_strength(interface='wlan0'):
    try:
        result = subprocess.check_output(['iwconfig', interface], stderr=subprocess.STDOUT, text=True)
        match = re.search(r'Signal level=(-\d+)', result)

        if match:
            signal_strength = int(match.group(1))
            if signal_strength is None:
                return "Notconnected"
            elif signal_strength >= -50:
                return "Good"
            elif -50 > signal_strength >= -70:
                return "Medium"
            else:
                return "Low"
        else:
            return None

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

@app.before_request
def log_api_call():
    print(f"API called: {request.endpoint}")

@app.route('/data', methods=["GET"])
def data():
    deviceData, alarm = slave.getSlaveData()
    deviceData["wifi_strength"] = get_wifi_strength()
    deviceData["program_name"] = slave.program_name
    return {"data": deviceData, "alarm": alarm}

@app.route('/notification')
def notify():
    return 'Hello, World!'

@app.route('/warning')
def warn():
    return 'Hello, World!'

@app.route('/lights', methods=["POST"])
def lights():
    data = request.json
    res = slave.setLightStatus(int(data['light']), int(data['state']))
    return {'result': res}

@app.route('/getsettings', methods=["GET"])
def getsettings():
    res = slave.getSettings()
    with sqlite3.connect(db_path) as conn:
        lgt = conn.execute(""" SELECT on_hour, on_min, off_hour, off_min FROM light_settings LIMIT 1 """).fetchone()
    if lgt:
        res['light'] = { "on_hour": lgt[0], "on_min": lgt[1], "off_hour": lgt[2], "off_min": lgt[3] }
    else:
        res['light'] = { "on_hour": 7, "on_min": 0, "off_hour": 21, "off_min": 0 }

    print(type(res))
    return res

@app.route('/historicalData/<start>/<end>', methods=["GET"])
def getchat(start, end):
    print("entering get chart")
    columns = ["PH", "EC", "water_temp", "ambient_temp"]
    all_data = []
    start_timestamp = start
    end_timestamp = end
    print(start_timestamp)
    print(end_timestamp)
    for column in columns:
        results = get_graph_value(start_timestamp, end_timestamp, column)
        all_data.append({"name": column, "data": results})
    json_output = {"data": all_data}
    print(json_output)
    print(type(json_output))
    return json_output

def get_graph_value(start_timestamp, end_timestamp, column):
    conn = sqlite3.connect('/home/pi/croppico-api-new/sensor_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, {}
        FROM sensor_data
        WHERE timestamp BETWEEN ? AND ?
    '''.format(column), (start_timestamp, end_timestamp))
    results = cursor.fetchall()
    conn.close()
    data = [{'x': row[0], 'y': row[1]} for row in results]
    return data

@app.route('/getGuideMediaList', methods=["GET"])
def media():
    demo_pdf_folder = '/var/www/html/assets/media/demo_pdf'
    demo_video_folder = '/var/www/html/assets/media/demo_video'
    pdf_files = get_file_list(demo_pdf_folder, '.pdf')
    video_files = get_file_list(demo_video_folder, '.mp4')
    result = {'Video': video_files, 'pdf': pdf_files}
    return result

def get_file_list(folder_path, file_type):
    file_list = []
    for filename in os.listdir(folder_path):
        if filename.endswith(file_type):
            if file_type == ".pdf":
                folder_path = "/assets/media/demo_pdf"
            if file_type == ".mp4":
                folder_path = "/assets/media/demo_video"
            file_url = f"{folder_path}/{filename}"
            file_list.append({'name': filename, 'url': file_url})
    return file_list

@app.route('/system/screen', methods=["POST"])
def pause_poll():
    params = request.json
    print(params)
    screen = params["screen"]
    status = params["status"]
    print(screen, status)
    res = slave.poll_pause(str(status))
    return {'result': res}

@app.route('/settings/<sType>', methods=["POST"])
def settings(sType):
    params = request.json
    print(sType, params)
    res = slave.setNewSettings(str(sType), params)
    # return res
    return {'result': res}
    # return {'result': True}

@app.route('/settings/9/getsensorcalibration/<aType>', methods=["GET"])
def sensorCalibration(aType):
    if int(aType) == 1:
        return {
            'data': [
                {
                    'value': 4,
                    'isShow': True
                },
                {
                    'value': 7,
                    'isShow': True
                },
                {
                    'value': 9,
                    'isShow': False
                },
                {
                    'value': 10,
                    'isShow': False
                },
            ]
        }
    if int(aType) == 2:
        return {
            'data': [
                {
                    'value': 12.88,
                    'isShow': False
                },
                {
                    'value': 700,
                    'isShow': False
                },
                {
                    'value': 1.413,
                    'isShow': True
                },
                {
                    'value': 2000,
                    'isShow': False
                },
            ]
        }

@app.route('/settings/9/getcalibrationresult', methods=["GET"])
def getresultfrommcu():
    res = slave.getcalibResult()
    return {'result': res}
    # return True

@app.route('/settings/9/putnumberofsolutionsdone', methods=["POST"])
def totalNumbersDone():
    params = request.json
    res = slave.putnumberofsolution(params)
    return {'result': res}

@app.route('/maintenance/state/<state>', methods=["POST"])
def maintenanceState(state):
    res = slave.setMaintenanceState(eval(state))
    return {'result': res}

@app.route('/maintenance/control/<mType>', methods=["POST"])
def maintenance(mType):
    state = request.json["state"]
    res = slave.setMaintenanceControl(int(mType), state)
    return {'result': res}

@app.route('/adhoc/start', methods=["POST"])
def adhoc():
    cmMsg = request.json
    res = slave.processAdhoc(cmMsg)
    return {'result': res}

@app.route('/system/restart', methods=["POST"])
def restart():
    res = slave.restartController()
    return {'result': res}

@app.route('/system/reseterror', methods=["POST"])
def reset():
    res = slave.resetError()
    return {'result': res}

@app.route('/system/flush', methods=["POST"])
def flush():
    state = request.json["status"]
    res = slave.flush(state)
    return {'result': res}

@app.route('/system/flush/getflushresult', methods=["GET"])
def flushresult():
    print("get flush result")
    res = slave.getFlushResult()
    return {'result': res}

@app.route('/system/topup', methods=["POST"])
def topup():
    state = request.json["status"]
    res = slave.topup(state)
    return {'result': res}

@app.route('/system/topup/gettopupresult', methods=["GET"])
def topupresult():
    print("get topup result")
    res = slave.getTopupResult()
    return {'result': res}

@app.route('/system/useracknowledgement', methods=["POST"])
def useracknowledgement():
    res = slave.useracknowledgement()
    return {'result': res}

@app.route('/system/model', methods=["POST"])
def model():
    res = slave.model()
    return {'result': res}
#New
@app.route('/system/resetwater', methods=["GET"])
def resetwater():
    res = slave.ResetWater()    
    return {'result': res}
#New
@app.route('/system/EMReset', methods=["GET"])
def emeterreset():
    res = slave.eMeterReset()
    return {'result': res}
#New
@app.route('/system/watercon/pause', methods=["GET"])
def watercon_pause():
    try:
        res = slave.waterpas("01")
        return {'result': res}
    except Exception as e:
        print("watercon_pause error", e)
        return {'result': False}   
#New
@app.route('/system/watercon/resume', methods=["GET"])
def watercon_resume():
    try:
        res = slave.waterpas("00")
        return {'result': res}
    except Exception as e:
        print("watercon_resume error", e)
        return {'result': False}

@app.route('/system/versioninfo', methods=["GET"])
def version():
    slave_version, board_version = slave.getSlaveVersion()
    ip = str(get_local_ip())
    res = {"slave": slave_version,
           "serial": slave.device_id,
           "master": master_version,
           "board_version": board_version,
           "local_ip": ip}
    print("home---------------->", res)
    return res

@app.route('/screensaverdata', methods=["POST"])
def screensaver():
    print("screensaver")
    data = request.json
    print("recieved", data)
    interval_time = request.json["interval_time"]
    status = request.json["status"]
    if str(status) == "True":
        status = 1
    if str(status) == "False":
        status = 0
    res = slave.screen_saver(interval_time, status)
    return {'result': res}

@app.route('/system/wifinames', methods=["GET"])
def wifinames():
    wifi_list = []
    try:
        output = subprocess.check_output(["sudo", "iw", "dev", "wlan0", "scan"]).decode("utf-8", errors="ignore")
        current_ssid = ""
        security = "OPEN"

        for line in output.split("\n"):
            line = line.strip()

            if line.startswith("capability:"):
                security = "SECURED" if "Privacy" in line else "OPEN"

            if line.startswith("SSID:"):
                current_ssid = line.replace("SSID:", "").strip()
                if current_ssid:
                    wifi_list.append({"ssid": current_ssid, "security": security})

        unique_wifi = {w["ssid"]: w for w in wifi_list}
        wifi_list = list(unique_wifi.values())

        try: cur = subprocess.check_output(["iwgetid", "-r"]).decode("utf-8").strip()
        except Exception: cur = ""

        return jsonify({"res": wifi_list, "cur": cur})

    except Exception as e:
        print("WiFi scan error:", e)
        return jsonify({"res": [], "cur": ""})

@app.route('/system/connectwifi', methods=["POST"])
def wificonnect():
    try:
        creds = request.get_json() or {}
        ssid = str(creds.get("ssid", "")).strip()
        pwd = str(creds.get("pwd", "")).strip()
        print("Connecting to:", ssid, "- password:", "(none, open network)" if not pwd else "(provided)")

        if not ssid:
            return jsonify({"res": False})
        #New
        if not pwd: #Working
            print("Connecting to OPEN WiFi...")
            success = connect_open_wifi(ssid)
            return {'res': success}

        if pwd:
            print("Connecting to SECURED WiFi...")
            c = subprocess.call(["sudo", "nodewifi.sh", ssid, pwd])
            if c != 0: return {'res': False}

    except Exception as e:
        print("Error:", e)
        return {'res': False}
    return {'res': True}
    
#New
@app.route("/settings/light", methods=["POST"])
def set_light_settings():
    try:
        data = request.json
        print(f"Setting Light ON/OFF time:  ", data)
        with sqlite3.connect(db_path) as conn:
            conn.execute("""INSERT INTO light_settings (id, on_hour, on_min, off_hour, off_min)
                        VALUES (1, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET
                        on_hour = excluded.on_hour, on_min = excluded.on_min, 
                        off_hour = excluded.off_hour, off_min = excluded.off_min""", 
                        ( int(data.get('on_hour', 7)), int(data.get('on_min', 0)),
                          int(data.get('off_hour', 21)), int(data.get('off_min', 0))))
            conn.commit()
        return jsonify({"result": True})
    except Exception as e:
        print(f"Error updating Light time: {type(e)} – {e}")
        return jsonify({"result": False})

if __name__ == '__main__':
    slave.start()
    db_checker.start_aqi_calc()
    app.run(port=14999, host="0.0.0.0") 

