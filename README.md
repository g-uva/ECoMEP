# 🌱🌍♻️ ECoMEP - Edge-Cloud Continuum Multi-Level ML Energy Prediction Framework (GreenDIGIT project)

>**Disclaimer**: the information on this README is still temporary. The tools, architecture and other specifications are subject to change.

> Part of GreenDIGIT WP6.2 — Predictive AI for Federated Energy-Aware Workflows  
> Developed in collaboration with SoBigData RI, IFCA, DIRAC, and GreenDIGIT RIs and partners.


## Overview

This framework enables **real-time predictive modelling** across **Edge–Fog–Cloud infrastructures** using **multi-level machine learning pipelines**. It ingests environmental and performance metrics (e.g. energy, CPU usage, workload profiles) from **distributed clusters and IoT devices**, processes them, and trains models to **forecast resource usage, network load, and system performance**.

Deployed as part of the **GreenDIGIT WP6.2** research activities, this module integrates with:

- [WP6.1 Environmental Metric Publication System](#)
- [WP6.3 Energy-Aware Brokering Framework](#)
- SoBigData RI metrics ecosystem
- IFCA and DIRAC records infrastructure
- (Future plans): Testbed experimentation (e.g., Chamaleon/FABRIC/GD)

---

## Architecture

- [ ] TODO: copy/paste architecture diagram once it's completed.

## Machine Learning Pipeline

### Ingestion & Preprocessing
- Collect metrics from edge nodes, sensors, and cluster logs
- Use **MQTT**, **Prometheus**, or **Kafka/NATS**
- Normalie, timestamp-align, and validate data

### Model Training
- Train using:
  - **Time Series Forecasting** (LSTM, Prophet)
  - **Regression/Classification** (XGBoost, RF)
  - **Energy/Latency Prediction**
- Tools: **PyTorch**, **TensorFlow**, **Scikit-learn**

### Real-Time Inference
- ONNX or TensorFlow Lite models served at edge
- Model registry: MLflow or DVC-based

---

## Folder Structure

<!-- ```bash
.
├── ingestion/             # Metric ingestion and connectors
├── preprocessing/         # Data cleaning and transformation
├── training/              # Training scripts and model tracking
├── inference/             # Model serving scripts (ONNX, Lite)
├── deployment/            # Helm charts, Dockerfiles
├── crate/                 # RO-Crate metadata, licences, schema
├── ro-crate-metadata.json
├── Dockerfile
├── requirements.txt
└── README.md
``` -->

### New version
```bash
EdgeCloudPredictive/
├── ingestion/                # Kafka consumers, schema
├── preprocessing/            # Feature builders, GreatExp suites
├── training/                 # PyTorch/Sklearn code, MLflow configs
├── inference/                # FastAPI server, ONNX / TFLite loaders
├── deployment/               # Helm charts, Dockerfiles
│   ├── helm/                 # Chart for Training & Inference services
│   └── gha-workflows/        # CI/CD YAML
├── crate/                    # RO-Crate metadata, licences, schema
├── ro-crate-metadata.json
└── notebooks/                # EDA & experiment design
```

## Outputs and Publications
Unified JSON or RO-Crate formatted metrics

- `/FETCH` endpoint compatible with WP6.1 publication system
- Optionally `POST`ed to:
    - cASO and Grid record services
    - CIM record registry with auth token

### Interoperability
- RO-Crate compliant for FAIR metadata
- Containerised for deployment in federated clusters
- Compatible with SoBigData metrics registry and Dirac grid APIs
- Modular, with pluggable ML models and data formats

## Citation
```
@software{GreenDIGIT_WP62,
  title = {Edge-Cloud Continuum Multi-Level Predictive Framework},
  author = {GreenDIGIT WP6.2 Contributors},
  year = {2025},
  version = {v1.0},
  url = {https://github.com/GreenDIGIT/WP6.2-Predictive-Framework}
}
```

## Contributors
Gonçalo Ferreira – UvA Researcher - WP6.2 Developer
- [ ] [Collaborators, Partners]

Supported by GreenDIGIT, SoBigData RI, IFCA, DIRAC, and CNR.

## Contact
For questions, integration requests or metric schema definitions, contact:

GreenDIGIT WP6.2 Team
📧 contact@greendigit.eu
🌐 greendigit.eu