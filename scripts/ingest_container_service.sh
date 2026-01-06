#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SCRIPT_DIR"
# NET=$(docker network ls --format '{{.Name}}' | grep _default) | ""
# NET="mqtt_kafka_service_default" # Default network in docker-compose.
cp ../cim_service/synthetic_metrics.ndjson .
docker run --rm --network mqtt_kafka_service_default \
  -v "$REPO_ROOT:/app" -w /app/scripts python:3.11-slim bash -lc \
  "pip install -r /app/requirements.txt && python ingest_kafka.py kafka \
   --input synthetic_metrics.ndjson --bootstrap kafka:9092 --topic metrics.raw.stream"
rm -rf ./synthetic_metrics.ndjson
