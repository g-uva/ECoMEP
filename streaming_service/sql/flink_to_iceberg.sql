-- Detach so compose doesn't block
SET 'execution.attached' = 'false';

-- Kafka source (raw JSON)
CREATE TABLE raw_metrics (
  NodeID STRING,
  `timestamp` DOUBLE,
  cpu DOUBLE,
  power DOUBLE,
  latency_ms DOUBLE,
  bandwidth_mbps DOUBLE,
  renewable_share DOUBLE
) WITH (
  'connector' = 'kafka',
  'topic' = 'metrics.raw.stream',
  'properties.bootstrap.servers' = 'kafka:9092',
  'scan.startup.mode' = 'earliest-offset',
  'format' = 'json',
  'json.ignore-parse-errors' = 'true'
);

-- Iceberg catalog on MinIO (HadoopCatalog style)
CREATE CATALOG lake WITH (
  'type'='iceberg',
  'catalog-impl'='org.apache.iceberg.hadoop.HadoopCatalog',
  'warehouse'='s3a://warehouse',
  'io-impl'='org.apache.iceberg.aws.s3.S3FileIO',
  's3.endpoint'='http://minio:9000',
  's3.path-style-access'='true',
  's3.access-key-id'='minio',
  's3.secret-access-key'='minio123'
);
USE CATALOG lake;
CREATE DATABASE IF NOT EXISTS metrics;

-- Target table (ACID)
CREATE TABLE IF NOT EXISTS metrics.clean (
  device_id STRING,
  ts TIMESTAMP_LTZ(3),
  cpu DOUBLE,
  power_w DOUBLE,
  latency_ms DOUBLE,
  bandwidth_mbps DOUBLE,
  renewable_share DOUBLE
)
PARTITIONED BY (bucket(64, device_id), days(ts));

-- Continuous insert (Kafka -> Iceberg)
INSERT INTO metrics.clean
SELECT
  NodeID AS device_id,
  TO_TIMESTAMP_LTZ(CAST(`timestamp`*1000 AS BIGINT), 3) AS ts,
  cpu,
  power AS power_w,
  latency_ms,
  bandwidth_mbps,
  renewable_share
FROM default_catalog.default_database.raw_metrics;


-- clean stream for dashboards (to existing topic `metrics.clean`)
CREATE TABLE metrics_clean_kafka (
  device_id STRING,
  ts TIMESTAMP_LTZ(3),
  cpu DOUBLE,
  power_w DOUBLE,
  latency_ms DOUBLE,
  bandwidth_mbps DOUBLE,
  renewable_share DOUBLE
) WITH (
  'connector'='kafka',
  'topic'='metrics.clean',
  'properties.bootstrap.servers'='kafka:9092',
  'format'='json'
);

INSERT INTO metrics_clean_kafka
SELECT device_id, ts, cpu, power_w, latency_ms, bandwidth_mbps, renewable_share
FROM metrics.clean;
