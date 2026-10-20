# Flink streaming job contract

The Flink cluster is included under the `advanced` Compose profile. The production stream job must consume `agent-events.v1`, use `event_time` watermarks, aggregate per-agent hourly metrics, write idempotently to ClickHouse, and emit late-event/retraction metrics. Keep the existing Python consumer as the verified baseline until a packaged Flink job with the Kafka and ClickHouse connector JAR versions is built and tested against the selected Flink release.

Start the cluster with:

```powershell
docker compose --profile advanced up -d flink-jobmanager flink-taskmanager
```

The Flink dashboard is at `http://localhost:8081`.
