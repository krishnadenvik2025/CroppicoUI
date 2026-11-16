import os
import sys
import time
import socket
import getpass
import ipaddress
import zipfile

import paramiko

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
BASE_DIR = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__)))

SSH_USER = "pi"
# Password is asked at runtime. For unattended use, set CROPICCO_PW in the
# environment instead of hardcoding it in the exe.
SSH_PASSWORD_ENV = "CROPICCO_PW"

SERVICE = "cropicco-api.service"

APP_DIR = "/home/pi/croppico-api-new"
APP_TOP = "croppico-api-new"          # top-level folder inside script.zip
WEB_DIR = "/var/www/html"
WEB_TOP = "html"                      # top-level folder inside croppico_ui.zip

# Files on the Pi that must survive a backend update (never overwritten/deleted)
KEEP = ["config.json", "processdata.sqlite", "sensor_data.db"]

MCU_DIR = "/home/pi/stm-bootloader"
MCU_SCRIPT = f"{MCU_DIR}/mcu_update.py"
FW_DIR = f"{MCU_DIR}/latest_firmware"
FW_PATH = f"{FW_DIR}/firmware.bin"
STM32FLASH = f"{MCU_DIR}/git/stm32flash/stm32flash"
SERIAL_PORTS = ["/dev/ttyAMA0", "/dev/ttyUSB0"]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def run(ssh, cmd, timeout=120):
    """Run a command on the Pi. Raise RuntimeError if it exits non-zero."""
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")      # read BEFORE waiting
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    if code != 0:
        raise RuntimeError(f"'{cmd}' failed ({code}): {err.strip() or out.strip()}")
    return out


def remote_exists(ssh, path):
    _, stdout, _ = ssh.exec_command(f"test -e '{path}'")
    return stdout.channel.recv_exit_status() == 0


def upload(ssh, local, remote):
    """Upload a file with a simple progress indicator and size verification."""
    total = os.path.getsize(local)
    last = {"pct": -1}

    def progress(done, size):
        pct = int(done * 100 / size) if size else 100
        if pct != last["pct"] and pct % 10 == 0:
            print(f"  uploading... {pct}%")
            last["pct"] = pct

    sftp = ssh.open_sftp()
    try:
        sftp.put(local, remote, callback=progress)
    finally:
        sftp.close()

    remote_size = run(ssh, f"stat -c %s '{remote}'").strip()
    if remote_size != str(total):
        raise RuntimeError(f"Upload verification failed for {os.path.basename(local)} "
                           f"(local {total} bytes, remote {remote_size} bytes)")


def check_local_zip(path, required_member):
    """Make sure the zip exists, is valid, and contains the expected file."""
    if not os.path.exists(path):
        print(f"[ERROR] '{os.path.basename(path)}' not found in {BASE_DIR}")
        return False
    try:
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                print(f"[ERROR] '{os.path.basename(path)}' is corrupted.")
                return False
            if required_member not in z.namelist():
                print(f"[ERROR] '{os.path.basename(path)}' does not contain '{required_member}'. "
                      "Wrong zip or wrong folder structure.")
                return False
    except zipfile.BadZipFile:
        print(f"[ERROR] '{os.path.basename(path)}' is not a valid zip file.")
        return False
    return True


def clear_except(ssh, path, keep=()):
    """Delete everything inside `path`, except the names listed in `keep`."""
    keep_expr = " ".join(f"! -name '{k}'" for k in keep)
    run(ssh, f"sudo find '{path}' -mindepth 1 -maxdepth 1 {keep_expr} -exec rm -rf {{}} +")


def start_service_and_verify(ssh):
    """Start the service and confirm it stays active."""
    run(ssh, f"sudo systemctl start {SERVICE}")
    time.sleep(3)
    _, stdout, _ = ssh.exec_command(f"systemctl is-active {SERVICE}")
    state = stdout.read().decode().strip()
    return state == "active"


def ask_ip():
    print("\n=== Cropicco Firmware Updater ===")
    print("Before you continue:")
    print("  1. Connect this PC to the same Wi-Fi/LAN as the Cropicco device.")
    print("  2. Make sure the device is powered on.")
    print("  3. Enter the device's IP address (for example: 192.168.1.90).\n")
    while True:
        ip = input("Device IP address (or 'q' to quit): ").strip()
        if ip.lower() == "q":
            return None
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            print("Invalid IP address. Please enter it like 192.168.1.90\n")


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


