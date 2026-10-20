# Synthetic Core Demo

This walkthrough demonstrates the default local path only. It uses synthetic
data and the local development API key. It has not yet been automated as a
multi-service integration test; see [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

## Start the platform

From the repository root in PowerShell:

```powershell
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Wait for the API to report healthy. The command below creates a unique event,
submits it, and submits the exact same payload again to demonstrate duplicate
handling:

```powershell
$base = "http://localhost:8000"
$headers = @{ "X-API-Key" = "local-development-key" }
$now = [DateTime]::UtcNow
$windowStart = $now.Date
$windowEnd = $windowStart.AddDays(1)
$runId = "demo-run-$([guid]::NewGuid().ToString('N'))"
$event = @{
    event_id = "demo-event-$([guid]::NewGuid().ToString('N'))"
    schema_version = 1
    event_type = "agent.tool_completed"
    event_time = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
    run_id = $runId
    agent_id = "demo-agent"
    tool_name = "synthetic_lookup"
    latency_ms = 125
    success = $true
    model_version = "demo-model-v1"
    prompt_version = "demo-prompt-v1"
}
$body = $event | ConvertTo-Json

$first = Invoke-RestMethod -Method Post -Uri "$base/v1/events" `
    -Headers $headers -ContentType "application/json" -Body $body
$duplicate = Invoke-RestMethod -Method Post -Uri "$base/v1/events" `
    -Headers $headers -ContentType "application/json" -Body $body
$first
$duplicate
```

Expected response fields: the first call has `status: accepted`; the second
has `status: duplicate`. The API returns HTTP 201 for the first request and
HTTP 200 for the exact duplicate. Reusing an event ID with a different payload
is a conflict (HTTP 409), not an update.

Build and inspect a curated metrics dataset:

```powershell
$dataset = Invoke-RestMethod -Method Post `
    -Uri "$base/v1/datasets/agent-metrics" -Headers $headers
$dataset
Invoke-RestMethod -Method Get `
    -Uri "$base/v1/provenance/runs/$runId" -Headers $headers
```

The dataset response should report `quality_status: passed`; its `dataset_id`
is unique and its output is versioned. The provenance response should include
the submitted event ID and its raw storage path. These outcomes depend on the
local services being available; the repository does not yet have an automated
integration test asserting the full path.

Inspect stream and batch reconciliation for the current UTC day:

```powershell
$start = $windowStart.ToString("yyyy-MM-ddTHH:mm:ssZ")
$end = $windowEnd.ToString("yyyy-MM-ddTHH:mm:ssZ")
$startQuery = [uri]::EscapeDataString($start)
$endQuery = [uri]::EscapeDataString($end)
$range = "start_time=$startQuery&end_time=$endQuery"

Invoke-RestMethod -Method Get `
    -Uri "$base/v1/streaming/metrics?$range" -Headers $headers
Invoke-RestMethod -Method Post `
    -Uri "$base/v1/reconciliation?$range" -Headers $headers
```

Reconciliation reports differences; it does not silently rewrite history. A
`matched` result depends on the consumer having processed the event and on
streaming and batch data covering the same event-time interval. Investigate a
mismatch rather than treating it as a successful check.

## Optional evaluation record

This records a synthetic human-reviewed scenario; it does not run or score an
AI model:

```powershell
$scenarioBody = @{
    source_run_id = $runId
    source_event_id = $event.event_id
    failure_category = "synthetic_demo"
    expected_behavior = "The tool call completes successfully."
    evaluation_method = "human_review"
    source_dataset_version = $dataset.dataset_id
    sanitized_input = "Synthetic input for the demo; no production data."
} | ConvertTo-Json
$scenario = Invoke-RestMethod -Method Post `
    -Uri "$base/v1/evaluations/scenarios" -Headers $headers `
    -ContentType "application/json" -Body $scenarioBody

$evaluationBody = @{
    scenario_id = $scenario.scenario_id
    observed_behavior = "The synthetic tool call completed successfully."
    outcome = "passed"
    score = 100
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$base/v1/evaluations/runs" `
    -Headers $headers -ContentType "application/json" -Body $evaluationBody
```

The recorded result is an example audit/evaluation record, not evidence of
model quality or evaluation repeatability.

## Failure and recovery exercise

Use a second terminal while the stack is running:

```powershell
docker compose stop consumer
```

Submit additional unique synthetic events using the same event shape above,
then restart the consumer:

```powershell
docker compose start consumer
```

Inspect whether lag drains after processing resumes, then rerun reconciliation
for the affected event-time range. The consumer's metrics endpoint is
unavailable while its container is stopped, so Grafana may show a scrape
failure or stale lag value during the outage. Record the observed lag and
recovery time; this is an exercise to perform and document, not a pre-verified
recovery claim.

## Stop

```powershell
docker compose down
```

This preserves named volumes. Do not remove them if you need to inspect the
demo's persisted state.
