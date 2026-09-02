import json
import subprocess
import time
# from datetime import datetime, timezone
import paho.mqtt.client as mqtt

API_KEY = "579b464db66ec23bdd0000017f73855c9618411c6fd25abca5056c47"
RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
API_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

CITY = "Chennai"
STATE = "Tamil Nadu"
STATION_NAME = "Perungudi, Chennai - TNPCB"
LIMIT = 100

MQTT_BROKER = "mqtt.denvik.in"
MQTT_PORT = 1883
MQTT_TOPIC = "croppico-test/CPCB"
MQTT_USERNAME = "Denvik"
MQTT_PASSWORD = "PvhMtj1QlGgQ1w2"
POLL_INTERVAL_SECONDS = 30 * 60  # 30 minutes


def fetch_station_records(retries=3, backoff_seconds=10, timeout=60):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-s",                      # silent (no progress meter)
                    "-S",                      # but still show errors
                    "-G",                      # build a GET request with the -d params below
                    "--data-urlencode", f"api-key={API_KEY}",
                    "--data-urlencode", "format=json",
                    "--data-urlencode", f"limit={LIMIT}",
                    "--data-urlencode", f"filters[city]={CITY}",
                    "--data-urlencode", f"filters[state]={STATE}",
                    "--max-time", str(timeout),
                    "-w", "\n%{http_code}",    # append HTTP status on its own line
                    API_URL,
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 10,   
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"curl exited with code {result.returncode}: {result.stderr.strip()}"
                )

            # The last line is the HTTP status code we appended with -w
            output = result.stdout
            body, _, status_code = output.rpartition("\n")

            if status_code == "429":
                print("Rate limit exhausted (HTTP 429). Skipping retries this cycle.")
                return []

            if not status_code.startswith("2"):
                raise RuntimeError(f"HTTP {status_code} from API. Body: {body[:300]}")

            data = json.loads(body)
            records = data.get("records", [])
            return [r for r in records if r.get("station") == STATION_NAME]

        except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as e:
            last_error = e
            print(f"Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(backoff_seconds)

    raise last_error


def build_payload(records):
    """Turn the list of per-pollutant records into the target JSON shape."""
    if not records:
        return None

    pollutant_data = {}
    last_updated = None

    for r in records:
        pollutant = r.get("pollutant_id")
        if not pollutant:
            continue

        pollutant_data[pollutant] = {
            "avg": r.get("avg_value"),
            "min": r.get("min_value"),
            "max": r.get("max_value"),
        }
        if r.get("last_update"):
            last_updated = r["last_update"]

    payload = {
        "current_Timestamp": int(time.time()),
        "last_updated": last_updated,
        "data": pollutant_data,
    }
    return payload

def make_mqtt_client():
    client = mqtt.Client()
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    return client


def publish_payload(client, payload):
    message = json.dumps(payload)
    result = client.publish(MQTT_TOPIC, message, qos=1, retain=True)
    result.wait_for_publish()
    print(f"[{int(time.time())}] Published to '{MQTT_TOPIC}':")
    print(message)

def run_once(client):
    try:
        records = fetch_station_records()
        if not records:
            print("No AQI data found for station, skipping this cycle.")
            return

        payload = build_payload(records)
        if payload is None:
            print("Could not build payload, skipping this cycle.")
            return

        publish_payload(client, payload)

    except json.JSONDecodeError:
        print("Invalid JSON received from API.")
    except Exception as e:
        print("Unexpected error:", e)

def main():
    client = make_mqtt_client()
    client.loop_start()
    try:
        while True:
            run_once(client)
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()