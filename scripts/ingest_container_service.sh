# NET=$(docker network ls --format '{{.Name}}' | grep _default) | ""
# NET="mqtt_kafka_service_default" # Default network in docker-compose.
cp ../cim_service/synthetic_metrics.ndjson .
docker run --rm --network mqtt_kafka_service_default \
  -v "$PWD:/app" -w /app python:3.11-slim bash -lc \
  "pip install -r requirements.txt && python ingest.py kafka \
   --input synthetic_metrics.ndjson --bootstrap kafka:9092 --topic metrics.raw.stream"
rm -rf ./synthetic_metrics.ndjson
