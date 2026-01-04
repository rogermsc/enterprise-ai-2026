# GCP Deployment Guide

## Deploying the Enterprise AI Platform on Google Cloud

### Overview

This guide covers deploying the platform on GCP using:

- **GKE**: Google Kubernetes Engine for container orchestration
- **Cloud SQL**: Managed PostgreSQL with HA
- **Memorystore**: Managed Redis for caching
- **Cloud Load Balancing**: Global load balancing with Cloud Armor
- **Secret Manager**: Secure credential storage

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GCP PROJECT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        VPC Network                                       ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │                                                                          ││
│  │  ┌────────────────────────────────────────────────────────────────────┐ ││
│  │  │                    Global Load Balancer                             │ ││
│  │  │                    + Cloud Armor WAF                                │ ││
│  │  └────────────────────────────────────────────────────────────────────┘ ││
│  │                               │                                          ││
│  │                               ▼                                          ││
│  │  ┌──────────────────────┐          ┌──────────────────────┐             ││
│  │  │   Subnet: us-west1   │          │   Subnet: us-east1   │             ││
│  │  │   (10.0.0.0/20)      │          │   (10.1.0.0/20)      │             ││
│  │  │                      │          │                      │             ││
│  │  │  ┌────────────────────────────────────────────────┐   │             ││
│  │  │  │              GKE AUTOPILOT CLUSTER             │   │             ││
│  │  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐        │   │             ││
│  │  │  │  │ Gateway │  │Orchestr│  │  Tools  │        │   │             ││
│  │  │  │  │  Pods   │  │  Pods   │  │  Pods   │        │   │             ││
│  │  │  │  └─────────┘  └─────────┘  └─────────┘        │   │             ││
│  │  │  └────────────────────────────────────────────────┘   │             ││
│  │  │                      │          │                      │             ││
│  │  └──────────────────────┘          └──────────────────────┘             ││
│  │                                                                          ││
│  │  ┌────────────────────────────────────────────────────────────────────┐ ││
│  │  │                    Private Services Access                          │ ││
│  │  │  ┌──────────────────────────────────────────────────────────────┐  │ ││
│  │  │  │  Cloud SQL PostgreSQL (Regional HA)                          │  │ ││
│  │  │  │  - Primary: us-west1-a                                        │  │ ││
│  │  │  │  - Standby: us-west1-b                                        │  │ ││
│  │  │  └──────────────────────────────────────────────────────────────┘  │ ││
│  │  │  ┌──────────────────────────────────────────────────────────────┐  │ ││
│  │  │  │  Memorystore Redis (Standard)                                 │  │ ││
│  │  │  │  - us-west1                                                   │  │ ││
│  │  │  └──────────────────────────────────────────────────────────────┘  │ ││
│  │  └────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Cloud Monitoring│  │  Secret Manager │  │Artifact Registry│             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- gcloud CLI configured with appropriate project
- Terraform >= 1.5.0
- kubectl >= 1.28
- Helm >= 3.12
- Docker for building images

---

## Infrastructure Setup

### 1. Project and APIs

```hcl
# terraform/gcp/project.tf

locals {
  required_apis = [
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}
```

### 2. VPC Network

```hcl
# terraform/gcp/network.tf

resource "google_compute_network" "main" {
  name                    = "vpc-ai-platform-${var.environment}"
  project                 = var.project_id
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "subnet-ai-platform-${var.environment}"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.main.id
  ip_cidr_range = "10.0.0.0/20"

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.4.0.0/14"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.8.0.0/20"
  }

  private_ip_google_access = true
}

# Private services access for Cloud SQL and Memorystore
resource "google_compute_global_address" "private_services" {
  name          = "private-services-ip"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
}
```

### 3. GKE Autopilot Cluster

```hcl
# terraform/gcp/gke.tf

resource "google_container_cluster" "main" {
  name     = "gke-ai-platform-${var.environment}"
  project  = var.project_id
  location = var.region

  # Autopilot mode
  enable_autopilot = true

  network    = google_compute_network.main.id
  subnetwork = google_compute_subnetwork.main.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All"
    }
  }

  release_channel {
    channel = "REGULAR"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Enable Binary Authorization
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  # Enable Shielded Nodes
  node_pool_defaults {
    node_config_defaults {
      gcfs_config {
        enabled = true
      }
    }
  }

  deletion_protection = true
}
```

### 4. Cloud SQL PostgreSQL

```hcl
# terraform/gcp/cloudsql.tf

resource "google_sql_database_instance" "main" {
  name             = "sql-ai-platform-${var.environment}"
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_15"

  depends_on = [google_service_networking_connection.private_services]

  settings {
    tier              = "db-custom-4-16384"
    availability_type = "REGIONAL"
    disk_size         = 100
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      location                       = var.region
      backup_retention_settings {
        retained_backups = 30
      }
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 4096
      record_application_tags = true
      record_client_address   = true
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "main" {
  name     = "aiplatform"
  project  = var.project_id
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "main" {
  name     = "aiplatform"
  project  = var.project_id
  instance = google_sql_database_instance.main.name
  password = random_password.postgresql.result
}
```

### 5. Memorystore Redis

