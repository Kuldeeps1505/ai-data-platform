# Phase 3 Security and Governance

## Data classification and minimization

- Raw events retain operational metadata only; prompts and tool payloads are not collected by the baseline contract.
- Evaluation scenarios store a sanitized reference, never a raw production payload by default.
- The built-in sanitizer masks e-mail addresses, telephone-like strings, and payment-card-like strings. It is a baseline control, not a complete DLP solution; add domain-specific redaction before production use.

## Access and audit

- API mutation endpoints support `X-API-Key`; set `API_KEY` outside source control.
- Health, metrics, documentation, and the local navigation page stay unauthenticated so orchestrators can probe service health.
- Scenario creation and evaluation runs create immutable audit records with action, actor, resource, time, and metadata.
- In AWS, API credentials belong in Secrets Manager; the ECS runtime policy is limited to the platform bucket and that secret.

## Retention and correction

- Local development keeps Docker volumes until explicitly removed.
- The Terraform baseline uses versioned, KMS-encrypted S3 storage, moves objects to Standard-IA after 30 days, and expires them after 365 days. Change this only through a reviewed retention decision.
- Corrections are new versioned datasets/scenarios; do not silently overwrite historical outputs. Handle deletion requests through an auditable deletion workflow before production adoption.

## Production controls still required

- Replace API keys with workload identity/OIDC and role-based authorization.
- Put services in private subnets behind a TLS-terminating load balancer.
- Add an approved KMS customer-managed key, backup/restore testing, vulnerability scanning, and formal data-subject deletion procedures.
