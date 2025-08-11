# MQTT and Kafka Project

This project sets up an MQTT broker and Kafka using Docker containers. It allows for seamless communication between the two services, enabling the forwarding of messages from MQTT to Kafka.

## Project Structure

```
mqtt-kafka-project
├── docker
│   ├── kafka
│   │   └── Dockerfile
│   └── mqtt
│       └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Docker installed on your machine
- Docker Compose installed

## Getting Started

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mqtt-kafka-project
   ```

2. **Build the Docker images**:
   You can build the images using Docker Compose, which will automatically build the images defined in the `docker-compose.yml` file.
   ```bash
   docker-compose build
   ```

3. **Run the services**:
   Start the MQTT broker and Kafka services using Docker Compose.
   ```bash
   docker-compose up
   ```

4. **Accessing the services**:
   - The MQTT broker will be available on `localhost:1883`.
   - Kafka will be accessible on `localhost:9092`.

## Stopping the Services

To stop the services, you can use:
```bash
docker-compose down
```

## Additional Information

- Ensure that the necessary ports are open and not being used by other applications.
- You can modify the configurations in the respective Dockerfiles and `docker-compose.yml` as needed for your specific use case.