import json, time, random, socket
import paho.mqtt.client as mqtt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NODES = json.loads((ROOT / "namespaces.json").read_text())

BROKER = "localhost"
PORT = 1883
TOPIC_BASE = "ecc/metrics"

# Paho 2.x + MQTT v5 + v2 callback API
client = mqtt.Client(
    protocol=mqtt.MQTTv5,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    transport="tcp",
)

# Optional: fail fast if DNS picks IPv6 first on your setup
# (diagnostic only)
print("getaddrinfo:", socket.getaddrinfo(BROKER, PORT))

client.enable_logger()  # verbose logs to stdout

connected = False

def on_connect(client, userdata, flags, reason_code, properties):
    global connected
    print("on_connect reason_code:", reason_code)
    connected = (int(reason_code) == 0)

def on_disconnect(client, userdata, rc, properties=None):
    print("on_disconnect rc:", rc)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.loop_start()
# If you still hit Errno 49, try connect_async (non-blocking) then wait
client.connect_async(BROKER, PORT, keepalive=60)
client.reconnect_delay_set(min_delay=1, max_delay=5)

# Wait for connection (with timeout so we don’t loop forever)
deadline = time.time() + 10
while not connected and time.time() < deadline:
    print("Waiting for MQTT connection...")
    time.sleep(0.2)

if not connected:
    raise SystemExit("Could not connect to MQTT. Check broker logs and port reachability.")

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
        metric = random_metric(node)
        topic = f"{TOPIC_BASE}/{node['NodeID']}"
        result = client.publish(topic, json.dumps(metric), qos=0, retain=False)
        print(f"Published to {topic}: rc={result.rc}")
    time.sleep(2)
