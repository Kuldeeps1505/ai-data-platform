package com.aidataplatform.flink;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.HashSet;
import java.util.Set;
import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.java.functions.KeySelector;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.util.Collector;

/** Kafka event-time aggregation with a ClickHouse recent-metrics sink. */
public final class AgentMetricsJob {
  private static final String BOOTSTRAP = System.getenv().getOrDefault("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092");
  private static final String CLICKHOUSE_URL = System.getenv().getOrDefault("CLICKHOUSE_JDBC_URL", "jdbc:ch:http://clickhouse:8123/ai_data_platform?user=platform&password=platform");

  public static void main(String[] args) throws Exception {
    StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
    env.enableCheckpointing(30_000);

    KafkaSource<String> source = KafkaSource.<String>builder()
      .setBootstrapServers(BOOTSTRAP).setTopics("agent-events.v1")
      .setGroupId("flink-agent-metrics-v1").setStartingOffsets(org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer.earliest())
      .setValueOnlyDeserializer(new SimpleStringSchema()).build();

    DataStream<AgentEvent> events = env.fromSource(source,
      WatermarkStrategy.<String>forBoundedOutOfOrderness(Duration.ofSeconds(30))
        .withTimestampAssigner((SerializableTimestampAssigner<String>) (value, ignored) -> parse(value).eventTimeMillis),
      "agent-events")
      .map(AgentMetricsJob::parse).returns(TypeInformation.of(AgentEvent.class));

    SingleOutputStreamOperator<Metric> metrics = events.keyBy((KeySelector<AgentEvent, String>) value -> value.agentId)
      .window(TumblingEventTimeWindows.of(Time.hours(1))).allowedLateness(Time.seconds(30))
      .process(new HourlyMetrics()).returns(TypeInformation.of(Metric.class));
    metrics.addSink(new ClickHouseSink()).name("clickhouse-recent-metrics");
    env.execute("agent-event-time-metrics");
  }

  private static AgentEvent parse(String value) {
    try {
      JsonNode node = new ObjectMapper().readTree(value);
      return new AgentEvent(node.path("event_id").asText(), node.path("event_type").asText(),
        node.path("run_id").asText(), node.path("agent_id").asText(), node.path("latency_ms").asLong(),
        node.path("success").asBoolean(), OffsetDateTime.parse(node.path("event_time").asText().replace(' ', 'T')).toInstant().toEpochMilli());
    } catch (Exception error) { throw new IllegalArgumentException("invalid agent event", error); }
  }

  public static final class AgentEvent {
    public String eventId, eventType, runId, agentId; public long latencyMs, eventTimeMillis; public boolean success;
    public AgentEvent() {}
    AgentEvent(String eventId, String eventType, String runId, String agentId, long latencyMs, boolean success, long eventTimeMillis) {
      this.eventId=eventId; this.eventType=eventType; this.runId=runId; this.agentId=agentId; this.latencyMs=latencyMs; this.success=success; this.eventTimeMillis=eventTimeMillis;
    }
  }
  public static final class Metric {
    public long windowStart; public String agentId; public int totalRuns, failedRuns, retryCount; public double averageLatency;
    public Metric() {}
    Metric(long windowStart, String agentId, int totalRuns, int failedRuns, int retryCount, double averageLatency) { this.windowStart=windowStart; this.agentId=agentId; this.totalRuns=totalRuns; this.failedRuns=failedRuns; this.retryCount=retryCount; this.averageLatency=averageLatency; }
  }
  static final class HourlyMetrics extends ProcessWindowFunction<AgentEvent, Metric, String, org.apache.flink.streaming.api.windowing.windows.TimeWindow> {
    @Override public void process(String agentId, Context context, Iterable<AgentEvent> values, Collector<Metric> out) {
      Set<String> runs = new HashSet<>(), failed = new HashSet<>(); int retries = 0, count = 0; long latency = 0;
      for (AgentEvent event : values) { runs.add(event.runId); if (!event.success || "agent.run_failed".equals(event.eventType)) failed.add(event.runId); if ("agent.tool_retry".equals(event.eventType)) retries++; latency += event.latencyMs; count++; }
      out.collect(new Metric(context.window().getStart(), agentId, runs.size(), failed.size(), retries, count == 0 ? 0 : ((double) latency / count)));
    }
  }
  static final class ClickHouseSink extends RichSinkFunction<Metric> {
    private transient Connection connection; private transient PreparedStatement statement;
    @Override public void open(Configuration config) throws Exception {
      connection = DriverManager.getConnection(CLICKHOUSE_URL);
      statement = connection.prepareStatement("INSERT INTO stream_agent_metrics (window_start, agent_id, total_runs, failed_runs, failure_rate, average_latency_ms, retry_count, generated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
    }
    @Override public void invoke(Metric metric, Context ignored) throws Exception {
      statement.setTimestamp(1, new Timestamp(metric.windowStart)); statement.setString(2, metric.agentId); statement.setInt(3, metric.totalRuns); statement.setInt(4, metric.failedRuns);
      statement.setDouble(5, metric.totalRuns == 0 ? 0 : ((double) metric.failedRuns / metric.totalRuns)); statement.setDouble(6, metric.averageLatency); statement.setInt(7, metric.retryCount); statement.setTimestamp(8, Timestamp.from(Instant.now())); statement.executeUpdate();
    }
    @Override public void close() throws Exception { if (statement != null) statement.close(); if (connection != null) connection.close(); }
  }
}
