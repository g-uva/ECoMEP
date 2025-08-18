# topics.py
from confluent_kafka.admin import AdminClient, NewTopic
import os
import sys

BOOTSTRAP = os.getenv("BOOTSTRAP", "kafka:9092")

TOPICS = [
    # name, partitions, replication, configs
    ("metrics.raw.stream", 6, 1, {
        "cleanup.policy": "delete",
        "retention.ms": "604800000",
        "retention.bytes": "10737418240",
        "segment.ms": "3600000",
        "min.insync.replicas": "1",
    }),
    ("metrics.clean", 6, 1, {
        "cleanup.policy": "delete",
        "retention.ms": "3888000000",
        "segment.ms": "3600000",
        "min.insync.replicas": "1",
    }),
    ("errors.dlq", 3, 1, {
        "cleanup.policy": "delete",
        "retention.ms": "2592000000",
    }),
    ("reference.devices", 3, 1, {
        "cleanup.policy": "compact",
        "min.cleanable.dirty.ratio": "0.1",
        "segment.ms": "3600000",
    }),
]

def ensure_topics():
    print(">> ensuring Kafka topics via Admin API", flush=True)
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})
    # check existing topics
    existing = set(admin.list_topics(timeout=10).topics.keys())

    new = []
    for name, parts, repl, cfg in TOPICS:
        if name in existing:
            print(f"   - {name} exists")
            continue
        new.append(NewTopic(topic=name, num_partitions=parts, replication_factor=repl, config=cfg))

    if not new:
        print(">> topics already present")
        return

    fs = admin.create_topics(new, request_timeout=30)
    for name, f in fs.items():
        try:
            f.result()  # raises on failure
            print(f"   + created {name}")
        except Exception as e:
            # if creation races or broker rejects config, show it and continue
            print(f"   ! {name} creation failed: {e}", file=sys.stderr)
