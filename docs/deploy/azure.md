# Azure Deployment Guide

## Deploying the Enterprise AI Platform on Azure

### Overview

This guide covers deploying the platform on Azure using:

- **AKS**: Azure Kubernetes Service for container orchestration
- **Azure Database for PostgreSQL**: Managed PostgreSQL with Flexible Server
- **Azure Cache for Redis**: Managed Redis for caching and memory
- **Azure Application Gateway**: Traffic management and WAF
- **Azure Key Vault**: Secure credential storage

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AZURE REGION                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Virtual Network (10.0.0.0/8)                      ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │                                                                          ││
│  │  ┌──────────────────────────────────────────────────────────────────┐   ││
│  │  │                    Application Gateway Subnet                     │   ││
│  │  │                        (10.1.0.0/24)                              │   ││
│  │  │  ┌─────────────────────────────────────────────────────────────┐ │   ││
│  │  │  │           Azure Application Gateway + WAF                    │ │   ││
│  │  │  └─────────────────────────────────────────────────────────────┘ │   ││
│  │  └──────────────────────────────────────────────────────────────────┘   ││
│  │                                                                          ││
│  │  ┌──────────────────────────────────────────────────────────────────┐   ││
│  │  │                        AKS Subnet                                 │   ││
│  │  │                        (10.2.0.0/16)                              │   ││
│  │  │  ┌─────────────────────────────────────────────────────────────┐ │   ││
│  │  │  │                     AKS CLUSTER                              │ │   ││
│  │  │  │  ┌───────────┐  ┌───────────┐  ┌───────────┐               │ │   ││
│  │  │  │  │  Gateway  │  │Orchestrator│  │   Tools   │               │ │   ││
│  │  │  │  │   Pods    │  │   Pods    │  │   Pods    │               │ │   ││
│  │  │  │  └───────────┘  └───────────┘  └───────────┘               │ │   ││
│  │  │  └─────────────────────────────────────────────────────────────┘ │   ││
│  │  └──────────────────────────────────────────────────────────────────┘   ││
│  │                                                                          ││
│  │  ┌──────────────────────────────────────────────────────────────────┐   ││
│  │  │                      Data Subnet                                  │   ││
│  │  │                      (10.3.0.0/24)                                │   ││
│  │  │  ┌──────────────────────────────────────────────────────────┐    │   ││
│  │  │  │  Azure Database for PostgreSQL (Flexible Server)         │    │   ││
│  │  │  │  - Zone Redundant HA                                      │    │   ││
│  │  │  └──────────────────────────────────────────────────────────┘    │   ││
│  │  │  ┌──────────────────────────────────────────────────────────┐    │   ││
│  │  │  │  Azure Cache for Redis (Premium)                          │    │   ││
│  │  │  │  - Geo-Replication                                        │    │   ││
│  │  │  └──────────────────────────────────────────────────────────┘    │   ││
│  │  └──────────────────────────────────────────────────────────────────┘   ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  Azure Monitor  │  │   Key Vault     │  │Container Registry│            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- Azure CLI configured with appropriate subscription
- Terraform >= 1.5.0
- kubectl >= 1.28
- Helm >= 3.12
- Docker for building images

---

## Infrastructure Setup

### 1. Resource Group and Networking

```hcl
# terraform/azure/main.tf

resource "azurerm_resource_group" "main" {
  name     = "rg-ai-platform-${var.environment}"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}

resource "azurerm_virtual_network" "main" {
  name                = "vnet-ai-platform-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/8"]

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}

resource "azurerm_subnet" "appgw" {
  name                 = "snet-appgw"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.1.0.0/24"]
}

resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.2.0.0/16"]
}

resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.3.0.0/24"]

  service_endpoints = ["Microsoft.Storage", "Microsoft.Sql"]

  delegation {
    name = "fs"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}
```

### 2. AKS Cluster

