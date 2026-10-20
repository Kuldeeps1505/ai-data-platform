"""Spark historical recompute contract.

Submit to the standalone cluster after adding the platform dependency image that contains
PyArrow and the ClickHouse driver: spark-submit --master spark://spark-master:7077
/opt/spark/jobs/recompute_metrics.py --input /data/raw --output /data/recomputed
"""
import argparse
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

spark = SparkSession.builder.appName("ai-data-platform-recompute").getOrCreate()
events = spark.read.parquet(args.input)
metrics = (events.withColumn("window_start", F.date_trunc("hour", "event_time"))
  .groupBy("window_start", "agent_id")
  .agg(F.countDistinct("run_id").alias("total_runs"),
       F.countDistinct(F.when((F.col("success") == F.lit(False)) | (F.col("event_type") == "agent.run_failed"), F.col("run_id"))).alias("failed_runs"),
       F.avg("latency_ms").alias("average_latency_ms"),
       F.expr("percentile_approx(latency_ms, 0.95)").alias("p95_latency_ms"),
       F.sum(F.when(F.col("event_type") == "agent.tool_retry", 1).otherwise(0)).alias("retry_count"))
  .withColumn("failure_rate", F.when(F.col("total_runs") > 0, F.col("failed_runs") / F.col("total_runs")).otherwise(F.lit(0.0))))
metrics.write.mode("overwrite").parquet(args.output)
spark.stop()
