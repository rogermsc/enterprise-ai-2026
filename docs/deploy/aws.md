# AWS Deployment Guide

## Deploying the Enterprise AI Platform on AWS

### Overview

This guide covers deploying the platform on AWS using:

- **EKS**: Kubernetes cluster for container orchestration
- **RDS**: Managed PostgreSQL for persistent state
- **ElastiCache**: Managed Redis for caching and memory
- **Application Load Balancer**: Traffic management
- **AWS Secrets Manager**: Secure credential storage

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS REGION                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                           VPC (10.0.0.0/16)                              ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │                                                                          ││
│  │  ┌──────────────────────┐          ┌──────────────────────┐             ││
│  │  │   Public Subnet A    │          │   Public Subnet B    │             ││
│  │  │    (10.0.1.0/24)     │          │    (10.0.2.0/24)     │             ││
│  │  │  ┌────────────────┐  │          │  ┌────────────────┐  │             ││
│  │  │  │   NAT Gateway  │  │          │  │   NAT Gateway  │  │             ││
│  │  │  └────────────────┘  │          │  └────────────────┘  │             ││
│  │  └──────────────────────┘          └──────────────────────┘             ││
│  │                                                                          ││
│  │  ┌──────────────────────┐          ┌──────────────────────┐             ││
│  │  │  Private Subnet A    │          │  Private Subnet B    │             ││
│  │  │    (10.0.10.0/24)    │          │    (10.0.20.0/24)    │             ││
│  │  │                      │          │                      │             ││
│  │  │  ┌────────────────────────────────────────────────┐   │             ││
│  │  │  │                  EKS CLUSTER                    │   │             ││
│  │  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐        │   │             ││
│  │  │  │  │ Gateway │  │Orchestr│  │  Tools  │        │   │             ││
│  │  │  │  │  Pods   │  │  Pods   │  │  Pods   │        │   │             ││
│  │  │  │  └─────────┘  └─────────┘  └─────────┘        │   │             ││
│  │  │  └────────────────────────────────────────────────┘   │             ││
│  │  │                      │          │                      │             ││
│  │  └──────────────────────┘          └──────────────────────┘             ││
│  │                                                                          ││
│  │  ┌──────────────────────┐          ┌──────────────────────┐             ││
│  │  │   Data Subnet A      │          │   Data Subnet B      │             ││
│  │  │    (10.0.100.0/24)   │          │    (10.0.200.0/24)   │             ││
│  │  │  ┌─────────────────────────────────────────────────┐  │             ││
│  │  │  │  RDS PostgreSQL (Multi-AZ)                      │  │             ││
│  │  │  └─────────────────────────────────────────────────┘  │             ││
│  │  │  ┌─────────────────────────────────────────────────┐  │             ││
│  │  │  │  ElastiCache Redis (Cluster Mode)               │  │             ││
│  │  │  └─────────────────────────────────────────────────┘  │             ││
│  │  └──────────────────────┘          └──────────────────────┘             ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │      ALB        │  │ Secrets Manager │  │   CloudWatch    │             │
│  │  (Internet)     │  │  (Credentials)  │  │   (Logging)     │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0
- kubectl >= 1.28
- Helm >= 3.12
- Docker for building images

---

## Infrastructure Setup

### 1. VPC and Networking

```hcl
# terraform/aws/vpc.tf

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "ai-platform-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-2a", "us-west-2b"]
  private_subnets = ["10.0.10.0/24", "10.0.20.0/24"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  database_subnets = ["10.0.100.0/24", "10.0.200.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false
  one_nat_gateway_per_az = true

  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}
```

### 2. EKS Cluster

```hcl
# terraform/aws/eks.tf

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.0.0"

  cluster_name    = "ai-platform-${var.environment}"
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    general = {
      name = "general"

      instance_types = ["m6i.xlarge"]

      min_size     = 2
      max_size     = 10
      desired_size = 3

      labels = {
        role = "general"
      }
    }

    gpu = {
      name = "gpu"

      instance_types = ["g5.xlarge"]

      min_size     = 0
      max_size     = 4
      desired_size = 0

      labels = {
        role = "gpu"
      }

      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  manage_aws_auth_configmap = true

  aws_auth_roles = [
    {
      rolearn  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/Admin"
      username = "admin"
      groups   = ["system:masters"]
    },
  ]
}
```

### 3. RDS PostgreSQL

```hcl
# terraform/aws/rds.tf

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.0.0"

  identifier = "ai-platform-${var.environment}"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = "db.r6g.large"

  allocated_storage     = 100
  max_allocated_storage = 500

  db_name  = "aiplatform"
  username = "aiplatform"
  port     = 5432

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]

  maintenance_window              = "Mon:00:00-Mon:03:00"
  backup_window                   = "03:00-06:00"
  backup_retention_period         = 30
  delete_automated_backups        = false
  deletion_protection             = true
  skip_final_snapshot             = false
  final_snapshot_identifier_prefix = "ai-platform-final"

  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  parameters = [
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements,vector"
    }
  ]

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}
```

### 4. ElastiCache Redis

