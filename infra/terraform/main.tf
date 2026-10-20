locals {
  name = "${var.project_name}-${var.environment}"
  tags = { Project = var.project_name, Environment = var.environment, ManagedBy = "terraform" }
}

resource "aws_s3_bucket" "data" {
  bucket_prefix = "${local.name}-data-"
  tags = local.tags
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" } bucket_key_enabled = true }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    id = "retention"
    status = "Enabled"
    filter { prefix = "" }
    transition { days = 30 storage_class = "STANDARD_IA" }
    expiration { days = 365 }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

resource "aws_secretsmanager_secret" "api_key" {
  name_prefix = "${local.name}-api-key-"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id = aws_secretsmanager_secret.api_key.id
  secret_string = var.api_key
}

resource "aws_cloudwatch_log_group" "api" {
  name = "/${local.name}/api"
  retention_in_days = 30
  tags = local.tags
}

resource "aws_iam_role" "task_execution" {
  name_prefix = "${local.name}-execution-"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "runtime" {
  name = "data-and-secret-access"
  role = aws_iam_role.task_execution.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"], Resource = [aws_s3_bucket.data.arn, "${aws_s3_bucket.data.arn}/*"] },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.api_key.arn }
  ] })
}

resource "aws_ecs_cluster" "platform" { name = local.name tags = local.tags }

resource "aws_ecs_task_definition" "api" {
  family = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode = "awsvpc"
  cpu = "512"
  memory = "1024"
  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn = aws_iam_role.task_execution.arn
  container_definitions = jsonencode([{ name = "api", image = var.container_image, essential = true,
    portMappings = [{ containerPort = 8000 }],
    secrets = [{ name = "API_KEY", valueFrom = aws_secretsmanager_secret.api_key.arn }],
    environment = [{ name = "RAW_STORAGE_PATH", value = "/data/raw" }, { name = "CURATED_STORAGE_PATH", value = "/data/curated" }],
    logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.api.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "ecs" } }
  }])
  tags = local.tags
}