```hcl
# terraform/azure/aks.tf

resource "azurerm_kubernetes_cluster" "main" {
  name                = "aks-ai-platform-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "ai-platform-${var.environment}"
  kubernetes_version  = "1.28"

  default_node_pool {
    name                = "system"
    node_count          = 3
    vm_size             = "Standard_D4s_v5"
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 10

    node_labels = {
      "role" = "system"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
  }

  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "workload" {
  name                  = "workload"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_D8s_v5"
  enable_auto_scaling   = true
  min_count             = 2
  max_count             = 20
  vnet_subnet_id        = azurerm_subnet.aks.id

  node_labels = {
    "role" = "workload"
  }
}
```

### 3. Azure Database for PostgreSQL

```hcl
# terraform/azure/postgresql.tf

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "psql-ai-platform-${var.environment}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  delegated_subnet_id    = azurerm_subnet.data.id
  private_dns_zone_id    = azurerm_private_dns_zone.postgresql.id
  administrator_login    = "aiplatform"
  administrator_password = random_password.postgresql.result
  zone                   = "1"
  storage_mb             = 131072
  sku_name               = "GP_Standard_D4s_v3"

  high_availability {
    mode                      = "ZoneRedundant"
    standby_availability_zone = "2"
  }

  backup_retention_days = 35

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "aiplatform"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "VECTOR,PG_STAT_STATEMENTS"
}
```

### 4. Azure Cache for Redis

```hcl
# terraform/azure/redis.tf

resource "azurerm_redis_cache" "main" {
  name                = "redis-ai-platform-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 2
  family              = "P"
  sku_name            = "Premium"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  subnet_id = azurerm_subnet.data.id

  redis_configuration {
    enable_authentication = true
    maxmemory_policy      = "volatile-lru"
  }

  patch_schedule {
    day_of_week    = "Sunday"
    start_hour_utc = 2
  }

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}
```

### 5. Key Vault

```hcl
# terraform/azure/keyvault.tf

resource "azurerm_key_vault" "main" {
  name                = "kv-ai-platform-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "premium"

  enabled_for_disk_encryption     = true
  enabled_for_deployment          = true
  enabled_for_template_deployment = true
  purge_protection_enabled        = true
  soft_delete_retention_days      = 90

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"

    virtual_network_subnet_ids = [
      azurerm_subnet.aks.id,
    ]
  }

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  value        = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}:${random_password.postgresql.result}@${azurerm_postgresql_flexible_server.main.fqdn}/${azurerm_postgresql_flexible_server_database.main.name}?sslmode=require"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_url" {
  name         = "redis-url"
  value        = "rediss://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}"
  key_vault_id = azurerm_key_vault.main.id
}
```

### 6. Application Gateway with WAF

```hcl
# terraform/azure/appgw.tf

resource "azurerm_web_application_firewall_policy" "main" {
  name                = "waf-ai-platform-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  managed_rules {
    managed_rule_set {
      type    = "OWASP"
      version = "3.2"
    }
  }

  policy_settings {
    enabled = true
    mode    = "Prevention"
  }
}

resource "azurerm_application_gateway" "main" {
  name                = "appgw-ai-platform-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku {
    name     = "WAF_v2"
    tier     = "WAF_v2"
    capacity = 2
  }

  gateway_ip_configuration {
    name      = "gateway-ip-config"
    subnet_id = azurerm_subnet.appgw.id
  }

  frontend_port {
    name = "https-port"
    port = 443
  }

  frontend_ip_configuration {
    name                 = "frontend-ip"
    public_ip_address_id = azurerm_public_ip.appgw.id
  }

  ssl_certificate {
    name                = "api-cert"
    key_vault_secret_id = azurerm_key_vault_certificate.api.secret_id
  }

  backend_address_pool {
    name = "aks-backend"
  }

  backend_http_settings {
    name                  = "http-settings"
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 60
    probe_name            = "health-probe"
  }

  probe {
    name                = "health-probe"
    host                = "127.0.0.1"
    path                = "/health/ready"
    protocol            = "Http"
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3
  }

  http_listener {
    name                           = "https-listener"
    frontend_ip_configuration_name = "frontend-ip"
    frontend_port_name             = "https-port"
    protocol                       = "Https"
    ssl_certificate_name           = "api-cert"
  }

  request_routing_rule {
    name                       = "routing-rule"
    rule_type                  = "Basic"
    priority                   = 100
    http_listener_name         = "https-listener"
    backend_address_pool_name  = "aks-backend"
    backend_http_settings_name = "http-settings"
  }

  firewall_policy_id = azurerm_web_application_firewall_policy.main.id

  tags = {
    Environment = var.environment
    Project     = "ai-platform"
  }
}
```

