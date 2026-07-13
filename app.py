from flask import Flask, request, send_file
from flask_cors import CORS
import constants, jsonify
from slave_controller_dsrc_uart_ui import SlaveController
import baselogger, os
import wifimanage as wfm
import subprocess, re, sqlite3, json, socket
from datetime import datetime, timedelta
import argparse, time, requests
from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection, CrcCalculator
from sensirion_driver_adapters.i2c_adapter.i2c_channel import I2cChannel
from sensirion_i2c_sen66.device import Sen66Device

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024
CORS(app)
device_id = constants.getserial()
slave = SlaveController(device_id)
master_version = 2.01
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
    
#for OAQ
API_KEY = '9f6287775e5e7cbc01e8281c41f81354'
cords = {'lat':12.93693, 'lon':80.23578}
BASE_URL = 'https://api.openweathermap.org/data/2.5/air_pollution'

'''sample = {
    "data": {
        "water_temperature": 14.5,
        "water_level": 1,
        "water_flow": 16,
        "ambient_temp": 23,
        "ambient_humid": 78,
        "water_pH": 8.1,
        "water_ec": 2000,
        "supp_ph_inc": 1,
        "supp_ph_dec": 1,
        "supp_ec_a": 1,
        "supp_ec_b": 1,
        "light_brightness": 70,
        "light_stat": [1, 0, 1, 0, 1],
        "error": 0
    },
    "settings": {
        "water_pump_setting": {
            "ontime": 30,
            "offtime": 40
        },
        "ph_setting": {
            "phmin": 7,
            "phmax": 9,
            "phideal": 8.1
        },
        "ec_setting": {
            "ecmin": 1800,
            "ecideal": 2100
        },
        "water_temperature_setting": {
            "tempmax": 23,
            "tempideal": 18
        },
        "supplement_pump_setting": {
            "ec": 60,
            "phinc": 30,
            "phdec": 30,
            "cycle": 40
        }
    }
}'''


@app.before_request
def log_api_call():
    print(f"API called: {request.endpoint}")



@app.route('/data', methods=["GET"])
def data():
    # return sample["data"]
    deviceData, alarm = slave.getSlaveData()
#    deviceData["wifi_strength"] = "low"
    deviceData["wifi_strength"] = get_wifi_strength()
    deviceData["program_name"] = slave.program_name
#    print("data--------------->", deviceData)
    return {"data": deviceData, "alarm": alarm}
    # return slave.getSlaveData()


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


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "Not Connected"


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
    all = wfm.Search()
    try:
        cur = str(subprocess.check_output(["sudo", "iwgetid"])).split('"')[1]
        res = {'res': all, 'cur': cur}
        return res
    except subprocess.CalledProcessError as e:
        print(e.output)
        res = {'res': all}
        return res


@app.route('/system/connectwifi', methods=["POST"])
def wificonnect():
    try:
        creds = request.json
        print("sudo", "nodewifi.sh", creds["ssid"], creds["pwd"])
        ssid = str(creds["ssid"])
        pwd = str(creds["pwd"])
        c = subprocess.call(["sudo", "nodewifi.sh", "" + ssid + "", "" + pwd + ""])
    except Exception as e:
        return {'res': False}
    return {'res': True}


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


if __name__ == '__main__':
    slave.start()
    app.run(port=14999, host="0.0.0.0")
