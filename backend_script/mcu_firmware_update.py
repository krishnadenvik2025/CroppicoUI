import RPi.GPIO as GPIO
import time,subprocess

device = "/dev/ttyAMA0"
# device = "/dev/ttyUSB0"

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(20,GPIO.OUT)
GPIO.setup(21,GPIO.OUT)

print("Inside bootloader")
GPIO.output(20,GPIO.LOW)
time.sleep(0.2)
GPIO.output(20,GPIO.HIGH)
time.sleep(2)
GPIO.output(21,GPIO.HIGH)
time.sleep(0.2)
GPIO.output(21,GPIO.LOW)
time.sleep(0.2)
GPIO.output(20,GPIO.LOW)

print("Programming Started")
# intoDir_Arg = ("cd", "/home/pi/stm-bootloader/git/stm32flash/")
# intoDir = subprocess.call('%s %s' % intoDir_Arg, shell=True)
# flash_arg = ("./stm32flash", "-b", "115200", "-v", "-w", "/home/pi/stm-bootloader/4.bin/dev/ttyUSB0")
# flash_arg = ("/home/pi/stm-bootloader/git/stm32flash/stm32flash", "-b", "115200", "-v", "-w",
#              "/home/pi/stm-bootloader/firmware.bin", "/dev/ttyAMA0")

flash_arg = ("/home/pi/stm-bootloader/git/stm32flash/stm32flash", "-b", "115200", "-v", "-w",
             "/home/pi/stm-bootloader/latest_firmware/firmware.bin", device)

flash = subprocess.call('%s %s %s %s %s %s %s' % flash_arg, shell=True)
time.sleep(2)
print("Programming Done - Releasing Bootloader")

GPIO.output(20,GPIO.LOW)
GPIO.output(21,GPIO.HIGH)
time.sleep(0.2)
GPIO.output(21,GPIO.LOW)