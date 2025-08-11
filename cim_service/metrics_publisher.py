import json, time, random, socket
import paho.mqtt.client as mqtt
from pathlib import Path
import os

# BROKER = os.getenv("BROKER", "mqtt") # from the docker-compose network

ROOT = Path(__file__).resolve().parent
NODES = json.loads((ROOT / "namespaces.json").read_text())

BROKER = "localhost"
PORT = 1883
TOPIC_BASE = "ecc/metrics"

# MQTT v3.1.1 + legacy v1 callback API
client = mqtt.Client(
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
)
client.enable_logger()

connected = False

def on_connect(client, userdata, flags, rc):
    global connected
    print("on_connect rc=", rc)
    connected = (rc == 0)

def on_disconnect(client, userdata, rc):
    print("on_disconnect rc=", rc)

def on_log(client, userdata, level, buf):
    print("LOG:", buf)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_log = on_log

print("getaddrinfo:", socket.getaddrinfo(BROKER, PORT))

client.loop_start()
client.connect_async(BROKER, PORT, keepalive=60)
client.reconnect_delay_set(min_delay=1, max_delay=5)

# Wait for connection with timeout
deadline = time.time() + 10
while not connected and time.time() < deadline:
    print("Waiting for MQTT connection...")
    time.sleep(0.2)
if not connected:
    raise SystemExit("No CONNACK — check broker logs while running this script.")

def random_metric(node):
    return {
        "NodeID": node["NodeID"],
        "timestamp": time.time(),
        "cpu": round(random.uniform(10, 90), 2),
        "power": round(random.uniform(50, 200), 2),
        "latency_ms": node["network"]["latency_ms"],
        "bandwidth_mbps": node["network"]["bandwidth_mbps"],
        "renewable_share": node["energyContext"]["renewableShare"],
    }

while True:
    for node in NODES:
        payload = random_metric(node)
        topic = f"{TOPIC_BASE}/{node['NodeID']}"
        r = client.publish(topic, json.dumps(payload), qos=0, retain=False)
        print(f"Published to {topic}: rc={r.rc}")
    time.sleep(2)