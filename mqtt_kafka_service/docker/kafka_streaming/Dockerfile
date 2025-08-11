FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY ./mqtt_to_kafka.py .
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "mqtt_to_kafka.py"]