# ----------------------------------------------------------------------------
# UI update
# ----------------------------------------------------------------------------
def system_update_ui(ssh, zip_name="croppico_ui.zip"):
    local_zip = os.path.join(BASE_DIR, zip_name)
    base = "/home/pi/ui_backups"
    cur, prv = f"{base}/cur_ui", f"{base}/prv_ui"
    swapped = False
    try:
        if not check_local_zip(local_zip, f"{WEB_TOP}/index.html"):
            return False

        print("Initializing UI update process")
        run(ssh, f"mkdir -p {cur} {prv}")

        print("Uploading new UI")
        upload(ssh, local_zip, f"{cur}/croppico-ui.zip")

        print("Extracting new UI")
        run(ssh, f"rm -rf {cur}/{WEB_TOP} && unzip -oq {cur}/croppico-ui.zip -d {cur}")
        run(ssh, f"test -f {cur}/{WEB_TOP}/index.html")

        print("Taking backup of current UI")
        run(ssh, f"sudo rm -rf {prv}/{WEB_TOP} && sudo cp -a {WEB_DIR} {prv}/{WEB_TOP}")

        print("Replacing UI")
        owner = run(ssh, f"stat -c %U:%G {WEB_DIR}").strip()     # keep original owner
        swapped = True
        clear_except(ssh, WEB_DIR)
        run(ssh, f"sudo cp -a {cur}/{WEB_TOP}/. {WEB_DIR}/")
        run(ssh, f"sudo chown -R {owner} {WEB_DIR}")
        run(ssh, f"test -f {WEB_DIR}/index.html")

        print("UI update done.")
        return True

    except Exception as e:
        print(f"Error: {e}")
        if swapped:
            print("Rolling back to the previous UI...")
            try:
                clear_except(ssh, WEB_DIR)
                run(ssh, f"sudo cp -a {prv}/{WEB_TOP}/. {WEB_DIR}/")
                print("Rollback complete.")
            except Exception as e2:
                print(f"[ERROR] Rollback failed: {e2}. Previous UI is at {prv}/{WEB_TOP}")
        return False


# ----------------------------------------------------------------------------
# Backend update
# ----------------------------------------------------------------------------
def system_update_backend(ssh, zip_name="script.zip"):
    local_zip = os.path.join(BASE_DIR, zip_name)
    base = "/home/pi/backend_backups"
    cur, prv = f"{base}/cur_backend", f"{base}/prv_backend"
    stopped = False
    swapped = False
    ok = False
    try:
        if not check_local_zip(local_zip, f"{APP_TOP}/main.py"):
            return False

        print("Initializing backend update process")
        run(ssh, f"mkdir -p {cur} {prv}")

        print("Uploading new backend")
        upload(ssh, local_zip, f"{cur}/script.zip")

        print("Extracting new backend")
        excludes = " ".join(f"'{APP_TOP}/{f}'" for f in KEEP) + f" '{APP_TOP}/__pycache__/*'"
        run(ssh, f"rm -rf {cur}/{APP_TOP} && unzip -oq {cur}/script.zip -x {excludes} -d {cur}")
        run(ssh, f"test -f {cur}/{APP_TOP}/main.py")

        print("Taking backup of current backend")
        run(ssh, f"sudo rm -rf {prv}/{APP_TOP} && sudo cp -a {APP_DIR} {prv}/{APP_TOP}")

        print("Stopping service")
        run(ssh, f"sudo systemctl stop {SERVICE}")
        stopped = True

        print("Replacing backend (database and config are preserved)")
        swapped = True
        run(ssh, f"sudo chown -R {SSH_USER}:{SSH_USER} {APP_DIR}")
        clear_except(ssh, APP_DIR, KEEP)
        run(ssh, f"cp -a {cur}/{APP_TOP}/. {APP_DIR}/")
        run(ssh, f"sudo chown -R {SSH_USER}:{SSH_USER} {APP_DIR}")

        print("Starting service...")
        if not start_service_and_verify(ssh):
            raise RuntimeError("Service did not start with the new backend.")
        stopped = False
        ok = True
        print("Backend update done. Service is running.")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        if not ok and swapped:
            print("Rolling back to the previous backend...")
            try:
                run(ssh, f"sudo chown -R {SSH_USER}:{SSH_USER} {APP_DIR}")
                clear_except(ssh, APP_DIR, KEEP)
                run(ssh, f"sudo cp -a {prv}/{APP_TOP}/. {APP_DIR}/")
                print("Rollback complete.")
            except Exception as e2:
                print(f"[ERROR] Rollback failed: {e2}. Previous backend is at {prv}/{APP_TOP}")
        if not ok and (stopped or swapped):
            print("Restarting service...")
            try:
                run(ssh, f"sudo systemctl start {SERVICE}")
            except Exception as e3:
                print(f"[ERROR] Failed to start service: {e3}")


