#!/bin/bash
# filepath: /Users/goncaloferreira/Work/uva/greendigit/EdgeCloudPredictive/mqtt_streaming_service/mqtt-kafka-project/docker/kafka/start-kafka.sh

export KAFKA_ADVERTISED_LISTENERS=${KAFKA_ADVERTISED_LISTENERS:-PLAINTEXT://kafka:9092}
export KAFKA_LISTENERS=${KAFKA_LISTENERS:-PLAINTEXT://0.0.0.0:9092}
export KAFKA_ZOOKEEPER_CONNECT=${KAFKA_ZOOKEEPER_CONNECT:-zookeeper:2181}

exec /bin/bash /start-kafka.sh