# Remaining Work Guide

This guide covers the three items that require external environment access or a concrete source-system decision. Do not place credentials, AWS account IDs, production data, or secret values in Git.

## 1. Validate Terraform locally

### Prerequisites

- Install Terraform 1.6 or newer from the official HashiCorp distribution.
- Install and authenticate the AWS CLI only if you intend to run `plan` or `apply`.

### Commands

Run from the repository root:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
```

If formatting reports changes, run `terraform -chdir=infra/terraform fmt -recursive`, review the diff, then commit the formatting-only changes.

### Expected result

- `init` downloads the AWS provider.
- `fmt -check` exits successfully.
- `validate` reports that the configuration is valid without contacting AWS.

## 2. Prepare AWS deployment

### Decisions required from the platform owner

| Decision | Required value | Why it is needed |
|---|---|---|
| AWS account and region | Account with deployment approval; preferred region such as `ap-south-1` | Determines billing, residency, and resource location. |
| Network | Existing VPC ID, at least two private subnet IDs, security-group ID | Terraform intentionally does not create account-wide network infrastructure. |
| Image registry | ECR repository URI and immutable image tag | ECS needs a container image to run. |
| Database | Managed PostgreSQL/RDS endpoint, credentials secret, security group | The current local PostgreSQL container is not a cloud database. |
| Streaming | Managed Kafka/MSK choice and bootstrap addresses, or an approved alternative | The current local Kafka broker is for development only. |
| Public access | ALB/domain/TLS certificate plan, or private-only API access | Determines safe API exposure. |
| Retention | Approved raw, curated, evaluation, log, and backup retention durations | Must align with policy and cost requirements. |

### Secure AWS authentication

Use AWS IAM Identity Center, a short-lived assumed role, or CI workload identity. Do not create or share long-lived administrator access keys.

Verify identity before planning:

```powershell
aws sts get-caller-identity
```

### Build and push an immutable image

Replace placeholders with approved values:

```powershell
aws ecr create-repository --repository-name ai-data-platform
aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com
docker build -t ai-data-platform:<GIT_SHA> .
docker tag ai-data-platform:<GIT_SHA> <ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/ai-data-platform:<GIT_SHA>
docker push <ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/ai-data-platform:<GIT_SHA>
```

Use a Git commit SHA, release version, or another immutable tag. Never deploy `latest`.

### Prepare Terraform variables

Copy [terraform.tfvars.example](../infra/terraform/terraform.tfvars.example) outside source control and fill the non-secret values. Set the secret only as a session/CI variable:

```powershell
$env:TF_VAR_api_key = '<long-random-secret>'
terraform -chdir=infra/terraform plan -var-file='C:\secure-path\platform.tfvars'
```

Review the plan with an authorized owner. Only then run:

```powershell
terraform -chdir=infra/terraform apply -var-file='C:\secure-path\platform.tfvars'
```

### Required extension before production apply

The checked-in Terraform establishes a secure storage and ECS task-definition baseline. Add or approve the following before exposing a production service:

1. RDS PostgreSQL with private networking, encrypted storage, backups, and a secret reference used by `DATABASE_URL`.
2. Amazon MSK or another approved Kafka provider; update `KAFKA_BOOTSTRAP_SERVERS` and configure authentication/TLS.
3. Private ECS service plus ALB, HTTPS certificate, health checks, listener rules, autoscaling, and WAF policy if internet-facing.
4. VPC endpoints/NAT policy for AWS APIs and container image retrieval.
5. CloudWatch alarms routed to the team’s incident channel.
6. A customer-managed KMS key if required by organization policy.
7. A CI/CD role with least privilege and a reviewed rollout/rollback strategy.

### Cloud acceptance test

After deployment, use a non-sensitive synthetic event and verify:

1. `/health` and `/ready` are healthy.
2. An authenticated event is accepted.
3. Kafka consumer lag returns to zero.
4. A curated dataset is published with `quality_status: passed`.
5. Reconciliation reports `matched: true`.
6. Grafana/CloudWatch show ingestion, freshness, quality, and error signals.
7. A sanitized evaluation scenario and audit record can be created.
8. Roll back one task-definition revision and prove data is retained.

## 3. Decide and implement CDC with Debezium

CDC is deliberately not enabled without a source-owner agreement. It should be added only when database changes are a required platform input.

### Required source-system contract

Before provisioning Debezium, document:

- Source PostgreSQL owner and database name.
- Tables and columns explicitly allowed for capture.
- Primary-key and delete/update semantics for each table.
- PII classification, redaction requirements, and retention policy.
- Expected schema-change process and compatibility policy.
- Replication-slot ownership, WAL-retention capacity, and recovery owner.
- Kafka topic names, ACLs, partitions, retention, and consumer ownership.
- Snapshot policy and acceptable load window.

### PostgreSQL source prerequisites

The source owner must configure logical replication and grant a least-privilege replication user. Exact commands vary by managed database and must be approved by that owner. Validate:

- `wal_level = logical`.
- Adequate `max_replication_slots` and `max_wal_senders`.
- Publication restricted to an allow-list of approved tables.
- TLS connection and secret storage.
- Monitoring for replication-slot lag and WAL growth.

### Recommended connector skeleton

Use a Debezium PostgreSQL connector with a table allow-list and a dedicated topic prefix. Do not use wildcard table capture in production.

```json
{
  "name": "approved-postgres-source",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "plugin.name": "pgoutput",
    "database.hostname": "<private-db-host>",
    "database.port": "5432",
    "database.user": "${secrets:cdc_user}",
    "database.password": "${secrets:cdc_password}",
    "database.dbname": "<approved_database>",
    "topic.prefix": "approved_source",
    "table.include.list": "public.approved_table",
    "snapshot.mode": "initial",
    "slot.name": "ai_data_platform_cdc",
    "publication.autocreate.mode": "disabled"
  }
}
```

### CDC acceptance test

1. Insert, update, and delete an approved synthetic record.
2. Confirm exactly the expected change events appear in the approved Kafka topic.
3. Confirm excluded tables and protected columns never appear.
4. Restart the connector and verify it resumes from its saved offset.
5. Simulate consumer downtime and verify lag recovery without source-data loss.
6. Perform a compatible schema change, validate the contract, and verify consumer behavior.
7. Measure connector lag, Kafka lag, database replication-slot lag, and WAL growth.

## Completion evidence

Keep the following in the project release record:

- Terraform plan and apply review evidence.
- Cloud acceptance-test results and actual benchmark measurements.
- Architecture decision records for network, RDS, Kafka, retention, and CDC.
- Security review approval and secret rotation owner.
- CDC source-owner approval, allow-list, and recovery runbook.
- Final known limitations and rollback test evidence.
