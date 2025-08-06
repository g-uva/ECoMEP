FROM python:3.13.5-slim
WORKDIR /app
COPY workload-producer.py .
RUN pip install requests
ENV PYTHONUNBUFFERED=1
CMD ["python", "workload-producer.py"]
