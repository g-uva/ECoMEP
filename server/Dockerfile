FROM python:3.11-slim
WORKDIR /app
COPY models/baseline.joblib models/
COPY server/ server/
RUN pip install -r server/requirements.txt
CMD ["uvicorn", "server.predict:app", "--host", "0.0.0.0", "--port", "8080"]
