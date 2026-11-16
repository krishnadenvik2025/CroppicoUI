import RPi.GPIO as GPIO
import time,subprocess

device = "/dev/ttyAMA0"
# device = "/dev/ttyUSB0"

def update_firmware(device):
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

    flash_arg = ("/home/pi/stm-bootloader/git/stm32flash/stm32flash", "-b", "115200", "-v", "-w",
                "/home/pi/stm-bootloader/latest_firmware/firmware.bin", device)

    flash = subprocess.call('%s %s %s %s %s %s %s' % flash_arg, shell=True)
    time.sleep(2)
    if flash != 0:
        print(f"Failed: stm32flash returned {flash}")
    print("Programming Done - Releasing Bootloader")

    GPIO.output(20,GPIO.LOW)
    GPIO.output(21,GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(21,GPIO.LOW)