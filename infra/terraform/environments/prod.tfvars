# =============================================================================
# Production Environment Configuration
# =============================================================================

environment = "prod"
aws_region  = "us-west-2"

# Networking
vpc_cidr         = "10.0.0.0/16"
private_subnets  = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]
public_subnets   = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
database_subnets = ["10.0.100.0/24", "10.0.110.0/24", "10.0.120.0/24"]

# Kubernetes
kubernetes_version = "1.28"
node_groups = {
  general = {
    instance_types = ["m6i.xlarge"]
    min_size       = 3
    max_size       = 20
    desired_size   = 5
    labels         = { role = "general" }
  }
  compute = {
    instance_types = ["c6i.2xlarge"]
    min_size       = 2
    max_size       = 10
    desired_size   = 3
    labels         = { role = "compute" }
  }
}

# Database
rds_instance_class = "db.r6g.xlarge"

# Redis
redis_node_type = "cache.r6g.large"

# Application
image_repository = "YOUR_ECR_REPO.dkr.ecr.us-west-2.amazonaws.com/ai-platform"
image_tag        = "v1.0.0"

# Note: Set anthropic_api_key via environment variable:
# export TF_VAR_anthropic_api_key="your-api-key"
