import paho.mqtt.client as mqtt
from kafka import KafkaProducer
import json

MQTT_BROKER = "localhost"
MQTT_TOPIC = "ecc/metrics/#"
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "metrics.raw.stream"

producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER, value_serializer=lambda v: json.dumps(v).encode())

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    producer.send(KAFKA_TOPIC, payload)
    print(f"Forwarded: {payload}")

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_message = on_message
client.connect(MQTT_BROKER)
client.subscribe(MQTT_TOPIC)
client.loop_forever()