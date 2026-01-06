FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Ensure bash + dos2unix are available
RUN apt-get update && \
    apt-get install -y --no-install-recommends bash dos2unix ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY streaming_service/kafka_streaming/mqtt_to_kafka.py .
COPY streaming_service/kafka_streaming/kafka-topics.sh .

# Normalize line endings and ensure executable
RUN dos2unix ./kafka-topics.sh && chmod +x ./kafka-topics.sh

# Run with bash; show simple markers to know where it dies
# CMD ["bash", "-lc", "set -Eeuo pipefail; echo '>> running kafka-topics.sh'; ./kafka-topics.sh; echo '>> kafka-topics.sh done'; exec python -u mqtt_to_kafka.py"]
CMD ["bash", "-c", "exec python -u mqtt_to_kafka.py"]