---

## Kubernetes Deployment

### Using Azure Key Vault with AKS

```yaml
# k8s/secret-provider.yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: azure-kvs
  namespace: ai-platform
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    userAssignedIdentityID: "MANAGED_IDENTITY_CLIENT_ID"
    keyvaultName: "kv-ai-platform-prod"
    objects: |
      array:
        - |
          objectName: database-url
          objectType: secret
        - |
          objectName: redis-url
          objectType: secret
        - |
          objectName: anthropic-api-key
          objectType: secret
    tenantId: "YOUR_TENANT_ID"
  secretObjects:
    - secretName: platform-secrets
      type: Opaque
      data:
        - objectName: database-url
          key: database_url
        - objectName: redis-url
          key: redis_url
        - objectName: anthropic-api-key
          key: anthropic_api_key
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
      containers:
        - name: gateway
          image: YOUR_ACR.azurecr.io/ai-platform-gateway:latest
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: secrets-store
              mountPath: "/mnt/secrets-store"
              readOnly: true
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
      volumes:
        - name: secrets-store
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: azure-kvs
```

---

## Deployment Commands

```bash
# 1. Login to Azure
az login
az account set --subscription YOUR_SUBSCRIPTION_ID

# 2. Apply Terraform
cd terraform/azure
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars

# 3. Get AKS credentials
az aks get-credentials --resource-group rg-ai-platform-prod --name aks-ai-platform-prod

# 4. Install CSI driver for Key Vault
az aks enable-addons --addons azure-keyvault-secrets-provider --resource-group rg-ai-platform-prod --name aks-ai-platform-prod

# 5. Deploy application
kubectl apply -f k8s/

# 6. Configure Application Gateway AGIC
helm repo add application-gateway-kubernetes-ingress https://appgwingress.blob.core.windows.net/ingress-azure-helm-package/
helm install ingress-azure application-gateway-kubernetes-ingress/ingress-azure \
  --namespace kube-system \
  --set appgw.subscriptionId=SUBSCRIPTION_ID \
  --set appgw.resourceGroup=rg-ai-platform-prod \
  --set appgw.name=appgw-ai-platform-prod
```

---

## Monitoring with Azure Monitor

```bash
# Enable container insights
az aks enable-addons -a monitoring --resource-group rg-ai-platform-prod --name aks-ai-platform-prod

# Create dashboard
az portal dashboard create \
  --resource-group rg-ai-platform-prod \
  --name "AI Platform Dashboard" \
  --input-path dashboards/ai-platform.json
```

---

## Security Checklist

- [ ] Azure AD integration for AKS enabled
- [ ] Network policies configured
- [ ] Key Vault with RBAC access
- [ ] Private endpoints for data services
- [ ] WAF in prevention mode
- [ ] Azure Policy for compliance
- [ ] Defender for Cloud enabled
- [ ] Azure Sentinel for SIEM
- [ ] Managed identity (no passwords in code)
- [ ] Encryption at rest with customer-managed keys

---

## Cost Estimation

| Component | SKU | Monthly Cost (Estimate) |
|-----------|-----|------------------------|
| AKS (3x D4s_v5) | Standard | $350 |
| PostgreSQL Flexible | GP_Standard_D4s_v3 | $280 |
| Redis Premium P2 | Premium | $320 |
| Application Gateway | WAF_v2 | $250 |
| Log Analytics | Per GB | $50 |
| **Total** | | **~$1,250/month** |

---

## References

- [AWS Deployment](./aws.md)
- [GCP Deployment](./gcp.md)
- [On-Premises Deployment](./onprem.md)
