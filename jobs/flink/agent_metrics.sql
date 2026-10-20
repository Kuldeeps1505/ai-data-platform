-- Flink SQL job specification for the advanced profile.
-- Package the matching flink-connector-kafka and ClickHouse JDBC connector JARs before submission.
CREATE TABLE agent_events (
  event_id STRING,
  event_type STRING,
  event_time TIMESTAMP_LTZ(3),
  run_id STRING,
  agent_id STRING,
  latency_ms INT,
  success BOOLEAN,
  WATERMARK FOR event_time AS event_time - INTERVAL '30' SECOND
) WITH (
  'connector' = 'kafka',
  'topic' = 'agent-events.v1',
  'properties.bootstrap.servers' = 'kafka:9092',
  'properties.group.id' = 'flink-agent-metrics-v1',
  'scan.startup.mode' = 'earliest-offset',
  'format' = 'json',
  'json.ignore-parse-errors' = 'false'
);

-- The production sink contract must upsert this keyed window into ClickHouse.
SELECT window_start, agent_id, COUNT(DISTINCT run_id) AS total_runs,
  COUNT(DISTINCT CASE WHEN success = FALSE OR event_type = 'agent.run_failed' THEN run_id END) AS failed_runs,
  AVG(latency_ms) AS average_latency_ms,
  SUM(CASE WHEN event_type = 'agent.tool_retry' THEN 1 ELSE 0 END) AS retry_count
FROM TABLE(TUMBLE(TABLE agent_events, DESCRIPTOR(event_time), INTERVAL '1' HOUR))
GROUP BY window_start, window_end, agent_id;
