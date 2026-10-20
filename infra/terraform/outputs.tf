output "data_bucket_name" { value = aws_s3_bucket.data.bucket }
output "api_key_secret_arn" { value = aws_secretsmanager_secret.api_key.arn }
output "ecs_cluster_name" { value = aws_ecs_cluster.platform.name }
