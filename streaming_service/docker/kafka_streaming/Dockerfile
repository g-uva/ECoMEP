FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY ./mqtt_to_kafka.py .
COPY ./requirements.txt .
COPY ./topics.sh .
RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x ./topics.sh


CMD ["topics.sh && \", "python", "-u", "mqtt_to_kafka.py"]
