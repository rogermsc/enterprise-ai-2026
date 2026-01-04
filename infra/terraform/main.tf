# =============================================================================
# Enterprise AI Platform - Terraform Root Module
# =============================================================================
#
# This Terraform configuration deploys the complete AI Platform infrastructure.
# Supports AWS, Azure, and GCP through provider-specific modules.
#
# Usage:
#   terraform init
#   terraform plan -var-file=environments/prod.tfvars
#   terraform apply -var-file=environments/prod.tfvars
#
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Uncomment for remote state (recommended for production)
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "ai-platform/terraform.tfstate"
  #   region         = "us-west-2"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

# =============================================================================
# Providers
# =============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_ca_certificate)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_ca_certificate)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# =============================================================================
# Random Resources
# =============================================================================

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "random_password" "redis" {
  length  = 32
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

# =============================================================================
# VPC Module
# =============================================================================

module "vpc" {
  source = "./modules/vpc"

  name        = "ai-platform-${var.environment}"
  environment = var.environment
  cidr        = var.vpc_cidr

  azs              = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets  = var.private_subnets
  public_subnets   = var.public_subnets
  database_subnets = var.database_subnets
}

# =============================================================================
# EKS Module
# =============================================================================

module "eks" {
  source = "./modules/eks"

  cluster_name    = "ai-platform-${var.environment}"
  cluster_version = var.kubernetes_version
  environment     = var.environment

  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids

  node_groups = var.node_groups
}

# =============================================================================
# RDS Module
# =============================================================================

module "rds" {
  source = "./modules/rds"

  identifier  = "ai-platform-${var.environment}"
  environment = var.environment

  vpc_id              = module.vpc.vpc_id
  database_subnets    = module.vpc.database_subnet_ids
  allowed_cidr_blocks = module.vpc.private_subnet_cidrs

  instance_class = var.rds_instance_class
  database_name  = "aiplatform"
  username       = "aiplatform"
  password       = random_password.database.result

  multi_az                   = var.environment == "prod"
  backup_retention_period    = var.environment == "prod" ? 30 : 7
  deletion_protection        = var.environment == "prod"
  performance_insights       = var.environment == "prod"
}

# =============================================================================
# Redis Module
# =============================================================================

module "redis" {
  source = "./modules/redis"

  name        = "ai-platform-${var.environment}"
  environment = var.environment

  vpc_id              = module.vpc.vpc_id
  private_subnets     = module.vpc.private_subnet_ids
  allowed_cidr_blocks = module.vpc.private_subnet_cidrs

  node_type      = var.redis_node_type
  num_cache_nodes = var.environment == "prod" ? 2 : 1
  auth_token     = random_password.redis.result
}

# =============================================================================
# Secrets Manager
# =============================================================================

resource "aws_secretsmanager_secret" "platform" {
  name                    = "ai-platform/${var.environment}/config"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
}

resource "aws_secretsmanager_secret_version" "platform" {
  secret_id = aws_secretsmanager_secret.platform.id
  secret_string = jsonencode({
    database_url      = "postgresql://${module.rds.username}:${random_password.database.result}@${module.rds.endpoint}/${module.rds.database_name}"
    redis_url         = "rediss://:${random_password.redis.result}@${module.redis.endpoint}:6379"
    jwt_secret        = random_password.jwt_secret.result
    anthropic_api_key = var.anthropic_api_key
  })
}

# =============================================================================
# Helm Release - AI Platform
# =============================================================================

resource "helm_release" "ai_platform" {
  name       = "ai-platform"
  namespace  = "ai-platform"
  chart      = "${path.module}/../helm/ai-platform"

  create_namespace = true
  wait             = true
  timeout          = 600

  values = [
    templatefile("${path.module}/helm-values.yaml.tpl", {
      environment       = var.environment
      image_repository  = var.image_repository
      image_tag         = var.image_tag
      secret_arn        = aws_secretsmanager_secret.platform.arn
      replicas          = var.environment == "prod" ? 3 : 1
    })
  ]

  depends_on = [
    module.eks,
    module.rds,
    module.redis,
  ]
}

# =============================================================================
# Outputs
# =============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
}

output "secret_arn" {
  description = "Secrets Manager ARN"
  value       = aws_secretsmanager_secret.platform.arn
}
