# mqtt_to_kafka.py
import os, json, sys
import paho.mqtt.client as mqtt
from kafka import KafkaProducer
from datetime import datetime, timezone

# ---- Config via env (defaults match docker-compose service names) ----
MQTT_BROKER   = os.getenv("MQTT_BROKER", "mqtt")
MQTT_PORT     = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC    = os.getenv("MQTT_TOPIC", "ecc/metrics/#")

KAFKA_BROKER  = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC   = os.getenv("KAFKA_TOPIC", "metrics.raw.stream")

print(f"[bridge] mqtt://{MQTT_BROKER}:{MQTT_PORT}  ->  kafka://{KAFKA_BROKER} topic={KAFKA_TOPIC}")

# ---- Kafka producer (JSON, with keys) ----
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER.split(","),
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: (k or "").encode("utf-8"),
    linger_ms=50,  # batch a little
)

# ---- MQTT client (MQTT v3.1.1 works with most Mosquitto defaults) ----
client = mqtt.Client(protocol=mqtt.MQTTv311)  # Paho 2.x OK with v3.1.1 + v1 callbacks
client.enable_logger()

def on_connect(cli, userdata, flags, rc):
    print(f"[bridge] MQTT connected rc={rc}, subscribing to {MQTT_TOPIC}")
    cli.subscribe(MQTT_TOPIC)

def on_message(cli, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        payload = {"raw_payload": msg.payload.decode("utf-8", errors="ignore")}
    # Enrich minimally
    payload.setdefault("provenance", {})["topic"] = msg.topic
    payload.setdefault("ts", int(datetime.now(tz=timezone.utc).timestamp() * 1000))
    payload.setdefault("ingest_version", 1)

    device = payload.get("device_id") or payload.get("NodeID") or "unknown-device"
    metric = payload.get("metric_type") or payload.get("metric") or "unknown-metric"
    key = f"{device}:{metric}"

    producer.send(KAFKA_TOPIC, value=payload, key=key)
    print(f"[bridge] {msg.topic} → {KAFKA_TOPIC} (key={key})")

client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_forever()
