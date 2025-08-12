-- 1) Keeps a live metric reader from the Kafka connector.
CREATE TABLE metrics_clean_kafka (...) WITH ('connector'='kafka','topic'='metrics.clean',...);
INSERT INTO metrics_clean_kafka SELECT ... FROM default_catalog.default_database.raw_metrics;