```hcl
# terraform/aws/elasticache.tf

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "ai-platform-${var.environment}"
  description                = "Redis cluster for AI platform"

  node_type            = "cache.r6g.large"
  num_cache_clusters   = 2
  port                 = 6379

  automatic_failover_enabled = true
  multi_az_enabled           = true

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result

  snapshot_retention_limit = 7
  snapshot_window          = "05:00-09:00"
  maintenance_window       = "mon:10:00-mon:14:00"

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}
```

### 5. Secrets Manager

```hcl
# terraform/aws/secrets.tf

resource "aws_secretsmanager_secret" "platform" {
  name = "ai-platform/${var.environment}/config"

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}

resource "aws_secretsmanager_secret_version" "platform" {
  secret_id = aws_secretsmanager_secret.platform.id
  secret_string = jsonencode({
    database_url     = "postgresql://${module.rds.db_instance_username}:${random_password.db.result}@${module.rds.db_instance_endpoint}/${module.rds.db_instance_name}"
    redis_url        = "rediss://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
    anthropic_api_key = var.anthropic_api_key
    jwt_secret        = random_password.jwt_secret.result
  })
}
```

---

## Kubernetes Deployment

### 1. Namespace and RBAC

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-platform
  labels:
    name: ai-platform

---
# k8s/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai-platform
  namespace: ai-platform
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/ai-platform-role
```

### 2. Gateway Deployment

```yaml
# k8s/gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  namespace: ai-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      serviceAccountName: ai-platform
      containers:
        - name: gateway
          image: YOUR_ECR_REPO/ai-platform-gateway:latest
          ports:
            - containerPort: 8080
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: platform-secrets
                  key: database_url
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: platform-secrets
                  key: redis_url
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: gateway
  namespace: ai-platform
spec:
  selector:
    app: gateway
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
```

### 3. Ingress with ALB

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-platform
  namespace: ai-platform
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:ACCOUNT:certificate/CERT_ID
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health/ready
spec:
  rules:
    - host: api.yourcompany.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gateway
                port:
                  number: 80
  tls:
    - hosts:
        - api.yourcompany.com
```

---

## Deployment Commands

### Initial Setup

```bash
# 1. Apply Terraform
cd terraform/aws
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars

# 2. Configure kubectl
aws eks update-kubeconfig --name ai-platform-prod --region us-west-2

# 3. Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=ai-platform-prod

# 4. Create secrets from Secrets Manager
kubectl create secret generic platform-secrets \
  --from-literal=database_url=$(aws secretsmanager get-secret-value --secret-id ai-platform/prod/config --query SecretString --output text | jq -r .database_url) \
  --from-literal=redis_url=$(aws secretsmanager get-secret-value --secret-id ai-platform/prod/config --query SecretString --output text | jq -r .redis_url) \
  -n ai-platform

# 5. Deploy application
kubectl apply -f k8s/
```

### Scaling

```bash
# Scale gateway pods
kubectl scale deployment gateway --replicas=5 -n ai-platform

# Enable HPA
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway
  namespace: ai-platform
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
EOF
```

---

## Monitoring Setup

### CloudWatch Container Insights

```bash
# Install CloudWatch agent
ClusterName=ai-platform-prod
RegionName=us-west-2
FluentBitHttpPort='2020'
FluentBitReadFromHead='Off'

curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml | \
  sed "s/{{cluster_name}}/${ClusterName}/g;s/{{region_name}}/${RegionName}/g" | \
  kubectl apply -f -
```

### Prometheus with Amazon Managed Prometheus

```bash
# Create AMP workspace
aws amp create-workspace --alias ai-platform-prod

# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/prometheus \
  -n monitoring \
  --set server.remoteWrite[0].url=https://aps-workspaces.us-west-2.amazonaws.com/workspaces/WORKSPACE_ID/api/v1/remote_write \
  --set server.remoteWrite[0].sigv4.region=us-west-2
```

---

## Security Checklist

- [ ] VPC endpoints for ECR, S3, Secrets Manager
- [ ] Security groups restrict access to necessary ports only
- [ ] RDS encryption at rest enabled
- [ ] Redis encryption at rest and in transit enabled
- [ ] IAM roles follow least privilege
- [ ] Pod security policies enforced
- [ ] Network policies restrict pod-to-pod traffic
- [ ] WAF rules configured on ALB
- [ ] CloudTrail logging enabled
- [ ] GuardDuty enabled for threat detection

---

## Cost Optimization

| Component | Instance Type | Monthly Cost (Estimate) |
|-----------|---------------|------------------------|
| EKS Cluster | N/A | $73 |
| Node Group (3x m6i.xlarge) | m6i.xlarge | $360 |
| RDS PostgreSQL | db.r6g.large | $350 |
| ElastiCache Redis | cache.r6g.large | $290 |
| ALB | N/A | $25 |
| Data Transfer | ~100GB | $9 |
| **Total** | | **~$1,107/month** |

### Cost Saving Tips

1. Use Savings Plans for consistent workloads
2. Enable cluster autoscaler for node optimization
3. Use spot instances for non-critical workloads
4. Reserved instances for RDS and ElastiCache
5. Enable S3 intelligent tiering for logs

---

## References

- [Azure Deployment](./azure.md)
- [GCP Deployment](./gcp.md)
- [On-Premises Deployment](./onprem.md)
