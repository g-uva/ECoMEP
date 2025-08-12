-- 1) Source: Kafka raw
CREATE TABLE raw_metrics (
  NodeID STRING,
  `timestamp` DOUBLE,
  cpu DOUBLE,
  power DOUBLE,
  latency_ms DOUBLE,
  bandwidth_mbps DOUBLE,
  renewable_share DOUBLE
) WITH (
  'connector'='kafka',
  'topic'='metrics.raw.stream',
  'properties.bootstrap.servers'='kafka:9092',
  'scan.startup.mode'='earliest-offset',
  'format'='json',
  'json.ignore-parse-errors'='true'
);

-- 2) Iceberg catalog (HadoopCatalog -> MinIO)
CREATE CATALOG lake WITH (
  'type'='iceberg',
  'catalog-impl'='org.apache.iceberg.hadoop.HadoopCatalog',
  'warehouse'='s3a://warehouse'
);
USE CATALOG lake;
CREATE DATABASE IF NOT EXISTS metrics;

-- 3) Target table
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

-- 4) Persist (continuous job; leave running)
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