```hcl
# terraform/gcp/redis.tf

resource "google_redis_instance" "main" {
  name           = "redis-ai-platform-${var.environment}"
  project        = var.project_id
  region         = var.region
  tier           = "STANDARD_HA"
  memory_size_gb = 4

  authorized_network = google_compute_network.main.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version = "REDIS_7_0"
  display_name  = "AI Platform Redis"

  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }

  labels = {
    environment = var.environment
    project     = "ai-platform"
  }

  depends_on = [google_service_networking_connection.private_services]
}
```

### 6. Secret Manager

```hcl
# terraform/gcp/secrets.tf

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    project     = "ai-platform"
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql://${google_sql_user.main.name}:${random_password.postgresql.result}@${google_sql_database_instance.main.private_ip_address}/${google_sql_database.main.name}"
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "redis-url"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "rediss://:${google_redis_instance.main.auth_string}@${google_redis_instance.main.host}:${google_redis_instance.main.port}"
}

# Workload Identity for secret access
resource "google_service_account" "platform" {
  account_id   = "ai-platform-${var.environment}"
  display_name = "AI Platform Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.platform.email}"
}

resource "google_service_account_iam_binding" "workload_identity" {
  service_account_id = google_service_account.platform.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[ai-platform/ai-platform]",
  ]
}
```

### 7. Cloud Load Balancing with Cloud Armor

```hcl
# terraform/gcp/loadbalancer.tf

resource "google_compute_security_policy" "main" {
  name    = "waf-ai-platform-${var.environment}"
  project = var.project_id

  # OWASP ModSecurity Core Rule Set
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-stable')"
      }
    }
    description = "SQL injection protection"
  }

  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('xss-stable')"
      }
    }
    description = "XSS protection"
  }

  rule {
    action   = "deny(403)"
    priority = 1002
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('rce-stable')"
      }
    }
    description = "Remote code execution protection"
  }

  # Rate limiting
  rule {
    action   = "rate_based_ban"
    priority = 2000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 1000
        interval_sec = 60
      }
      ban_duration_sec = 600
    }
    description = "Rate limiting"
  }

  # Default allow
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule"
  }
}
```

---

## Kubernetes Deployment

### Workload Identity Setup

```yaml
# k8s/service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai-platform
  namespace: ai-platform
  annotations:
    iam.gke.io/gcp-service-account: ai-platform-prod@YOUR_PROJECT.iam.gserviceaccount.com
```

### Gateway Deployment

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
          image: YOUR_REGION-docker.pkg.dev/YOUR_PROJECT/ai-platform/gateway:latest
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
              ephemeral-storage: "1Gi"
            limits:
              memory: "1Gi"
              cpu: "1000m"
              ephemeral-storage: "2Gi"
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            seccompProfile:
              type: RuntimeDefault
```

### GKE Gateway API Ingress

```yaml
# k8s/gateway-api.yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: ai-platform-gateway
  namespace: ai-platform
spec:
  gatewayClassName: gke-l7-global-external-managed
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - kind: Secret
            name: api-tls-cert
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ai-platform-route
  namespace: ai-platform
spec:
  parentRefs:
    - name: ai-platform-gateway
  hostnames:
    - "api.yourcompany.com"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: gateway
          port: 80
```

---

## Deployment Commands

```bash
# 1. Configure gcloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Apply Terraform
cd terraform/gcp
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars

# 3. Get GKE credentials
gcloud container clusters get-credentials gke-ai-platform-prod --region us-west1

# 4. Create secrets from Secret Manager
kubectl create secret generic platform-secrets \
  --from-literal=database_url=$(gcloud secrets versions access latest --secret=database-url) \
  --from-literal=redis_url=$(gcloud secrets versions access latest --secret=redis-url) \
  -n ai-platform

# 5. Deploy application
kubectl apply -f k8s/

# 6. Get external IP
kubectl get gateway ai-platform-gateway -n ai-platform -o jsonpath='{.status.addresses[0].value}'
```

---

## Monitoring with Cloud Monitoring

```bash
# Enable GKE monitoring
gcloud container clusters update gke-ai-platform-prod \
  --region us-west1 \
  --enable-managed-prometheus

# Create custom dashboard
gcloud monitoring dashboards create \
  --config-from-file=dashboards/ai-platform.json
```

---

## Security Checklist

- [ ] Workload Identity enabled (no service account keys)
- [ ] Private GKE cluster with authorized networks
- [ ] Cloud Armor WAF policies active
- [ ] Binary Authorization enabled
- [ ] VPC Service Controls configured
- [ ] Cloud Audit Logs enabled
- [ ] Security Command Center monitoring
- [ ] Customer-managed encryption keys (CMEK)
- [ ] Cloud IDS for threat detection
- [ ] Shielded GKE Nodes

---

## Cost Estimation

| Component | SKU | Monthly Cost (Estimate) |
|-----------|-----|------------------------|
| GKE Autopilot | Per pod | $300 |
| Cloud SQL | db-custom-4-16384 | $320 |
| Memorystore | 4GB Standard HA | $280 |
| Load Balancer | Global | $25 |
| Cloud Armor | Standard | $5 |
| Cloud Monitoring | Per metric | $50 |
| **Total** | | **~$980/month** |

---

## References

- [AWS Deployment](./aws.md)
- [Azure Deployment](./azure.md)
- [On-Premises Deployment](./onprem.md)
