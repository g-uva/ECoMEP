#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType
)


"""
# from repo root
cd /Users/goncaloferreira/Work/uva/greendigit/EdgeCloudPredictive

export SPARK_HOME=$HOME/spark-4.0.0
export PATH="$SPARK_HOME/bin:$PATH"

spark-submit \
  --packages io.delta:delta-spark_2.13:4.0.0 \
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
  --conf "spark.driver.extraJavaOptions=-Djava.security.manager=allow" \
  --conf "spark.executor.extraJavaOptions=-Djava.security.manager=allow" \
  /Users/goncaloferreira/Work/uva/greendigit/EdgeCloudPredictive/scripts/spark_gold_job.py \
  --input workloads/uth/uth_workload_2025.jsonl \
  --output data/gold_link_window_features_delta \
  --out-format delta \
  --window "5 minutes" \
  --mode overwrite \
  --partition-cols date
"""

UTH_SCHEMA = StructType([
    StructField("exec_unit_id", StringType(), True),
    StructField("src_node", StringType(), True),
    StructField("dst_node", StringType(), True),
    StructField("start_time", StringType(), True),
    StructField("end_time", StringType(), True),
    StructField("duration_s", DoubleType(), True),
    StructField("data_amount_mb", DoubleType(), True),
    StructField("bandwidth_req_mbps", DoubleType(), True),
    StructField("throughput_mbps", DoubleType(), True),
    StructField("jitter_ms", DoubleType(), True),
    StructField("packet_loss_percent", DoubleType(), True),
    StructField("energy_results", StructType([
        StructField("total_tx_Wh", DoubleType(), True),
        StructField("total_rx_Wh", DoubleType(), True),
        StructField("total_energy_Wh", DoubleType(), True),
        StructField("MB", DoubleType(), True),
    ]), True),
])

def build_spark(app_name: str, use_delta: bool) -> SparkSession:
    builder = SparkSession.builder.appName(app_name)
    if use_delta:
        # Works when delta-spark is available in the container / spark-submit packages
        builder = (builder
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        )
    return builder.getOrCreate()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input path (json/jsonl). Supports globs.")
    ap.add_argument("--output", required=True, help="Output path for Gold table.")
    ap.add_argument("--out-format", choices=["delta", "parquet"], default="parquet")
    ap.add_argument("--window", default="5 minutes", help='Spark window duration, e.g., "5 minutes", "1 hour"')
    ap.add_argument("--mode", choices=["overwrite", "append"], default="overwrite")
    ap.add_argument("--partition-cols", default="date", help="Comma-separated partition columns. Default: date")
    args = ap.parse_args()

    use_delta = args.out_format == "delta"
    spark = build_spark("gold_link_window_features_job", use_delta)

    # Read raw (Bronze-ish)
    df = (spark.read
        .schema(UTH_SCHEMA)
        .json(args.input)
    )

    # Clean + typed columns (Silver-ish step embedded)
    clean = (df
        .withColumn("start_ts", F.to_timestamp("start_time"))
        .withColumn("end_ts", F.to_timestamp("end_time"))
        .withColumn("date", F.to_date("start_ts"))
        .withColumn("tx_Wh", F.col("energy_results.total_tx_Wh"))
        .withColumn("rx_Wh", F.col("energy_results.total_rx_Wh"))
        .withColumn("energy_Wh", F.col("energy_results.total_energy_Wh"))
        .withColumn("effective_mb", F.col("energy_results.MB"))
        .drop("energy_results")
        .dropna(subset=["src_node", "dst_node", "start_ts"])
        .dropDuplicates(["exec_unit_id"])
        .filter(F.col("src_node") != F.col("dst_node"))
        .filter(F.col("duration_s") > F.lit(0.0))
    )

    # Gold: window aggregates per link
    win_col = F.window(F.col("start_ts"), args.window).alias("w")

    gold = (clean
        .groupBy("src_node", "dst_node", "date", win_col)
        .agg(
            F.count(F.lit(1)).alias("n_events"),
            F.sum("data_amount_mb").alias("sum_data_amount_mb"),
            F.sum("effective_mb").alias("sum_effective_mb"),
            F.sum("duration_s").alias("sum_duration_s"),
            F.sum("energy_Wh").alias("sum_energy_Wh"),
            F.sum("tx_Wh").alias("sum_tx_Wh"),
            F.sum("rx_Wh").alias("sum_rx_Wh"),

            F.avg("bandwidth_req_mbps").alias("avg_bandwidth_req_mbps"),
            F.avg("throughput_mbps").alias("avg_throughput_mbps"),
            F.avg("jitter_ms").alias("avg_jitter_ms"),
            F.avg("packet_loss_percent").alias("avg_packet_loss_percent"),

            F.expr("percentile_approx(throughput_mbps, 0.5)").alias("p50_throughput_mbps"),
            F.expr("percentile_approx(packet_loss_percent, 0.95)").alias("p95_packet_loss_percent"),
        )
        .withColumn("window_start_ts", F.col("w.start"))
        .withColumn("window_end_ts", F.col("w.end"))
        .drop("w")
        .withColumn(
            "energy_Wh_per_effective_mb",
            F.when(F.col("sum_effective_mb") > 0, F.col("sum_energy_Wh") / F.col("sum_effective_mb"))
             .otherwise(F.lit(None))
        )
        .withColumn(
            "energy_Wh_per_s",
            F.when(F.col("sum_duration_s") > 0, F.col("sum_energy_Wh") / F.col("sum_duration_s"))
             .otherwise(F.lit(None))
        )
        .withColumn(
            "throughput_efficiency_ratio",
            F.when(F.col("avg_bandwidth_req_mbps") > 0, F.col("avg_throughput_mbps") / F.col("avg_bandwidth_req_mbps"))
             .otherwise(F.lit(None))
        )
        .withColumn("ingested_at_ts", F.current_timestamp())
    )

    partition_cols = [c.strip() for c in args.partition_cols.split(",") if c.strip()]

    writer = (gold
        .repartition(*[F.col(c) for c in partition_cols])  # helps avoid tiny files per partition
        .write
        .mode(args.mode)
        .partitionBy(*partition_cols)
    )

    if args.out_format == "delta":
        writer.format("delta").save(args.output)
    else:
        writer.parquet(args.output)

    spark.stop()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