# ----------------------------------------------------------------------------
# MCU firmware update
# ----------------------------------------------------------------------------
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

        run(ssh, f"sudo mkdir -p '{FW_DIR}' && sudo chown {SSH_USER}:{SSH_USER} '{MCU_DIR}' '{FW_DIR}'")

        if remote_exists(ssh, MCU_SCRIPT):
            print("mcu_update.py found on device.")
        else:
            print("mcu_update.py not found on device. Uploading...")
            if not os.path.exists(local_script):
                print(f"[ERROR] '{script_name}' not found in {BASE_DIR}")
                return False
            upload(ssh, local_script, MCU_SCRIPT)

        print("Uploading firmware.bin...")
        run(ssh, f"sudo rm -f '{FW_PATH}'")
        upload(ssh, local_fw, FW_PATH)
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

        # --- the API service uses the serial port, so stop it first ---
        print("Stopping service...")
        run(ssh, f"sudo systemctl stop {SERVICE}")
        stopped = True

        print("Flashing MCU...")
        cmd = (f"sudo python3 -c \"import sys; sys.path.insert(0, '{MCU_DIR}'); "
               f"import mcu_update; mcu_update.update_firmware('{device}')\" 2>&1")
        _, stdout, _ = ssh.exec_command(cmd, timeout=300)
        out = stdout.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        print(out)

        low = out.lower()
        if code != 0 or "failed" in low or "error" in low or "unable" in low:
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
                if not start_service_and_verify(ssh):
                    print("[WARNING] Service is not active. Check it manually.")
            except Exception as e:
                print(f"[ERROR] Failed to start service: {e}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def reboot_device(ssh):
    print("System will be restarted in 5 seconds....")
    for i in range(1, 6):
        print(i)
        time.sleep(1)
    try:
        ssh.exec_command("sudo reboot")
        time.sleep(2)                     # let the command reach the Pi
    except Exception:
        pass                              # connection drops during reboot; expected


def main():
    ssh = None
    try:
        ip = ask_ip()
        if ip is None:
            return

        password = os.environ.get(SSH_PASSWORD_ENV) or getpass.getpass(
            "Device password (typing will not be shown): ")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {ip}...")
        ssh.connect(ip, 22, SSH_USER, password, timeout=10, banner_timeout=15,
                    auth_timeout=15, look_for_keys=False, allow_agent=False)
        ssh.get_transport().set_keepalive(30)
        print("Connected.\n")

        while True:
            print("Choose an option:")
            print("  1. Backend firmware Update")
            print("  2. UI Update")
            print("  3. MCU firmware Update")
            print("  4. Exit")
            try:
                choice = int(input("Enter Your Choice (1-4): "))
            except ValueError:
                print("Invalid choice. Please enter a number between 1 and 4.\n")
                continue

            if choice == 1:
                system_update_backend(ssh)
            elif choice == 2:
                if system_update_ui(ssh):
                    reboot_device(ssh)
                    break                 # connection is gone after reboot
            elif choice == 3:
                system_update_firmware(ssh)
            elif choice == 4:
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 4.\n")
                continue
            print()

    except paramiko.AuthenticationException:
        print("Authentication failed. Check the password.")
    except (socket.timeout, TimeoutError):
        print("Connection timed out. Check the IP address and that both devices are on the same network.")
    except (paramiko.SSHException, OSError) as e:
        print(f"Could not connect/communicate with the device: {e}")
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if ssh:
            ssh.close()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()