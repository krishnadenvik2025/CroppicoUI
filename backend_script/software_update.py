import os, paramiko, sys, time

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.channel.recv_exit_status()
    if code != 0:
        raise RuntimeError(f"'{cmd}' failed ({code}): {stderr.read().decode().strip()}")
    return stdout.read().decode()

def system_update_ui(ssh, local_zip="croppico_ui.zip"):
    base = "/home/pi/ui_backups"
    cur, prv = f"{base}/cur_ui", f"{base}/prv_ui"
    service = "cropicco-api.service"
    try:
        if not os.path.exists(local_zip):
            print("[ERROR] File not found. Please place the file in the same folder with name 'croppico_ui.zip'.")
            return False
        print("Initializing UI update process")
        run(ssh, f"mkdir -p {cur} {prv}")

        print("Uploading new UI")
        sftp = ssh.open_sftp()
        try:
            sftp.put(local_zip, f"{cur}/croppico-ui.zip")
        finally:
            sftp.close()

        print("Extracting new UI")
        run(ssh, f"rm -rf {cur}/html && unzip -o {cur}/croppico-ui.zip -d {cur}/html")

        print("Taking backup of current UI")
        run(ssh, f"rm -rf {prv}/html && cp -r /var/www/html {prv}/html")

        print("Replacing UI")
        run(ssh, f"sudo rm -rf /var/www/html && sudo cp -r {cur}/html /var/www/html")

        print("Done...")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def system_update_backend(ssh, local_zip="script.zip"):
    base = "/home/pi/backend_backups"
    cur, prv = f"{base}/cur_backend", f"{base}/prv_backend"
    try:
        if not os.path.exists(local_zip):
            print("[ERROR] File not found. Please place the file in the same folder with name 'script.zip'.")
            return False
        print("Initializing backend update process")
        run(ssh, f"mkdir -p {cur} {prv}")

        print("Uploading new backend")
        sftp = ssh.open_sftp()
        try:
            sftp.put(local_zip, f"{cur}/script.zip")
        finally:
            sftp.close()

        print("Extracting new backend")
        run(ssh, f"rm -rf {cur}/backend_script && unzip -o {cur}/script.zip -d {cur}/backend_script")

        print("Taking backup of current backend")
        run(ssh, f" rm -rf {prv}/backend_script && cp -r /home/pi/croppico-api-new {prv}/backend_script")

        print("Replacing backend")
        run(ssh, f"sudo cp -a {cur}/backend_script/. /home/pi/croppico-api-new")

        print("Done")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        print("Restarting service....")
        try:
            run(ssh, f"sudo systemctl restart cropicco-api.service")
        except Exception as e:
            print(f"Failed to restart service: {e}")

try:
    print("Enter System's ip address and ensure both system and Laptop/PC is connected to the same network")
    ip = str(input("(eg: 192.168.1.90)"))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, 22, 'pi', '!@#$%^&*()@123')
    time.sleep(2)
    print("Choose an option:\n1. Backend firmware Update\n2. UI Update\n3. Exit")
    choice = int(input("Enter Your Choice(1-3):"))
    if choice == 1:
        bck = system_update_backend(ssh)
    elif choice == 2:
        ui = system_update_ui(ssh)
        if ui:
            print("System will be restarted after 5 seconds....")
            for i in range(1,6):
                print(i)
                time.sleep(1)
            run(ssh, "sudo reboot")

    elif choice == 3:
        print("Exiting in 2 seconds.....")
        time.sleep(2)
        sys.exit()
    else:
        print("Invalid Choice... Please enter a number between 1 and 3")
        sys.exit()
finally:
    ssh.close()
    