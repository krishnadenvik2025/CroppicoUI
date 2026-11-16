import os, sys, time, getpass, paramiko

BASE_DIR = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__)))

SERVICE = "cropicco-api.service"
APP_DIR = "/home/pi/croppico-api-new"
WEB_DIR = "/var/www/html"
KEEP = ["config.json", "processdata.sqlite", "sensor_data.db"]
MCU_DIR = "/home/pi/stm-bootloader"
MCU_SCRIPT = f"{MCU_DIR}/mcu_update.py"
FW_DIR = f"{MCU_DIR}/latest_firmware"
FW_PATH = f"{FW_DIR}/firmware.bin"
STM32FLASH = f"{MCU_DIR}/git/stm32flash/stm32flash"
SERIAL_PORTS = ["/dev/ttyAMA0", "/dev/ttyUSB0"]

def remote_exists(ssh, path):
    _, stdout, _ = ssh.exec_command(f"test -e '{path}'")
    return stdout.channel.recv_exit_status() == 0

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    if code != 0:
        raise RuntimeError(f"'{cmd}' failed ({code}): {err.strip()}")
    return out

def upload(ssh, local, remote):
    sftp = ssh.open_sftp()
    try:
        sftp.put(local, remote)
    finally:
        sftp.close()

def choose_serial_port(ssh):
    print("\nSelect the serial port connected to the MCU:")
    status = {}
    for i, port in enumerate(SERIAL_PORTS, 1):
        status[i] = remote_exists(ssh, port)
        print(f"  {i}. {port}" + ("" if status[i] else "  (not found on device)"))
    print("  0. Cancel")
    while True:
        try:
            n = int(input("Enter choice: "))
        except ValueError:
            print("Please enter a number.")
            continue
        if n == 0:
            return None
        if n in status:
            if status[n]:
                return SERIAL_PORTS[n - 1]
            print(f"{SERIAL_PORTS[n - 1]} does not exist on the device. Pick another.")
        else:
            print("Invalid choice.")

def system_update_ui(ssh, zip_name="croppico_ui.zip"):
    local_zip = os.path.join(BASE_DIR, zip_name)
    base = "/home/pi/ui_backups"
    cur, prv = f"{base}/cur_ui", f"{base}/prv_ui"
    try:
        if not os.path.exists(local_zip):
            print(f"[ERROR] '{zip_name}' not found in {BASE_DIR}")
            return False
        print("Initializing UI update process")
        run(ssh, f"mkdir -p {cur} {prv}")

        print("Uploading new UI")
        upload(ssh, local_zip, f"{cur}/croppico-ui.zip")

        print("Extracting new UI")
        run(ssh, f"rm -rf {cur}/html && unzip -oq {cur}/croppico-ui.zip -d {cur}")
        run(ssh, f"test -f {cur}/html/index.html")

        print("Taking backup of current UI")
        run(ssh, f"rm -rf {prv}/html && cp -a {WEB_DIR} {prv}/html")

        print("Replacing UI")
        run(ssh, f"sudo find {WEB_DIR} -mindepth 1 -delete && sudo cp -a {cur}/html/. {WEB_DIR}/")

        print("Done...")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def system_update_backend(ssh, zip_name="script.zip"):
    local_zip = os.path.join(BASE_DIR, zip_name)
    base = "/home/pi/backend_backups"
    cur, prv = f"{base}/cur_backend", f"{base}/prv_backend"
    top = "croppico-api-new"
    stopped = False
    try:
        if not os.path.exists(local_zip):
            print(f"[ERROR] '{zip_name}' not found in {BASE_DIR}")
            return False
        print("Initializing backend update process")
        run(ssh, f"mkdir -p {cur} {prv}")

        print("Uploading new backend")
        upload(ssh, local_zip, f"{cur}/script.zip")

        print("Extracting new backend")
        excludes = " ".join(f"'{top}/{f}'" for f in KEEP) + f" '{top}/__pycache__/*'"
        run(ssh, f"rm -rf {cur}/{top} && unzip -oq {cur}/script.zip -x {excludes} -d {cur}")
        run(ssh, f"test -f {cur}/{top}/main.py") 

        print("Taking backup of current backend")
        run(ssh, f"sudo rm -rf {prv}/{top} && sudo cp -a {APP_DIR} {prv}/{top}")

        print("Stopping service")
        run(ssh, f"sudo systemctl stop {SERVICE}")
        stopped = True

        print("Replacing backend (database and config are preserved)")
        run(ssh, f"sudo chown -R pi:pi {APP_DIR}")
        keep = " ".join(f"! -name '{f}'" for f in KEEP)
        run(ssh, f"find {APP_DIR} -mindepth 1 -maxdepth 1 {keep} -exec rm -rf {{}} +")
        run(ssh, f"cp -a {cur}/{top}/. {APP_DIR}/")
        run(ssh, f"sudo chown -R pi:pi {APP_DIR}")
        run(ssh, f"python3 -m pip install -r {APP_DIR}/requirements.txt")

        print("Done")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if stopped:
            print("Starting service....")
            try:
                run(ssh, f"sudo systemctl start {SERVICE}")
            except Exception as e:
                print(f"Failed to start service: {e}")

