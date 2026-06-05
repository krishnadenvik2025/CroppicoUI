import datetime
import json, sqlite3
import time, datetime
from threading import Thread, Timer
from typing import List
from serial import Serial, SerialException, PARITY_NONE
from sqlitedict import SqliteDict
import baselogger
from connection_handler import ConnectionHandler
from constants import Message, StoreParams, MaintenanceEvents, ErrorEvents, Peripherals
from slave_request_new import Requests
import RPi.GPIO as GPIO
import sys
from local_publish import Publish

# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(12, GPIO.OUT)

GPIO.setwarnings(False)

if GPIO.getmode() is None:
    GPIO.setmode(GPIO.BCM)

GPIO.setup(12, GPIO.OUT)

now = lambda: int(time.time())
datenow = lambda: datetime.datetime.now()

logToFile = True


def readConfig():
    with open('/home/pi/croppico-api-new/config.json', 'r') as c:
        config = json.load(c)
    return config


class SlaveController(Thread):
    def __init__(self, device_id):
        super(SlaveController, self).__init__()
        self.device_id = device_id
        self.__run_controller = False
        self.__ser = Serial('/dev/serial0', 115200, timeout=2.0, parity=PARITY_NONE)
        self.__slave_requests = Requests()
        self.connectionHandler = ConnectionHandler(self.device_id)
        self.messages = Message()
        self.storeparams = StoreParams()
        self.maintenanceevent = MaintenanceEvents()
        self.peripherals = Peripherals()
        self.errorevent = ErrorEvents()
        self.slaveVersion = "00.00"
        self.board_version = "00.00"
        self.store = SqliteDict('./processdata.sqlite', autocommit=True, encode=json.dumps, decode=json.loads)
        print(self.store)
        if logToFile:
            self.logger = baselogger.get_logger('Slave Controller')
            self.logger.info("Initiated...")
        self.light_brightness = 100
        self.brightness_control = GPIO.PWM(12, 100)
        self.connectionHandler.client.on_message = self.cloudMessage
        self.connectionHandler.connect()
        self.localMqtt = Publish()
        self.localMqtt.connect()
        self.__isUserControlling = False
        self.__data = {}
        self.__previousData = {}
        self.__alarm = {}
        self.__settings = {}
        self.__previousAlarm = {}
        self.__lastUpdatedTime = now()
        self.__lastSettingPolledTime = 0
        self.__wasAnySettingUpdated = False
        self.lastUserInputTime = 0
        self.__isMaintenanceActive = False
        self.schLightState = False
        self.peripheralsMaintenanceState = {
            self.peripherals.water_pump: False,
            self.peripherals.water_chiller: False,
            self.peripherals.supplement_ec_pump: False,
            self.peripherals.supplement_ph_inc_pump: False,
            self.peripherals.supplement_ph_dec_pump: False
        }
        self.uartError = False
        self.supplementLevels = {
            "supp_ph_inc": 1,
            "supp_ph_dec": 1,
            "supp_ec_a": 1,
            "supp_ec_b": 1
        }
        self.isComBusy = False
        self.crcErrorCount = 0
        self.wasAlarmError = False
        self.last_updated_timestamp_sqlite = now()
        self.pause_polling = False
        self.start_timer = False
        self.restart_timer = 0
        self.processConfig = readConfig()
        self.program_name = self.processConfig["program_name"]

    def run(self):
        try:
            if logToFile:
                self.logger.info("Started running...")
            self.brightness_control.start(self.light_brightness)
            # self.checkLightSchedule()
            if datetime.time(21, 0, 0) > datetime.time(datenow().hour, datenow().minute,
                                                       datenow().second) > datetime.time(7, 0, 0):
                if logToFile:
                    self.logger.removeHandler(self.logger.handlers[0])
                    self.logger = baselogger.get_logger('Slave Controller')
                self.connectionHandler.re_init_logger()
                print("Turning ON All Lights per schedule")
                self.light_brightness = 100
                self.brightness_control.ChangeDutyCycle(self.light_brightness)
                self.setLightStatus(255, 1)
                self.schLightState = True
            else:
                print("Turning OFF All Lights per schedule")
                self.setLightStatus(255, 0)
                self.light_brightness = 0
                self.brightness_control.ChangeDutyCycle(self.light_brightness)
                self.schLightState = False
            self.__run_controller = True
            time.sleep(0.5)
            self.checkSlaveSettings()
            time.sleep(0.5)
            self.checkSlaveStatus()
            pre = self.__isUserControlling
            # self.getSlaveVersion()
            z = 0
            while self.__run_controller:
                # print(">>",self.lastUserInputTime, self.lastUserInputTime + 5 < now())
                time.sleep(10)
                if self.start_timer:
                    if self.restart_timer + 1500 < now():
                        self.pause_polling = False
                        self.start_timer = False
                        if logToFile: self.logger.info("Poll Restarted by inbuilt timer")
                    else:
                        pass
                if not self.pause_polling:
                    self.checkLightSchedule()
                    if self.__wasAnySettingUpdated:
                        if logToFile: self.logger.info("Updating settings as user is in Home")
                        if not self.isComBusy:
                            self.checkSlaveSettings()
                            time.sleep(0.5)
                        if not self.isComBusy:
                            self.checkSlaveStatus()
                            time.sleep(0.5)
                        self.__wasAnySettingUpdated = False
                    if self.__isUserControlling is False:
                        if pre is not self.__isUserControlling:
                            if logToFile: self.logger.info(
                                "Updating settings as user is in Home using pre" + str(
                                    self.__isUserControlling) + " " + str(
                                    self.lastUserInputTime))
                            self.checkSlaveSettings()
                            pre = self.__isUserControlling
                    if self.__isUserControlling is False:
                        if self.lastUserInputTime + 5 < now():
                            if logToFile: self.logger.info("Is UserControlling... " + str(self.__isUserControlling))
                            # while self.isComBusy: pass
                            # if self.isComBusy: self.__ser.flush()
                            self.checkSlaveStatus()
                            time.sleep(5)
                    else:
                        pre = self.__isUserControlling
                    if self.__lastUpdatedTime + 110 < now():
                        try:
                            pubRes = self.__data.copy()
                            pubRes["timestamp"] = now()
                            resStr = ""
                            if not self.uartError:
                                for i in range(len(self.__data["light_stat"])):
                                    if self.__data["light_stat"][i] == 1:
                                        resStr += "true"
                                    else:
                                        resStr += "false"
                                    resStr += ":"
                                resStr = resStr[:-1]
                                pubRes["light_stat"] = resStr
                                pubRes["light_brightness"] = self.light_brightness
                                self.supplementLevels["supp_ph_inc"] = str(int(not int(pubRes["supp_ph_inc"])))
                                self.supplementLevels["supp_ph_dec"] = str(int(not int(pubRes["supp_ph_dec"])))
                                self.supplementLevels["supp_ec_a"] = str(int(not int(pubRes["supp_ec_a"])))
                                self.supplementLevels["supp_ec_b"] = str(int(not int(pubRes["supp_ec_b"])))
                                self.connectionHandler.publish(self.messages.data, json.dumps(pubRes))
                                # if self.__data["error"] == "1":
                                # pubAlarmRes = None
                                if not self.wasAlarmError:
                                    pubAlarmRes = self.__alarm.copy()
                                    pubAlarmRes.update(self.supplementLevels)
                                    pubAlarmRes["timestamp"] = now()
                                    print("ALARM  : ", pubAlarmRes)
                                    self.connectionHandler.publish(self.messages.alarm, json.dumps(pubAlarmRes))
                                # self.checkCloudMaintenanceControl("ALL")
                                self.store.commit()
                                self.__lastUpdatedTime = now()
                            else:
                                if self.crcErrorCount > 20:
                                    self.connectionHandler.publish(self.messages.error, json.dumps({"uart": "ERROR"}))
                                    self.__data = dict.fromkeys(self.__data, 0)
                                    self.wasAlarmError = True
                        except Exception as e:
                            print("exception occured")
                            print(f"Error: {str(e)}")
        except:
            if logToFile: self.logger.info("exception occured in thread -- Critical")

    def stop(self):
        if logToFile: self.logger.info("Stopped...")
        self.__run_controller = False

    def pollSlave(self, request, need_response=True):
        self.isComBusy = True
        # time.sleep(0.5)
        try:
            self.__ser.flush()
            self.__ser.flushInput()
            self.__ser.flushOutput()
            # while not self.__ser.getCTS() : pass
            # print("PAYLOAD : ", request)
            if logToFile: self.logger.info("PAYLOAD : %s" % request)
            request = self.appendCRC(request)
            # print("SEND : ", request)
            if logToFile: self.logger.info("SEND : %s" % request)
            self.__ser.write(request.encode('utf-8'))
            if need_response:
                response = self.__ser.readline().decode('utf-8').rstrip()
                # print("RECEIVE : ", response)
                if logToFile: self.logger.info("RECEIVE : %s" % response)
                response = ",".join(response.split(",")[0:-1])
                if logToFile: self.logger.info("RECEIVE DD: %s " % response)
                if self.checkCRC(response) is not True:
                    self.uartError = True
                    self.isComBusy = False
                    self.crcErrorCount += 1
                    if logToFile: self.logger.error("CRC invalid")
                    raise ValueError("CRC invalid")
                else:
                    self.uartError = False
                    self.crcErrorCount = 0
                    self.isComBusy = False
                return response
            else:
                return True
        except Exception as exc:
            # print("error while polling:", exc)
            self.uartError = True
            # self.connectionHandler.publish(self.messages.error, json.dumps({"UART": "ERROR "}))
            self.__ser.flush()
            if logToFile: self.logger.error("error while polling slave %s" % exc)
            # if logToFile: self.logger.error("FLUSHING.............................")
            # self.__ser.flushInput()
            # time.sleep(0.2)
            # self.__ser.flushOutput()
            # time.sleep(0.2)
            # self.__ser.flush()
            # time.sleep(0.2)
            # self.__ser.flush()
            # time.sleep(0.2)
            self.isComBusy = False
            return False

    def appendCRC(self, request):
        crcString = request
        MyList = request.split(",")
        strLen = len(MyList)
        crc = 0
        for i in range(0, strLen):
            crc = crc + float(MyList[i])
        crc = crc + 10
        #        crcString = crcString + ',' + str(crc)
        crcString = crcString + ',' + "{:.3f}".format(crc)
        return crcString + "\n"

    def checkCRC(self, response):
        crcString = response
        MyList = response.split(",")
        strLen = len(MyList)
        crc = 0
        for i in range(0, strLen - 1):
            crc = crc + float(MyList[i])
        crc = crc + 10
        rxCRC = MyList[strLen - 1]
        # print(rxCRC , crc)
        if int(float(rxCRC)) == int(crc):
            crcIsValid = True
        else:
            crcIsValid = False
        return crcIsValid

    def getSlaveVersion(self):
        version = self.pollSlave(self.__slave_requests.get_version())
        if version is not False:
            version, board_version = self.__slave_requests.Decode.version(version)
            if version is not False:
                self.slaveVersion = version
                self.board_version = board_version
                return self.slaveVersion, self.board_version
        else:
            return self.slaveVersion, self.board_version

    def checkLightSchedule(self):
        # print("Light", self.schLightState)
        if datetime.time(21, 0, 0) > datetime.time(datenow().hour, datenow().minute, datenow().second) > datetime.time(
                7, 0, 0):
            if not self.schLightState:
                if logToFile: self.logger.removeHandler(self.logger.handlers[0])
                if logToFile: self.logger = baselogger.get_logger('Slave Controller')
                self.connectionHandler.re_init_logger()
                print("Turning ON All Lights per schedule")
                self.light_brightness = 100
                self.brightness_control.ChangeDutyCycle(self.light_brightness)
                self.setLightStatus(255, 1)
            self.schLightState = True
        else:
            if self.schLightState:
                print("Turning OFF All Lights per schedule")
                self.setLightStatus(255, 0)
                self.light_brightness = 0
                self.brightness_control.ChangeDutyCycle(self.light_brightness)
            self.schLightState = False

    def get_debug_data(self):
        ph_debug_data = str(self.pollSlave(self.__slave_requests.get_ph_debug()))
        print(ph_debug_data)
        ec_debug_data = str(self.pollSlave(self.__slave_requests.get_ec_debug()))
        print(ec_debug_data)
        if str(ph_debug_data) is not "False":
            self.localMqtt.publish("CROPPICCO/DEBUG/DEVELOPER/PH/DATA", ph_debug_data)
        if str(ec_debug_data) is not "False":
            self.localMqtt.publish("CROPPICCO/DEBUG/DEVELOPER/EC/DATA", ec_debug_data)

    def checkSlaveStatus(self):
        # time.sleep(1)
        if self.isComBusy: self.__ser.flushInput()
        if logToFile: self.logger.info("Polling slave data")
        decoded_data = self.__slave_requests.Decode.data(self.pollSlave(self.__slave_requests.get_data()))
        if logToFile: self.logger.warn("Decoded Data : " + json.dumps(decoded_data))
        #        self.get_debug_data()
        if decoded_data is not False:
            self.__previousData = self.__data
            decoded_data["light_brightness"] = self.light_brightness
            self.__data = decoded_data
            if decoded_data["ph_inc_pump"] == "1":
                if logToFile: self.logger.info("returning ph inc pump to zero")
                flagchanged = self.pollSlave(self.__slave_requests.put_ph_inc_status())
            if decoded_data["ph_dec_pump"] == "1":
                if logToFile: self.logger.info("returning ph dec pump to zero")
                flagchanged = self.pollSlave(self.__slave_requests.put_ph_dec_status())
            # if self.__data["error"] == "1":
            #     self.logger.error("Alarm Polling Error")
            if logToFile: self.logger.info("saving to sqlite")
            current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.insert_data(current_timestamp, decoded_data["water_pH"], decoded_data["water_ec"],
                             decoded_data["ambient_temp"], decoded_data["water_temperature"],
                             decoded_data["ec_a_pump"], decoded_data["ec_b_pump"], decoded_data["ph_inc_pump"],
                             decoded_data["ph_dec_pump"])
            time.sleep(5)
        else:
            self.__ser.flushInput()
            self.__ser.flushOutput()
            self.__ser.flush()
            self.uartError = True
            self.crcErrorCount += 1
        decoded_alarm = self.__slave_requests.Decode.alarm(self.pollSlave((self.__slave_requests.get_alarm())))
        if logToFile: self.logger.warn("Decoded Alarm : " + json.dumps(decoded_alarm))
        if decoded_alarm is not False:
            self.__previousAlarm = self.__alarm
            self.__alarm = decoded_alarm
            # print(self.__alarm)
            # self.__data["error"] = 0
            self.wasAlarmError = False
        else:
            self.wasAlarmError = True
            self.__ser.flushInput()
            self.__ser.flushOutput()
            self.__ser.flush()
            self.uartError = True
            self.crcErrorCount += 1
            # else:
            #     print("Has alarm")
            #
            # else:
            #     print("not notty decoded")
        time.sleep(1)

    def insert_data(self, timestamp, ph, ec, ambient_temp, water_temp, ec_a_dose, ec_b_dose, ph_up_dose, ph_down_dose):
        if now() - self.last_updated_timestamp_sqlite >= 200:
            conn = sqlite3.connect('/home/pi/croppico-api-new/sensor_data.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sensor_data (
                    timestamp, PH, EC, ambient_temp, water_temp, ec_a_dose, ec_b_dose, ph_up_dose, ph_down_dose
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, ph, ec, ambient_temp, water_temp, ec_a_dose, ec_b_dose, ph_up_dose, ph_down_dose))

            conn.commit()
            conn.close()
            self.last_updated_timestamp_sqlite = now()

    def checkSlaveSettings(self):
        if logToFile: self.logger.info("Polling slave settings")
        settings = self.__slave_requests.Decode.settings((self.pollSlave(self.__slave_requests.get_settings())))
        if logToFile: self.logger.info("Received Settings : " + json.dumps(settings))
        if settings is not False:
            self.__settings = settings
        else:
            time.sleep(1)
            self.checkSlaveSettings()

    def getSettings(self):
        self.__isUserControlling = True
        if logToFile: self.logger.info("User In Settings " + str(self.__isUserControlling))
        # self.checkSlaveSettings()
        self.lastUserInputTime = now()
        return self.__settings

    def getcalibResult(self):
        if logToFile: self.logger.info("getcalibration result")
        isCalibdone = self.__slave_requests.Decode.calibresult(self.pollSlave(self.__slave_requests.get_calib_result()))
        if logToFile: self.logger.info("getcalibration result 33333333" + str(isCalibdone))
        if float(isCalibdone) == 1:
            if logToFile: self.logger.info("returning success")
            flagchanged = self.pollSlave(self.__slave_requests.put_calib_status())
            return True
        if float(isCalibdone) == 2:
            if logToFile: self.logger.info("returning fail")
            flagchanged = self.pollSlave(self.__slave_requests.put_calib_status())
            return "error"

    def getFlushResult(self):
        if logToFile: self.logger.info("get flush result")
        isCalibdone = self.__slave_requests.Decode.calibresult(self.pollSlave(self.__slave_requests.get_flush_result()))
        if logToFile: self.logger.info("get Flush result 33333333" + str(isCalibdone))
        if float(isCalibdone) == 1:
            if logToFile: self.logger.info("returning success")
            print(" flush success, please turn off the system")
            time.sleep(1)
            flagchanged = self.pollSlave(self.__slave_requests.put_flushcalib_status())
            return True
        if float(isCalibdone) == 2:
            if logToFile: self.logger.info("returning fail")
            print("flush fail, please turn off the system")
            time.sleep(1)
            flagchanged = self.pollSlave(self.__slave_requests.put_flushcalib_status())
            return "error"

    def getTopupResult(self):
        if logToFile: self.logger.info("get topup result")
        isCalibdone = self.__slave_requests.Decode.calibresult(self.pollSlave(self.__slave_requests.get_topup_result()))
        if logToFile: self.logger.info("get topup result 33333333" + str(isCalibdone))
        if float(isCalibdone) == 1:
            if logToFile: self.logger.info("returning success")
            print("regular use")
            time.sleep(1)
            flagchanged = self.pollSlave(self.__slave_requests.put_topupcalib_status())
            return True
        if float(isCalibdone) == 2:
            if logToFile: self.logger.info("returning fail")
            print("please try again after sometime, regular use")
            time.sleep(1)
            flagchanged = self.pollSlave(self.__slave_requests.put_topupcalib_status())
            return "error"
        if float(isCalibdone) == 3:
            if logToFile: self.logger.info("check for clog fail")
            print("please check for any clog in the valve and try again, regular use")
            time.sleep(1)
            flagchanged = self.pollSlave(self.__slave_requests.put_topupcalib_status())
            return "clog"

    def putnumberofsolution(self, params):
        if logToFile: self.logger.info("putcalib result check" + str(params))
        if params["solution"] == "ph":
            solution = params["solution"]
            count = params["count"]
            if logToFile: self.logger.info("put number of solution" + str(count))
            # if logToFile: self.logger.info("calibration exit ph" + str(result))
            result = self.pollSlave(self.__slave_requests.Settings.putnumberofsolutionph(count))
            if logToFile: self.logger.info("calibration exit ph" + str(result))
            return True
        if params["solution"] == "ec":
            solution = params["solution"]
            count = int(params["count"])
            result = self.pollSlave(
                self.__slave_requests.Settings.putnumberofsolutionec(count))
            return True

    def getSlaveData(self):
        self.__isUserControlling = False
        # self.checkSlaveStatus()
        return self.__data, self.__alarm
        # return {"data": self.__data, "alarm": self.__alarm}

    def setLightStatus(self, light, state):
        # while self.isComBusy: pass
        #        if self.isComBusy: self.__ser.flushInput()
        #        if self.isComBusy:
        #            print("waiting for serial")
        #            time.sleep(0.4)
        while self.isComBusy: pass
        result = False
        # print(type(light), type(state))
        if light == 0:
            result = self.pollSlave(self.__slave_requests.Lights.set_brightness(state), need_response=False)
            self.light_brightness = state
            self.brightness_control.ChangeDutyCycle(self.light_brightness)
            self.store[self.storeparams.lightbrightness] = state
        elif light == 255:
            result = self.pollSlave((self.__slave_requests.Lights.set_all_lights(state)), need_response=False)
            self.store[self.storeparams.alllights] = state
        else:
            result = self.pollSlave(self.__slave_requests.Lights.set_light(light, state), need_response=True)
            # print(result)
            self.store[self.storeparams.lights(light)] = state
        # print("LIGHT", result)
        # self.logger.info("Lights "+result)
        self.lastUserInputTime = now()
        if logToFile: self.logger.info(">> Pressing light " + str(self.lastUserInputTime))
        # while self.isComBusy: pass
        if self.isComBusy: self.__ser.flushInput()
        time.sleep(0.3)
        # self.checkSlaveStatus()
        return True if result is not False else False

    def checkResult(self, result):
        result = result.split(",")
        if result[0] == "88":
            return True
        else:
            return False

    def poll_pause(self, flag):
        if flag == "true":
            if logToFile: self.logger.info("Poll Paused By UI")
            self.pause_polling = True
            self.start_timer = True
            self.restart_timer = now()
        if flag == "false":
            if logToFile: self.logger.info("Poll Restarted by UI")
            self.start_timer = False
            self.pause_polling = False
        return True

    def setNewSettings(self, stype, params):
        while self.isComBusy: pass
        result = False
        # print(stype, params)
        if stype == "waterpump":
            print('water pump')
            # print("",self.__slave_requests.Settings.set_pump_time(params["ontime"], params["offtime"]))
            if logToFile: self.logger.info("Update water pump settings")
            # print(len(tx), tx)
            result = self.pollSlave(self.__slave_requests.Settings.set_pump_time(params["offtime"], params["ontime"]))
            if logToFile: self.logger.info("maintanence mtype check" + str(result))
            self.store[self.storeparams.settings.water_pump_settings] = params
            self.connectionHandler.publish(self.messages.setting, json.dumps({"water_pump": params}))
        elif stype == "ph":
            print('pH Limits')
            if logToFile: self.logger.info("Update pH settings")
            result = self.pollSlave(
                self.__slave_requests.Settings.set_ph_levels(float(params["phmin"]), float(params["phmax"]),
                                                             float(params["phsensor_setpoint"]),
                                                             float(params["phpump_setpoint"])))
            self.store[self.storeparams.settings.ph_settings] = params
            self.connectionHandler.publish(self.messages.setting, json.dumps({"ph_thresholds": params}))
        elif stype == "ec":
            print('ec limits')
            if logToFile: self.logger.info("Update eC settings")
            result = self.pollSlave(
                self.__slave_requests.Settings.set_ec_levels(int(float(params["ecmin"]) * 1000), params["ecideal"],
                                                             params["ecsensor_setpoint"],
                                                             params["ecpump_setpoint"]))
            self.store[self.storeparams.settings.ec_settings] = params
            self.connectionHandler.publish(self.messages.setting, json.dumps({"ec_thresholds": params}))
        elif stype == "watertemp":
            print('water temp limits')
            if logToFile: self.logger.info("Update water temperature settings")
            result = self.pollSlave(
                self.__slave_requests.Settings.set_water_temperature(params["tempideal"]))
            self.store[self.storeparams.settings.water_temperature_settings] = params
            self.connectionHandler.publish(self.messages.setting, json.dumps({"water_temperature": params}))
        elif stype == "supplementpump":
            print('supplemnet pump times')
            if logToFile: self.logger.info("Update supplement pump settings")
            result = self.pollSlave(
                self.__slave_requests.Settings.set_supplement_pump_time(params["phdose"], params["ecdose"],
                                                                        params["cycle"]))
            self.store[self.storeparams.settings.supplement_pump_settings] = params
            self.connectionHandler.publish(self.messages.setting, json.dumps({"supplement_pump": params}))
        elif stype == "systemsetting":
            print('system type')
            if logToFile: self.logger.info("Update system type settings")
            system_type = params["type"]
            print(type(system_type), system_type)
            result = self.pollSlave(self.__slave_requests.Settings.set_system_type(system_type))
            # self.store[self.storeparams.settings.supplement_pump_settings] = params
            self.connectionHandler.publish(self.messages.setting, json.dumps({"system_type": system_type}))
        elif stype == "calibration":
            if logToFile: self.logger.info("calibration menu" + str(params))
            if params["solution"] == "ph":
                solutionValue = params["value"]
                if logToFile: self.logger.info('ph calibration clicked for value' + str(solutionValue))
                response = self.pollSlave(
                    self.__slave_requests.Settings.set_ph_constant_value(solutionValue), need_response=True)
                if logToFile: self.logger.info("calibration ph" + str(response))
                # doneFlag = False
                # result = True
                # return result
            if params["solution"] == "ec":
                solutionValue = params["value"]
                if logToFile: self.logger.info('ec calibration clicked for value' + str(solutionValue))
                result = self.pollSlave(
                    self.__slave_requests.Settings.set_ec_constant_value(solutionValue), need_response=True)
                if logToFile: self.logger.info("calibration ec" + str(result))
                # return result
            if params["solution"] == "ec_a_pump":
                solutionValue = params["value"]
                if solutionValue:  # send entered value
                    result = self.pollSlave(
                        self.__slave_requests.Settings.set_EC_A_pump_value(solutionValue))
                    if logToFile: self.logger.info("ec a user value" + str(result))
            if params["solution"] == "ec_b_pump":
                solutionValue = params["value"]
                if solutionValue:  # send entered value
                    print('user entered ec b measured value', solutionValue)
                    result = self.pollSlave(
                        self.__slave_requests.Settings.set_EC_B_pump_value(solutionValue))
                    if logToFile: self.logger.info("ec b user value" + str(result))
            if params["solution"] == "flow_sensor":
                solutionValue = params["value"]
                if solutionValue:  # send entered value
                    print('user entered flow pump measured value', solutionValue)
                    # solutionValue = float(solutionValue)
                    # changedvalue = solutionValue * 10
                    result = self.pollSlave(
                        self.__slave_requests.Settings.set_Flow_sensor_value(float(solutionValue) * 10))
                    if logToFile: self.logger.info("flow sensor user value" + str(result))
        self.__wasAnySettingUpdated = True
        self.lastUserInputTime = now()
        time.sleep(2)
        self.checkSlaveSettings()
        print(result)
        return True if result is not False else False

    def restartController(self):
        result = self.pollSlave(self.__slave_requests.restart())
        if logToFile: self.logger.info("Restarting Controller...")
        return True if result is not False else False

    def resetError(self):
        result = self.pollSlave(self.__slave_requests.reseterror())
        if logToFile: self.logger.info("Resetting errors...")
        return True if result is not False else False

    def flush(self, state):
        if state == "start":
            result = self.pollSlave(self.__slave_requests.flush_start())
            if logToFile: self.logger.info("Flush starts...")
            return True if result is not False else False
        if state == "stop":
            result = self.pollSlave(self.__slave_requests.flush_stop())
            if logToFile: self.logger.info("Flush stops...")
            print("restart system to use")
            return True if result is not False else False

    def topup(self, state):
        if state == "start":
            result = self.pollSlave(self.__slave_requests.topup_start())
            if logToFile: self.logger.info("topup starts...")
            return True if result is not False else False
        if state == "stop":
            result = self.pollSlave(self.__slave_requests.topup_stop())
            print("restart system since emergency")
            if logToFile: self.logger.info("topup stops...")
            return True if result is not False else False

    def screen_saver(self, interval_time, status):
        result = self.pollSlave(self.__slave_requests.Settings.put_screensaver(interval_time, status))
        if logToFile: self.logger.info("screensaver settings...")
        self.__wasAnySettingUpdated = True
        self.lastUserInputTime = now()
        self.checkSlaveSettings()
        return True if result is not False else False

    def useracknowledgement(self):
        result = self.pollSlave(self.__slave_requests.useracknowledgement())
        if logToFile: self.logger.info("Resetting errors...")
        return True if result is not False else False

    def model(self):
        result = self.pollSlave(self.__slave_requests.model())
        if logToFile: self.logger.info("Resetting errors...")
        return True if result is not False else False

    def setMaintenanceState(self, state):
        # print(state, self.__isUserControlling)
        print("Maintenance state seting - ", state, self.__isMaintenanceActive)
        while self.isComBusy: pass
        self.__isUserControlling = state
        if self.__isMaintenanceActive != state:
            result = self.pollSlave(
                self.__slave_requests.Maintenance.start() if state else self.__slave_requests.Maintenance.stop()
            )
            self.connectionHandler.publish(self.messages.notification, json.dumps({"Maintainance": state}))
            print("published-----")
            if logToFile: self.logger.info(self.maintenanceevent.status(state))
            self.lastUserInputTime = now()
            self.__isMaintenanceActive = state
            return True if result is not False else False
        return True

    def evalExitMaintenanceMode(self):
        res = True
        for peripheral in self.peripheralsMaintenanceState:
            if self.peripheralsMaintenanceState[peripheral]:
                res = False
        if res:
            self.setMaintenanceState(False)

    def setMaintenanceControl(self, mtype, state, duration):
        result = False
        if not self.__isMaintenanceActive:
            self.setMaintenanceState(True)
        state = int(state)
        duration = int(duration)
        while self.isComBusy: pass
        if mtype == 1:
            print(self.peripherals.water_pump)
            result = self.pollSlave(self.__slave_requests.Maintenance.set_water_pump(state, duration))
            if logToFile: self.logger.info(self.maintenanceevent.water_pump(state))
            self.connectionHandler.publish(self.messages.event,
                                           json.dumps({"event": self.maintenanceevent.water_pump(state)}))
            self.peripheralsMaintenanceState[self.peripherals.water_pump] = bool(state)
        elif mtype == 2:
            print(self.peripherals.water_chiller)
            result = self.pollSlave(self.__slave_requests.Maintenance.set_water_chiller(state, duration))
            if logToFile: self.logger.info(self.maintenanceevent.water_chiller(state))
            self.connectionHandler.publish(self.messages.event,
                                           json.dumps({"event": self.maintenanceevent.water_chiller(state)}))
            self.peripheralsMaintenanceState[self.peripherals.water_chiller] = bool(state)
        elif mtype == 3:
            print(self.peripherals.supplement_ec_pump)
            result = self.pollSlave(self.__slave_requests.Maintenance.set_ec_pump(state, duration))
            if logToFile: self.logger.info(self.maintenanceevent.ec_pump(state))
            self.connectionHandler.publish(self.messages.event,
                                           json.dumps({"event": self.maintenanceevent.ec_pump(state)}))
            self.peripheralsMaintenanceState[self.peripherals.supplement_ec_pump] = bool(state)
        elif mtype == 4:
            print(self.peripherals.supplement_ph_inc_pump)
            result = self.pollSlave(self.__slave_requests.Maintenance.set_ph_inc_pump(state, duration))
            if logToFile: self.logger.info(self.maintenanceevent.ph_inc_pump(state))
            self.connectionHandler.publish(self.messages.event,
                                           json.dumps({"event": self.maintenanceevent.ph_inc_pump(state)}))
            self.peripheralsMaintenanceState[self.peripherals.supplement_ph_inc_pump] = bool(state)
        elif mtype == 5:
            print(self.peripherals.supplement_ph_dec_pump)
            result = self.pollSlave(self.__slave_requests.Maintenance.set_ph_dec_pump(state, duration))
            if logToFile: self.logger.info(self.maintenanceevent.ph_dec_pump(state))
            self.connectionHandler.publish(self.messages.event,
                                           json.dumps({"event": self.maintenanceevent.ph_dec_pump(state)}))
            self.peripheralsMaintenanceState[self.peripherals.supplement_ph_dec_pump] = bool(state)

        # elif mtype == 6:
        # light-brightness

        elif mtype == 7:
            print(self.peripherals.flush_pump)
            result = self.pollSlave(self.__slave_requests.Maintenance.set_flush_pump(state, duration))
            if logToFile: self.logger.info(self.maintenanceevent.flush_pump(state))
            self.connectionHandler.publish(self.messages.event,
                                           json.dumps({"event": self.maintenanceevent.flush_pump(state)}))
            self.peripheralsMaintenanceState[self.peripherals.flush_pump] = bool(state)

        elif mtype == 8:
            print(self.peripherals.topup_pump)
            result = self.pollSlave(self.__slave_requests.Maintenance.set_topup_pump(state, duration))
            if logToFile: self.logger.info(self.maintenanceevent.topup_pump(state))
            if logToFile: self.logger.info("maintanence mtype check" + str(mtype))
            self.connectionHandler.publish(self.messages.event,
                                           json.dumps({"event": self.maintenanceevent.topup_pump(state)}))
            self.peripheralsMaintenanceState[self.peripherals.topup_pump] = bool(state)
        if not state:
            self.evalExitMaintenanceMode()
        # elif mtype == 6:
        #     print(self.peripherals.light_brightness)
        #     self.setLightStatus(state["light"], state["state"])
        #     self.connectionHandler.publish(self.messages.event, self.maintenanceevent.ph_dec_pump(state))
        return True if result is not False else False

    def cloudMessage(self, client, usr, msg):
        if logToFile: self.logger.info("Received downward data : %s" % msg)
        cmType = msg.topic.split("/")[2]
        cmMsg = json.loads(msg.payload)
        if logToFile: self.logger.info("DOWNLINK -----> " + cmType + "   " + json.dumps(cmMsg))
        try:
            if cmType == "maintenance":
                self.processAdhoc(cmMsg)
            if cmType == "reset":
                self.resetError()
                self.connectionHandler.publish(self.messages.event,
                                               json.dumps({"event": "error_reset"}))

            if cmType == "settings":
                ''' {"device_id": "00000000d4ad6605", "water_pump": {"ontime": "20:00",
                "offtime": "90:00"}, "peal": "6"}, "ec_thresholds": {"ecideal": "1.1"},
                "water_temperature": {"tempideal": "25"}, "supplement_pump": {"cycle": 2},
                "program_name": "Salad medleyPH6.0-EC1.1","light_1": false,
                "light_2": false, "light_3": false, "light_4": false, "light_5": true} '''
                if cmMsg["water_pump"]:
                    onT = int(cmMsg["water_pump"]["ontime"].split(":")[0])
                    offT = int(cmMsg["water_pump"]["offtime"].split(":")[0])
                    print(onT, offT)
                    cmMsg["water_pump"]["offtime"] = offT
                    cmMsg["water_pump"]["ontime"] = onT
                    self.setNewSettings("waterpump", cmMsg["water_pump"])
                if cmMsg["ph_thresholds"]:
                    cmMsg["ph_thresholds"]["phmin"] = float(cmMsg["ph_thresholds"]["phideal"]) - 0.3
                    cmMsg["ph_thresholds"]["phmax"] = float(cmMsg["ph_thresholds"]["phideal"]) + 0.3
                    cmMsg["ph_thresholds"]["phideal"] = float(0.2)  # dummy
                    cmMsg["ph_thresholds"]["phsensor_setpoint"] = float(0.5)
                    cmMsg["ph_thresholds"]["phpump_setpoint"] = float(0.1)
                    self.setNewSettings("ph", cmMsg["ph_thresholds"])
                if cmMsg["ec_thresholds"]:
                    cmMsg["ec_thresholds"]["ecmin"] = (float(cmMsg["ec_thresholds"]["ecideal"]))
                    cmMsg["ec_thresholds"]["ecideal"] = int(float(25))  # delta-ui
                    cmMsg["ec_thresholds"]["ecsensor_setpoint"] = int(float(50))
                    cmMsg["ec_thresholds"]["ecpump_setpoint"] = int(float(20))
                    self.setNewSettings("ec", cmMsg["ec_thresholds"])
                if cmMsg["water_temperature"]:
                    # cmMsg["water_temperature"]["tempmax"] = 30  # float(cmMsg["water_temperature"]["tempideal"])+2
                    # cmMsg["water_temperature"]["tempideal"] = 25  # float(cmMsg["water_temperature"]["tempideal"])
                    self.setNewSettings("watertemp", cmMsg["water_temperature"])
                if cmMsg["supplement_pump"]:
                    cmMsg["supplement_pump"]["ecdose"] = 1
                    cmMsg["supplement_pump"]["phdose"] = 1
                    cmMsg["supplement_pump"]["cycle"] = int(cmMsg["supplement_pump"]["cycle"]) * (20 + 90)
                    self.setNewSettings("supplementpump", cmMsg["supplement_pump"])
                if cmMsg["program_name"]:
                    print("updating program name -------------------->")
                    with open("/home/pi/croppico-api-new/config.json", 'w') as f:
                        self.processConfig["program_name"] = cmMsg["program_name"]
                        json.dump(self.processConfig, f, indent=4)
                    self.program_name = cmMsg["program_name"]
        except Exception as e:
            if logToFile: self.logger.error("Error in Downlink Message", e)

    def processAdhoc(self, cmMsg):
        # while self.isComBusy: pass
        if logToFile:
            self.logger.info(json.dumps(cmMsg))
            # self.logger.info(type(cmMsg))
        while self.isComBusy: pass
        self.setMaintenanceState(True)
        if "water_pump" in cmMsg:
            if len(cmMsg["water_pump"].split(":")) == 2:
                wptime = int(cmMsg["water_pump"].split(":")[0]) * 60 + int(cmMsg["water_pump"].split(":")[1])
                if logToFile:
                    self.logger.info("water pump turned ON for - " + str(wptime) + "seconds")
                if wptime is not 0:
                    print("------------------->", wptime)
                    self.setMaintenanceControl(self.peripherals.getCode(self.peripherals.water_pump), True, wptime)
                    wpt = Timer(wptime, self.setMaintenanceControl,
                                (self.peripherals.getCode(self.peripherals.water_pump), False, wptime))
                    wpt.start()
        if "water_temperature_time" in cmMsg:
            if len(cmMsg["water_temperature_time"].split(":")) == 2:
                wtttime = int(cmMsg["water_temperature_time"].split(":")[0]) * 60 + int(
                    cmMsg["water_temperature_time"].split(":")[1])
                if logToFile:
                    self.logger.info("chiller turned ON for - " + str(wtttime) + "seconds")
                if wtttime is not 0:
                    self.setMaintenanceControl(self.peripherals.getCode(self.peripherals.water_chiller), True, wtttime)
                    wtt = Timer(wtttime, self.setMaintenanceControl,
                                (self.peripherals.getCode(self.peripherals.water_chiller), False, wtttime))
                    wtt.start()
        if "ec_pump" in cmMsg:
            if len(cmMsg["ec_pump"].split(":")) == 2:
                ecptime = int(cmMsg["ec_pump"].split(":")[0]) * 60 + int(cmMsg["ec_pump"].split(":")[1])
                if logToFile:
                    self.logger.info("EC-pump turned ON for - " + str(ecptime) + "seconds")
                if ecptime is not 0:
                    check = self.peripherals.getCode(self.peripherals.supplement_ec_pump)
                    if logToFile: self.logger.info("maintanence adhoc check" + str(check))
                    self.setMaintenanceControl(self.peripherals.getCode(self.peripherals.supplement_ec_pump), True,
                                               ecptime)
                    ect = Timer(ecptime, self.setMaintenanceControl,
                                (self.peripherals.getCode(self.peripherals.supplement_ec_pump), False, ecptime))
                    ect.start()
        if "flush_pump" in cmMsg:
            if len(cmMsg["flush_pump"].split(":")) == 2:
                flushptime = int(cmMsg["flush_pump"].split(":")[0]) * 60 + int(cmMsg["flush_pump"].split(":")[1])
                if logToFile:
                    self.logger.info("FLUSH-pump turned ON for - " + str(flushptime) + "seconds")
                if flushptime is not 0:
                    self.setMaintenanceControl(self.peripherals.getCode(self.peripherals.flush_pump), True, flushptime)
                    flusht = Timer(flushptime, self.setMaintenanceControl,
                                   (self.peripherals.getCode(self.peripherals.flush_pump), False, flushptime))
                    flusht.start()
        if "topup_pump" in cmMsg:
            if len(cmMsg["topup_pump"].split(":")) == 2:
                topupptime = int(cmMsg["topup_pump"].split(":")[0]) * 60 + int(cmMsg["topup_pump"].split(":")[1])
                if logToFile:
                    self.logger.info("TOPUP-pump turned ON for - " + str(topupptime) + "seconds")
                if topupptime is not 0:
                    check = self.peripherals.getCode(self.peripherals.topup_pump)
                    if logToFile: self.logger.info("maintanence adhoc check" + str(check))
                    self.setMaintenanceControl(self.peripherals.getCode(self.peripherals.topup_pump), True, topupptime)
                    ecbt = Timer(topupptime, self.setMaintenanceControl,
                                 (self.peripherals.getCode(self.peripherals.topup_pump), False, topupptime))
                    ecbt.start()
        if "ph_inc_pump" in cmMsg:
            if len(cmMsg["ph_inc_pump"].split(":")) == 2:
                piptime = int(cmMsg["ph_inc_pump"].split(":")[0]) * 60 + int(cmMsg["ph_inc_pump"].split(":")[1])
                if logToFile:
                    self.logger.info("pH_inc-pump turned ON for - " + str(piptime) + "seconds")
                if piptime is not 0:
                    self.setMaintenanceControl(self.peripherals.getCode(self.peripherals.supplement_ph_inc_pump), True,
                                               piptime)
                    pit = Timer(piptime, self.setMaintenanceControl,
                                (self.peripherals.getCode(self.peripherals.supplement_ph_inc_pump), False, piptime))
                    pit.start()
        if "ph_decc_pump" in cmMsg:
            if len(cmMsg["ph_decc_pump"].split(":")) == 2:
                pdptime = int(cmMsg["ph_decc_pump"].split(":")[0]) * 60 + int(cmMsg["ph_decc_pump"].split(":")[1])
                if logToFile:
                    self.logger.info("pH_dec-pump turned ON for - " + str(pdptime) + "seconds")
                if pdptime is not 0:
                    self.setMaintenanceControl(self.peripherals.getCode(self.peripherals.supplement_ph_dec_pump), True,
                                               pdptime)
                    pdt = Timer(pdptime, self.setMaintenanceControl,
                                (self.peripherals.getCode(self.peripherals.supplement_ph_dec_pump), False, pdptime))
                    pdt.start()
        if "light_1" in cmMsg:
            if len(cmMsg["light_1"]["duration"].split(":")) == 2:
                l1ttime = int(cmMsg["light_1"]["duration"].split(":")[0]) * 60 + int(
                    cmMsg["light_1"]["duration"].split(":")[1])
                if l1ttime is not 0:
                    self.evalExitMaintenanceMode()
                    if cmMsg["light_1"]["status"]:
                        self.setLightStatus(1, 1)
                        l1t = Timer(l1ttime, self.setLightStatus, (1, 0))
                        l1t.start()
                        if logToFile:
                            self.logger.info("light_1 turned ON for - " + str(l1ttime) + "seconds")
                    if not cmMsg["light_1"]["status"]:
                        self.setLightStatus(1, 0)
                        l1t = Timer(l1ttime, self.setLightStatus, (1, 1))
                        l1t.start()
                        if logToFile:
                            self.logger.info("light_1 turned OFF for - " + str(l1ttime) + "seconds")
        if "light_2" in cmMsg:
            if len(cmMsg["light_2"]["duration"].split(":")) == 2:
                l2ttime = int(cmMsg["light_2"]["duration"].split(":")[0]) * 60 + int(
                    cmMsg["light_2"]["duration"].split(":")[1])
                if l2ttime:
                    self.evalExitMaintenanceMode()
                    if cmMsg["light_2"]["status"]:
                        self.setLightStatus(2, 1)
                        l2t = Timer(l2ttime, self.setLightStatus, (2, 0))
                        l2t.start()
                        if logToFile:
                            self.logger.info("light_2 turned ON for - " + str(l2ttime) + "seconds")
                    if not cmMsg["light_2"]["status"]:
                        self.setLightStatus(2, 0)
                        l2t = Timer(l2ttime, self.setLightStatus, (2, 1))
                        l2t.start()
                        if logToFile:
                            self.logger.info("light_2 turned OFF for - " + str(l2ttime) + "seconds")
        if "light_3" in cmMsg:
            if len(cmMsg["light_3"]["duration"].split(":")) == 2:
                l3ttime = int(cmMsg["light_3"]["duration"].split(":")[0]) * 60 + int(
                    cmMsg["light_3"]["duration"].split(":")[1])
                if l3ttime:
                    self.evalExitMaintenanceMode()
                    if cmMsg["light_3"]["status"]:
                        self.setLightStatus(3, 1)
                        l3t = Timer(l3ttime, self.setLightStatus, (3, 0))
                        l3t.start()
                        if logToFile:
                            self.logger.info("light_3 turned ON for - " + str(l3ttime) + "seconds")
                    if not cmMsg["light_3"]["status"]:
                        self.setLightStatus(3, 0)
                        l3t = Timer(l3ttime, self.setLightStatus, (3, 1))
                        l3t.start()
                        if logToFile:
                            self.logger.info("light_3 turned OFF for - " + str(l3ttime) + "seconds")
        if "light_4" in cmMsg:
            if len(cmMsg["light_4"]["duration"].split(":")) == 2:
                l4ttime = int(cmMsg["light_4"]["duration"].split(":")[0]) * 60 + int(
                    cmMsg["light_4"]["duration"].split(":")[1])
                if l4ttime:
                    self.evalExitMaintenanceMode()
                    if cmMsg["light_4"]["status"]:
                        self.setLightStatus(4, 1)
                        l4t = Timer(l4ttime, self.setLightStatus, (4, 0))
                        l4t.start()
                        if logToFile:
                            self.logger.info("light_4 turned ON for - " + str(l4ttime) + "seconds")
                    if not cmMsg["light_4"]["status"]:
                        self.setLightStatus(4, 0)
                        l4t = Timer(l4ttime, self.setLightStatus, (4, 1))
                        l4t.start()
                        if logToFile:
                            self.logger.info("light_4 turned OFF for - " + str(l4ttime) + "seconds")
        if "light_5" in cmMsg:
            if len(cmMsg["light_5"]["duration"].split(":")) == 2:
                l5ttime = int(cmMsg["light_5"]["duration"].split(":")[0]) * 60 + int(
                    cmMsg["light_5"]["duration"].split(":")[1])
                if l5ttime:
                    self.evalExitMaintenanceMode()
                    if cmMsg["light_5"]["status"]:
                        self.setLightStatus(5, 1)
                        l5t = Timer(l5ttime, self.setLightStatus, (5, 0))
                        l5t.start()
                        if logToFile:
                            self.logger.info("light_5 turned ON for - " + str(l5ttime) + "seconds")
                    if not cmMsg["light_5"]["status"]:
                        self.setLightStatus(5, 0)
                        l5t = Timer(l5ttime, self.setLightStatus, (5, 1))
                        l5t.start()
                        if logToFile:
                            self.logger.info("light_5 turned OFF for - " + str(l5ttime) + "seconds")
        if "light_brightness_time" in cmMsg:
            if len(cmMsg["light_brightness_time"].split(":")) == 2:
                lbttime = int(cmMsg["light_brightness_time"].split(":")[0]) * 60 + int(
                    cmMsg["light_brightness_time"].split(":")[1])
                if lbttime:
                    self.evalExitMaintenanceMode()
                    if logToFile:
                        self.logger.info("lightbrightness time - " + str(lbttime) + "seconds")
                    btlev = int(cmMsg["light_brightness"])
                    if logToFile:
                        self.logger.info("lightbrightness  - " + str(btlev))
                    curBtlev = self.light_brightness
                    self.setLightStatus(0, btlev)
                    lbtt = Timer(lbttime, self.setLightStatus, (0, curBtlev))
                    lbtt.start()
            # >> > now = lambda: datetime.datetime.now()
            # >> > now()
            # datetime.datetime(2022, 5, 24, 16, 15, 13, 114808)
            # >> > k > datetime.time(now().hour, now().minute)
            # True
            # >> > k < datetime.time(now().hour, now().minute)
            # False
            # >> > datetime.time(21, 0, 0) > datetime.time(now().hour, now().minute, now().second) > datetime.time(7, 0,
            #                                                                                                      0)
            # True
            # >> > datetime.time(21, 0, 0) > datetime.time(now().hour, now().minute, now().second) > datetime.time(7, 0,
            #                                                                                                      0)
            # True
            # >> > datetime.time(21, 0, 0) > datetime.time(now().hour, now().minute, now().second) > datetime.time(7, 0,
            #  