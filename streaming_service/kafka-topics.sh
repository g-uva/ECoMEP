#!/usr/bin/env bash
set -euo pipefail

if command -v kafka-topics.sh >/dev/null 2>&1; then
  KAFKA_TOPICS_BIN="$(command -v kafka-topics.sh)"
else
  echo "ERROR: kafka-topics.sh not found in PATH. Install Kafka CLI or run an init container that has it."
  exit 1
fi

create() {
  local topic="$1"
  local parts="$2"
  shift 2
  "$KAFKA_TOPICS_BIN" --bootstrap-server "$BOOTSTRAP" \
    --create --if-not-exists \
    --topic "$topic" --partitions "$parts" --replication-factor 1 \
    "$@"
}

# 1) Raw Stream (7d delete)
create metrics.raw.stream 6 \
  --config cleanup.policy=delete \
  --config retention.ms=604800000 \
  --config retention.bytes=10737418240 \
  --config segment.ms=3600000 \
  --config min.insync.replicas=1

# 2) Clean Stream (45d delete)
create metrics.clean 6 \
  --config cleanup.policy=delete \
  --config retention.ms=3888000000 \
  --config segment.ms=3600000 \
  --config min.insync.replicas=1

# 3) Dead-letter (30d delete)
create errors.dlq 3 \
  --config cleanup.policy=delete \
  --config retention.ms=2592000000

# 4) Reference (compacted)
create reference.devices 3 \
  --config cleanup.policy=compact \
  --config min.cleanable.dirty.ratio=0.1 \
  --config segment.ms=3600000

# Show result in logs
"kafka-topics.sh" --bootstrap-server "$BOOTSTRAP" --list
