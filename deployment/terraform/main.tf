# HELIOS OS + SEVRA AI
# Terraform Infrastructure Provisioning

provider "aws" {
  region = "us-east-1"
}

resource "aws_eks_cluster" "helios_cluster" {
  name     = "helios-production"
  role_arn = aws_iam_role.eks_cluster_role.arn

  vpc_config {
    subnet_ids = ["subnet-12345", "subnet-67890"]
  }
}

resource "aws_db_instance" "helios_postgres" {
  allocated_storage    = 100
  engine               = "postgres"
  engine_version       = "16.2"
  instance_class       = "db.t4g.large"
  identifier           = "helios-central-db"
  username             = "postgres"
  password             = var.db_password
  parameter_group_name = "default.postgres16"
  skip_final_snapshot  = false
  multi_az             = true
  storage_encrypted    = true
}

resource "aws_elasticache_cluster" "helios_redis" {
  cluster_id           = "helios-event-bus"
  engine               = "redis"
  node_type            = "cache.m6g.large"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

variable "db_password" {
  description = "The password for the PostgreSQL database"
  type        = string
  sensitive   = true
}
