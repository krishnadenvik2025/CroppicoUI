import os, time, subprocess, logging, boto3
from datetime import datetime
from botocore.exceptions import ClientError

def get_logger(name="Snapshot_logger", log_file="snapshot_log.txt", log_dir="logs", level=logging.DEBUG):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        file_handler = logging.FileHandler(log_path, mode="a")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)-15s  %(levelname)-8s %(message)s"
        ))
        logger.addHandler(file_handler)
    return logger

logger = get_logger(log_dir="/home/pi/cctv_logs/")

# --- CONFIG ---
CAM_RTSP = "rtsp://admin:Denvik01@192.168.1.7:554/Streaming/channels/101"
SNAP_DIR = "/home/pi/snapshots"

S3_BUCKET = "your-bucket-name"
S3_PREFIX = f"snapshots/"
AWS_REGION = "ap-south-1"

INTERVAL_SECONDS = 300
s3 = boto3.client("s3", region_name=AWS_REGION)


def capture_snapshot():
    os.makedirs(SNAP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}.jpg"
    filepath = os.path.join(SNAP_DIR, filename)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-rtsp_transport", "tcp",
        "-i", CAM_RTSP,
        "-frames:v", "1",
        "-q:v", "2",
        filepath
    ]

    try:
        result = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=20
        )
        if result.returncode != 0 or not os.path.exists(filepath):
            logger.error(f"ffmpeg failed: {result.stderr.decode(errors='ignore')}")
            print(f"ffmpeg failed to capture snapshot: {result.stderr.decode(errors='ignore')}")
            return None
        return filepath
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timed out capturing snapshot")
        print("ffmpeg timed out capturing snapshot")
        return None
    except Exception as e:
        logger.error(f"Error capturing snapshot: {e}")
        print(f"Error capturing snapshot: {e}")
        return None


def upload_to_s3(filepath):
    filename = os.path.basename(filepath)
    s3_key = f"{S3_PREFIX}/{filename}"
    try:
        s3.upload_file(filepath, S3_BUCKET, s3_key)
        logger.info(f"Uploaded {filename} -> s3://{S3_BUCKET}/{s3_key}")
        print(f"Uploaded {filename} -> s3://{S3_BUCKET}/{s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        print(f"S3 upload failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected upload error: {e}")
        print(f"Unexpected upload error: {e}")
        return None


def cleanup_local(filepath):
    try:
        os.remove(filepath)
    except Exception as e:
        logger.warning(f"Could not remove local file {filepath}: {e}")


def main_loop():
    print(f"Starting snapshot loop for, every {INTERVAL_SECONDS}s")
    logger.info(f"Starting snapshot loop for, every {INTERVAL_SECONDS}s")

    while True:
        start_time = time.time()

        filepath = capture_snapshot()
        if filepath:
            uploaded_key = upload_to_s3(filepath)
            if uploaded_key:
                cleanup_local(filepath)

        elapsed = time.time() - start_time
        sleep_time = max(0, INTERVAL_SECONDS - elapsed)
        time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as e:
        logger.error(f"Exited from loop with error: {e}")
        print(f"Exited from loop with error: {e}")