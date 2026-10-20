CREATE TABLE IF NOT EXISTS customer_context (
  customer_id TEXT PRIMARY KEY,
  tier TEXT NOT NULL,
  account_status TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO customer_context (customer_id, tier, account_status)
VALUES ('demo-customer-1', 'standard', 'active')
ON CONFLICT (customer_id) DO NOTHING;

CREATE PUBLICATION ai_data_platform_publication FOR TABLE customer_context;