def system_update_firmware(ssh, fw_name="firmware.bin", script_name="mcu_update.py"):
    local_fw = os.path.join(BASE_DIR, fw_name)
    local_script = os.path.join(BASE_DIR, script_name)
    stopped = False
    try:
        if not os.path.exists(local_fw) or os.path.getsize(local_fw) == 0:
            print(f"[ERROR] '{fw_name}' not found (or empty) in {BASE_DIR}")
            return False

        if not remote_exists(ssh, STM32FLASH):
            print(f"[ERROR] stm32flash not found on the device at {STM32FLASH}")
            return False

        run(ssh, f"sudo mkdir -p '{FW_DIR}' && sudo chown pi:pi '{MCU_DIR}' '{FW_DIR}'")
        run(ssh, f"[ ! -e '{FW_PATH}' ] || sudo chown pi:pi '{FW_PATH}'")

        if remote_exists(ssh, MCU_SCRIPT):
            print("mcu_update.py found on device.")
        else:
            print("mcu_update.py not found on device. Uploading...")
            if not os.path.exists(local_script):
                print(f"[ERROR] '{script_name}' not found in {BASE_DIR}")
                return False
            upload(ssh, local_script, MCU_SCRIPT)

        print("Deleting existing firmware.bin")
        run(ssh, f"sudo rm -f '{FW_PATH}'")

        print("Uploading firmware.bin...")
        upload(ssh, local_fw, FW_PATH)
        remote_size = run(ssh, f"stat -c %s '{FW_PATH}'").strip()
        if remote_size != str(os.path.getsize(local_fw)):
            print("[ERROR] Uploaded firmware size does not match. Aborting.")
            return False
        print("Firmware uploaded and verified.")

        # --- user confirmation ---
        device = choose_serial_port(ssh)
        if device is None:
            print("Cancelled. Nothing was flashed.")
            return False
        print(f"\nReady to flash {fw_name} to the MCU via {device}.")
        print("Do NOT power off or disconnect the device while flashing.")
        if input("Continue? (y/N): ").strip().lower() != "y":
            print("Cancelled. Nothing was flashed.")
            return False

        # --- stop service (it uses the serial port) ---
        print("Stopping service...")
        run(ssh, f"sudo systemctl stop {SERVICE}")
        stopped = True

        # --- call update_firmware(device) ---
        print("Flashing MCU...")
        cmd = (f"sudo python3 -c \"import sys; sys.path.insert(0, '{MCU_DIR}'); "
               f"import mcu_update; mcu_update.update_firmware('{device}')\" 2>&1")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
        out = stdout.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        print(out)

        low = out.lower()
        if code != 0 or "failed" in low or "error" in low:
            print("------ [ERROR] Firmware update failed. ------")
            return False
        if "100.00%" in out:
            print("------ [SUCCESS] Firmware update completed successfully. ------")
            return True
        print("------ [WARNING] Result unclear. Please verify manually. ------")
        return False

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if stopped:
            print("Starting service...")
            try:
                run(ssh, f"sudo systemctl start {SERVICE}")
            except Exception as e:
                print(f"Failed to start service: {e}")

def main():
    ssh = None
    try:
        print("\n=== Cropicco Firmware Updater ===")
        print("Before you continue:")
        print("  1. Connect this PC to the same Wi-Fi/LAN as the Cropicco device.")
        print("  2. Make sure the device is powered on.")
        print("  3. Enter the device's IP address (for example: 192.168.1.90).\n")
        ip = input("Device IP address: ").strip()
        if not ip:
            print("IP address is required.")
            return
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, 22, "pi", "!@#$%^&*()@123", timeout=10,
                    look_for_keys=False, allow_agent=False)

        print("Choose an option:\n1. Backend firmware Update\n2. UI Update\n3. MCU firmware Update\n4. Exit")
        try:
            choice = int(input("Enter Your Choice (1-4): "))
        except ValueError:
            print("Invalid choice. Please enter a number between 1 and 3.")
            return

        if choice == 1:
            system_update_backend(ssh)
        elif choice == 2:
            if system_update_ui(ssh):
                print("System will be restarted in 5 seconds....")
                for i in range(1, 6):
                    print(i)
                    time.sleep(1)
                try:
                    ssh.exec_command("sudo reboot")
                    time.sleep(2)
                except Exception:
                    pass

        elif choice == 3:
            system_update_firmware(ssh)
        elif choice == 4:
            print("Exiting...")
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")

    except paramiko.AuthenticationException:
        print("Authentication failed. Check the password.")
    except Exception as e:
        print(f"Connection/Error: {e}")
    finally:
        if ssh:
            ssh.close()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()