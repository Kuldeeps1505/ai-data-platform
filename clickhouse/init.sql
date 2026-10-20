CREATE DATABASE IF NOT EXISTS ai_data_platform;

CREATE TABLE IF NOT EXISTS ai_data_platform.agent_metrics (
  window_start DateTime64(3, 'UTC'),
  agent_id String,
  total_runs UInt64,
  failed_runs UInt64,
  failure_rate Float64,
  average_latency_ms Nullable(Float64),
  p95_latency_ms Nullable(Float64),
  retry_count UInt64,
  dataset_version String,
  transformation_version String,
  quality_status String,
  generated_at DateTime64(3, 'UTC')
) ENGINE = ReplacingMergeTree(generated_at)
ORDER BY (agent_id, window_start);

CREATE TABLE IF NOT EXISTS ai_data_platform.stream_agent_metrics (
  window_start DateTime64(3, 'UTC'),
  agent_id String,
  total_runs UInt64,
  failed_runs UInt64,
  failure_rate Float64,
  average_latency_ms Float64,
  retry_count UInt64,
  generated_at DateTime64(3, 'UTC')
) ENGINE = ReplacingMergeTree(generated_at)
ORDER BY (agent_id, window_start);
