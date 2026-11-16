MCU_DIR = "/home/pi/stm-bootloader"
MCU_SCRIPT = f"{MCU_DIR}/mcu_update.py"
FW_DIR = f"{MCU_DIR}/latest_firmware"
FW_PATH = f"{FW_DIR}/firmware.bin"
STM32FLASH = f"{MCU_DIR}/git/stm32flash/stm32flash"
SERIAL_PORTS = ["/dev/ttyAMA0", "/dev/ttyUSB0"]

def remote_exists(ssh, path):
    _, stdout, _ = ssh.exec_command(f"test -e '{path}'")
    return stdout.channel.recv_exit_status() == 0

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

def system_update_mcu(ssh, fw_name="firmware.bin", script_name="mcu_update.py"):
    local_fw = os.path.join(BASE_DIR, fw_name)
    local_script = os.path.join(BASE_DIR, script_name)
    stopped = False
    try:
        # --- local checks ---
        if not os.path.exists(local_fw) or os.path.getsize(local_fw) == 0:
            print(f"[ERROR] '{fw_name}' not found (or empty) in {BASE_DIR}")
            return False

        # --- device checks ---
        if not remote_exists(ssh, STM32FLASH):
            print(f"[ERROR] stm32flash not found on the device at {STM32FLASH}")
            return False

        # make sure folders exist and are writable by 'pi'
        run(ssh, f"sudo mkdir -p '{FW_DIR}' && sudo chown pi:pi '{MCU_DIR}' '{FW_DIR}'")
        run(ssh, f"[ ! -e '{FW_PATH}' ] || sudo chown pi:pi '{FW_PATH}'")

        # --- mcu_update.py: add only if missing ---
        if remote_exists(ssh, MCU_SCRIPT):
            print("mcu_update.py found on device.")
        else:
            print("mcu_update.py not found on device. Uploading...")
            if not os.path.exists(local_script):
                print(f"[ERROR] '{script_name}' not found in {BASE_DIR}")
                return False
            upload(ssh, local_script, MCU_SCRIPT)

        # --- firmware.bin: always replace with the new one ---
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