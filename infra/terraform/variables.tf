variable "aws_region" { type = string }
variable "project_name" { type = string, default = "ai-data-platform" }
variable "environment" { type = string, default = "test" }
variable "api_key" { type = string, sensitive = true }
variable "container_image" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "security_group_ids" { type = list(string) }
