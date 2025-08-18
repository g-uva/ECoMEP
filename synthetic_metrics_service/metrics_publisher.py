# metrics_publisher.py — paced replay + SourceType filter + optional ts override
import json, time, socket, os
from pathlib import Path
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parent
INFILE = Path(os.getenv("NDJSON", ROOT / "gen/synthetic_metrics.ndjson"))

BROKER = os.getenv("BROKER", "localhost")
PORT = int(os.getenv("PORT", "1883"))
TOPIC_ROOT = os.getenv("TOPIC_ROOT", "gd-metrics")
QOS = int(os.getenv("QOS", "1"))

# Pacing / filtering controls
PACE_MODE = os.getenv("PACE_MODE", "cadence")
CADENCE_S = float(os.getenv("CADENCE_S", "3"))
REPLAY_SPEED = float(os.getenv("REPLAY_SPEED", "1.0"))
OVERRIDE_TS = os.getenv("OVERRIDE_TS", "true").lower()
SOURCE_TYPE = os.getenv("SOURCE_TYPE", "IoT")

def parse_iso_z(s: str) -> datetime:
    # Accept "YYYY-mm-ddTHH:MM:SSZ" or with offset
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)

def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def topic_for(rec: dict) -> str:
    # greendigit/<SourceType>/<site>/<node>/<subsystem>/<metric>
    return "/".join([
        TOPIC_ROOT,
        rec["source_type"],
        rec["site"],
        rec["node_id"],
        rec["subsystem"],
        rec["metric"],
    ])

def payload_for(rec: dict, send_time: datetime | None) -> str:
    pub = {
        "ts": iso_z(send_time) if (send_time and OVERRIDE_TS) else rec["ts"],
        "value": rec["value"],
        "unit": rec.get("unit", ""),
        "labels": rec.get("labels", {}),
        "interval_ms": rec.get("interval_ms", None),
        "quality": rec.get("quality", "measured"),
    }
    return json.dumps(pub, separators=(",", ":"))

def iter_groups_by_ts(path: Path):
    """Yield (ts_str, [records...]) groups; assumes NDJSON sorted by ts (your generator does this)."""
    current_ts = None
    bucket = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if SOURCE_TYPE and rec.get("source_type") != SOURCE_TYPE:
                continue  # filter by SourceType (default IoT)
            ts = rec["ts"]
            if current_ts is None:
                current_ts = ts
            if ts != current_ts:
                yield current_ts, bucket
                bucket = [rec]
                current_ts = ts
            else:
                bucket.append(rec)
    if bucket:
        yield current_ts, bucket

# MQTT client
client = mqtt.Client(
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
)
client.enable_logger()

def on_connect(client, userdata, flags, rc): print("on_connect rc=", rc)
def on_disconnect(client, userdata, rc):     print("on_disconnect rc=", rc)
def on_log(client, userdata, level, buf):    print("LOG:", buf)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_log = on_log

def main():
    if not INFILE.exists():
        raise SystemExit(f"Input NDJSON not found: {INFILE}")

    print("getaddrinfo:", socket.getaddrinfo(BROKER, PORT))
    client.loop_start()
    client.connect_async(BROKER, PORT, keepalive=60)
    client.reconnect_delay_set(min_delay=1, max_delay=5)

    # Wait for CONNACK
    deadline = time.time() + 10
    while not client.is_connected() and time.time() < deadline:
        print("Waiting for MQTT connection...")
        time.sleep(0.2)
    if not client.is_connected():
        raise SystemExit("No CONNACK — check broker logs while running this script.")

    sent = 0
    start_wall = time.monotonic()
    next_tick = start_wall
    prev_group_ts = None

    for ts_str, group in iter_groups_by_ts(INFILE):
        now = time.monotonic()

        if PACE_MODE == "cadence":
            next_tick += CADENCE_S
            sleep_s = max(0.0, next_tick - now)
            if sleep_s > 0:
                time.sleep(sleep_s)
            send_time = datetime.now(timezone.utc)

        elif PACE_MODE == "replay_ts":
            this_ts = parse_iso_z(ts_str)
            if prev_group_ts is not None:
                delta = (this_ts - prev_group_ts).total_seconds() / max(1e-9, REPLAY_SPEED)
                if delta > 0:
                    time.sleep(delta)
            prev_group_ts = this_ts
            send_time = datetime.now(timezone.utc)

        else:  # "none"
            send_time = datetime.now(timezone.utc)

        for rec in group:
            topic = topic_for(rec)
            payload = payload_for(rec, send_time)
            r = client.publish(topic, payload, qos=QOS, retain=False)
            if r.rc != mqtt.MQTT_ERR_SUCCESS:
                print("Publish failed rc=", r.rc, "topic=", topic)
            else:
                sent += 1
                if sent % 100 == 0:
                    print(f"Published {sent} messages… (last ts {ts_str})")

    print(f"Done. Published {sent} messages from {INFILE}")
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
