import json, time, random
import paho.mqtt.client as mqtt
from pathlib import Path

NODES = json.loads(Path("../cim_service/namespaces.json").read_text())
BROKER = "localhost"
TOPIC_BASE = "ecc/metrics"

client = mqtt.Client(protocol=mqtt.MQTTv311)

connected = False
def on_connect(client, userdata, flags, rc):
    global connected
    print("Connected with result code", rc)
    connected = True
client.on_connect = on_connect

client.loop_start()
client.connect(BROKER)

# Wait for connection before publishing
while not connected:
    print("Waiting for MQTT connection...")
    time.sleep(0.1)

def random_metric(node):
    return {
        "NodeID": node["NodeID"],
        "timestamp": time.time(),
        "cpu": round(random.uniform(10, 90), 2),
        "power": round(random.uniform(50, 200), 2),
        "latency_ms": node["network"]["latency_ms"],
        "bandwidth_mbps": node["network"]["bandwidth_mbps"],
        "renewable_share": node["energyContext"]["renewableShare"]
    }

while True:
    for node in NODES:
        metric = random_metric(node)
        topic = f"{TOPIC_BASE}/{node['NodeID']}"
        result = client.publish(topic, json.dumps(metric))
        print(f"Published to {topic}: {metric}, result: {result.rc}")
    time.sleep(2)