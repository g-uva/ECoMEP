uvicorn server.predict:app --reload --port 8080
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"lag_1h":0.42,"lag_2h":0.38,"lag_3h":0.35,"lag_6h":0.30}'
