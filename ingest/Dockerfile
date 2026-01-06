FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model artefacts and inference code
COPY models/ models/
COPY ingest/predict_xgb_lstm.py ingest/predict_xgb_lstm.py
COPY scripts/train_lstm.py scripts/train_lstm.py

CMD ["uvicorn", "ingest.predict_xgb_lstm:app", "--host", "0.0.0.0", "--port", "8080"]
