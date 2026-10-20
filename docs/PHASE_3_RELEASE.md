# Phase 3 Release and Recovery Runbook

## Pre-release checklist

1. Run unit tests and the live Compose workflow.
2. Confirm contract, duplicate, malformed-event, replay, reconciliation, and evaluation scenario demonstrations pass.
3. Record benchmark workload, environment, configuration, and measured output.
4. Review CloudWatch/Grafana alerts, audit records, retention setting, and known limitations.
5. Build an immutable tagged image and run Terraform `plan` with the target account and region.

## Deploy

1. Push the tagged image to ECR.
2. Set `TF_VAR_api_key` from a secret manager or secure CI variable.
3. Copy `terraform.tfvars.example` outside source control and fill the existing VPC, private subnet, and security group identifiers.
4. Run `terraform init`, `terraform plan`, then a reviewed `terraform apply`.
5. Deploy the ECS task definition revision through the approved service/load-balancer configuration.
6. Verify `/health`, `/ready`, metrics scrape, ingest one synthetic event, and reconcile its time window.

## Rollback

- Roll back ECS to the preceding task-definition revision.
- Do not delete the S3 bucket, Kafka topic, PostgreSQL data, or evaluation records during rollback.
- If a transformation is faulty, publish a corrected transformation version and request a bounded replay; preserve both versions and audit the decision.

## Known limitations

- Terraform provides the secure storage, secret, IAM, logs, cluster, and task-definition baseline. It intentionally does not create a VPC, ALB, RDS, or MSK cluster because those choices need account-level network and cost decisions.
- Local Compose remains the acceptance environment; AWS deployment requires supplied account access, network identifiers, image registry, and an approved rollout target.
