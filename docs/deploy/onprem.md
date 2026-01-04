# On-Premises Deployment Guide

## Deploying the Enterprise AI Platform On-Premises

### Overview

This guide covers deploying the platform in your own data center using:

- **Kubernetes**: Self-managed or enterprise distributions (OpenShift, Rancher, Tanzu)
- **PostgreSQL**: Self-managed with HA (Patroni/Stolon)
- **Redis**: Self-managed with Sentinel or Cluster mode
- **HAProxy/NGINX**: Load balancing and TLS termination
- **HashiCorp Vault**: Secret management

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ON-PREMISES DATA CENTER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        DMZ / EDGE NETWORK                                ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │     HAProxy / F5 / NGINX Plus (Active-Active)                       │││
│  │  │     - TLS Termination                                                │││
│  │  │     - WAF (ModSecurity)                                             │││
│  │  │     - Rate Limiting                                                  │││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                               │                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     APPLICATION NETWORK (VLAN 100)                       ││
│  │                                                                          ││
│  │  ┌────────────────────────────────────────────────────────────────────┐ ││
│  │  │                    KUBERNETES CLUSTER                               │ ││
│  │  │                                                                     │ ││
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │ ││
│  │  │  │  Control Plane │  │  Control Plane │  │  Control Plane │          │ ││
│  │  │  │   (Master 1)   │  │   (Master 2)   │  │   (Master 3)   │          │ ││
│  │  │  └───────────────┘  └───────────────┘  └───────────────┘          │ ││
│  │  │                                                                     │ ││
│  │  │  ┌───────────────────────────────────────────────────────────────┐ │ ││
│  │  │  │                    Worker Nodes (N+2)                         │ │ ││
│  │  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │ │ ││
│  │  │  │  │ Gateway │  │Orchestr│  │  Tools  │  │  Eval   │         │ │ ││
│  │  │  │  │  Pods   │  │  Pods   │  │  Pods   │  │  Pods   │         │ │ ││
│  │  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘         │ │ ││
│  │  │  └───────────────────────────────────────────────────────────────┘ │ ││
│  │  │                                                                     │ ││
│  │  └────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                               │                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                       DATA NETWORK (VLAN 200)                            ││
│  │                                                                          ││
│  │  ┌────────────────────────────────────────────────────────────────────┐ ││
│  │  │  PostgreSQL Cluster (Patroni + etcd)                               │ ││
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │ ││
│  │  │  │  Primary    │  │  Replica 1  │  │  Replica 2  │                │ ││
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘                │ ││
│  │  └────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                          ││
│  │  ┌────────────────────────────────────────────────────────────────────┐ ││
│  │  │  Redis Cluster (6 nodes: 3 masters + 3 replicas)                   │ ││
│  │  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐     │ ││
│  │  │  │ M1/R1 │ │ M2/R2 │ │ M3/R3 │ │  R1   │ │  R2   │ │  R3   │     │ ││
│  │  │  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘ └───────┘     │ ││
│  │  └────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                               │                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    MANAGEMENT NETWORK (VLAN 300)                         ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    ││
│  │  │ HashiCorp   │  │ Prometheus  │  │   Grafana   │  │   Ansible   │    ││
│  │  │   Vault     │  │ + Alertmgr  │  │             │  │   Tower     │    ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Kubernetes Masters | 3x 4 CPU, 16GB RAM | 3x 8 CPU, 32GB RAM |
| Kubernetes Workers | 3x 8 CPU, 32GB RAM | 6x 16 CPU, 64GB RAM |
| PostgreSQL Nodes | 3x 8 CPU, 32GB RAM, 500GB SSD | 3x 16 CPU, 64GB RAM, 1TB NVMe |
| Redis Nodes | 6x 4 CPU, 16GB RAM | 6x 8 CPU, 32GB RAM |
| Load Balancers | 2x 4 CPU, 8GB RAM | 2x 8 CPU, 16GB RAM |

### Software Requirements

- Kubernetes 1.28+ (kubeadm, OpenShift 4.14+, or Rancher 2.8+)
- PostgreSQL 15+
- Redis 7.0+
- HAProxy 2.8+ or NGINX Plus
- HashiCorp Vault 1.15+
- Ansible 2.15+

---

## Network Configuration

### VLAN Layout

| VLAN | Name | CIDR | Purpose |
|------|------|------|---------|
| 100 | Application | 10.100.0.0/16 | Kubernetes cluster |
| 200 | Data | 10.200.0.0/16 | Database and cache |
| 300 | Management | 10.300.0.0/24 | Monitoring, secrets |

### Firewall Rules

```yaml
# firewall-rules.yaml
ingress:
  - from: internet
    to: load-balancer
    ports: [443]
    description: "HTTPS traffic"

  - from: load-balancer
    to: kubernetes-workers
    ports: [30000-32767]
    description: "NodePort range"

  - from: kubernetes-pods
    to: postgresql
    ports: [5432]
    description: "Database access"

  - from: kubernetes-pods
    to: redis-cluster
    ports: [6379, 16379]
    description: "Redis data and cluster bus"

  - from: management
    to: all
    ports: [22]
    description: "SSH management"
```

---

## PostgreSQL High Availability Setup

### Patroni Configuration

```yaml
# patroni.yml
scope: ai-platform
namespace: /db/
name: postgresql0

restapi:
  listen: 0.0.0.0:8008
  connect_address: 10.200.0.10:8008

etcd:
  hosts:
    - 10.200.0.100:2379
    - 10.200.0.101:2379
    - 10.200.0.102:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: true
      use_slots: true
      parameters:
        shared_preload_libraries: 'pg_stat_statements,vector'
        max_connections: 200
        shared_buffers: 8GB
        effective_cache_size: 24GB
        work_mem: 64MB
        maintenance_work_mem: 2GB
        wal_level: replica
        max_wal_senders: 10
        max_replication_slots: 10
        hot_standby: on

  initdb:
    - encoding: UTF8
    - data-checksums

  pg_hba:
    - host replication replicator 10.200.0.0/16 scram-sha-256
    - host all all 10.100.0.0/16 scram-sha-256

postgresql:
  listen: 0.0.0.0:5432
  connect_address: 10.200.0.10:5432
  data_dir: /var/lib/postgresql/data
  authentication:
    superuser:
      username: postgres
      password: ${POSTGRES_PASSWORD}
    replication:
      username: replicator
      password: ${REPLICATOR_PASSWORD}

tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
```

### HAProxy for PostgreSQL

```haproxy
# haproxy-postgres.cfg
global
    maxconn 1000

defaults
    mode tcp
    timeout connect 10s
    timeout client 30m
    timeout server 30m

frontend postgresql_frontend
    bind *:5432
    default_backend postgresql_backend

backend postgresql_backend
    option httpchk GET /leader
    http-check expect status 200
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions

    server pg0 10.200.0.10:5432 check port 8008
    server pg1 10.200.0.11:5432 check port 8008
    server pg2 10.200.0.12:5432 check port 8008
```

---

## Redis Cluster Setup

### Redis Cluster Configuration

```conf
# redis.conf
port 6379
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes
appendfsync everysec
maxmemory 12gb
maxmemory-policy volatile-lru
requirepass ${REDIS_PASSWORD}
masterauth ${REDIS_PASSWORD}
tls-port 6379
tls-cert-file /etc/redis/tls/redis.crt
tls-key-file /etc/redis/tls/redis.key
tls-ca-cert-file /etc/redis/tls/ca.crt
tls-cluster yes
tls-replication yes
```

### Cluster Initialization

```bash
# Initialize 6-node cluster
redis-cli --cluster create \
  10.200.0.20:6379 \
  10.200.0.21:6379 \
  10.200.0.22:6379 \
  10.200.0.23:6379 \
  10.200.0.24:6379 \
  10.200.0.25:6379 \
  --cluster-replicas 1 \
  -a ${REDIS_PASSWORD} \
  --tls \
  --cert /etc/redis/tls/redis.crt \
  --key /etc/redis/tls/redis.key \
  --cacert /etc/redis/tls/ca.crt
```

---

## HashiCorp Vault Setup

### Vault Configuration

```hcl
# vault.hcl
storage "raft" {
  path    = "/opt/vault/data"
  node_id = "vault-1"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/opt/vault/tls/vault.crt"
  tls_key_file  = "/opt/vault/tls/vault.key"
}

api_addr     = "https://10.300.0.10:8200"
cluster_addr = "https://10.300.0.10:8201"

seal "awskms" {
  # Or use transit seal with another Vault
  region     = "us-west-2"
  kms_key_id = "alias/vault-unseal"
}

ui = true
```

### Kubernetes Auth Method

```bash
# Enable Kubernetes auth
vault auth enable kubernetes

# Configure with Kubernetes API
vault write auth/kubernetes/config \
  kubernetes_host="https://10.100.0.1:6443" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

# Create policy for platform
vault policy write ai-platform - <<EOF
path "secret/data/ai-platform/*" {
  capabilities = ["read"]
}
EOF

# Create role for Kubernetes service account
vault write auth/kubernetes/role/ai-platform \
  bound_service_account_names=ai-platform \
  bound_service_account_namespaces=ai-platform \
  policies=ai-platform \
  ttl=1h
```

---

## Kubernetes Deployment

### Vault Secrets Injection

```yaml
# k8s/deployment.yaml
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
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "ai-platform"
        vault.hashicorp.com/agent-inject-secret-database: "secret/data/ai-platform/database"
        vault.hashicorp.com/agent-inject-template-database: |
          {{- with secret "secret/data/ai-platform/database" -}}
          export DATABASE_URL="{{ .Data.data.url }}"
          {{- end -}}
    spec:
      serviceAccountName: ai-platform
      containers:
        - name: gateway
          image: registry.internal/ai-platform/gateway:latest
          command: ["/bin/sh", "-c"]
          args: ["source /vault/secrets/database && /app/gateway"]
          ports:
            - containerPort: 8080
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
```

### Network Policies

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-platform-policy
  namespace: ai-platform
spec:
  podSelector:
    matchLabels:
      app: gateway
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - ipBlock:
            cidr: 10.200.0.0/16  # Data network
      ports:
        - protocol: TCP
          port: 5432  # PostgreSQL
        - protocol: TCP
          port: 6379  # Redis
    - to:
        - ipBlock:
            cidr: 10.300.0.0/24  # Management network
      ports:
        - protocol: TCP
          port: 8200  # Vault
```

---

## Load Balancer Configuration

### HAProxy for Application Traffic

```haproxy
# haproxy.cfg
global
    log /dev/log local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

    # TLS settings
    ssl-default-bind-ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256
    ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

defaults
    log global
    mode http
    option httplog
    option dontlognull
    option http-server-close
    option forwardfor except 127.0.0.0/8
    timeout connect 5000
    timeout client  50000
    timeout server  50000

frontend https_frontend
    bind *:443 ssl crt /etc/haproxy/certs/api.pem alpn h2,http/1.1

    # WAF via ModSecurity
    filter spoe engine modsecurity config /etc/haproxy/spoe-modsecurity.conf

    # Rate limiting
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny deny_status 429 if { sc_http_req_rate(0) gt 100 }

    # Headers
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Real-IP %[src]

    default_backend kubernetes_backend

backend kubernetes_backend
    balance roundrobin
    option httpchk GET /health/ready
    http-check expect status 200

    server worker1 10.100.0.10:30080 check ssl verify required ca-file /etc/haproxy/certs/k8s-ca.pem
    server worker2 10.100.0.11:30080 check ssl verify required ca-file /etc/haproxy/certs/k8s-ca.pem
    server worker3 10.100.0.12:30080 check ssl verify required ca-file /etc/haproxy/certs/k8s-ca.pem
```

---

## Monitoring Stack

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true

  - job_name: 'postgresql'
    static_configs:
      - targets:
          - '10.200.0.10:9187'
          - '10.200.0.11:9187'
          - '10.200.0.12:9187'

  - job_name: 'redis'
    static_configs:
      - targets:
          - '10.200.0.20:9121'
          - '10.200.0.21:9121'
          - '10.200.0.22:9121'

  - job_name: 'haproxy'
    static_configs:
      - targets:
          - '10.100.0.1:8404'
          - '10.100.0.2:8404'
```

---

## Deployment Automation

### Ansible Playbook

```yaml
# site.yml
---
- name: Deploy AI Platform
  hosts: all
  become: true
  vars_files:
    - vars/main.yml
    - vars/vault.yml

  roles:
    - role: common
      tags: [common]

    - role: haproxy
      tags: [haproxy]
      when: "'loadbalancers' in group_names"

    - role: kubernetes
      tags: [kubernetes]
      when: "'kubernetes' in group_names"

    - role: postgresql
      tags: [postgresql]
      when: "'postgresql' in group_names"

    - role: redis
      tags: [redis]
      when: "'redis' in group_names"

    - role: vault
      tags: [vault]
      when: "'vault' in group_names"

    - role: monitoring
      tags: [monitoring]
      when: "'monitoring' in group_names"

  post_tasks:
    - name: Deploy application to Kubernetes
      kubernetes.core.k8s:
        state: present
        src: "{{ item }}"
      loop: "{{ lookup('fileglob', 'k8s/*.yaml', wantlist=True) }}"
      when: "'kubernetes' in group_names"
      delegate_to: localhost
```

---

## Backup and Recovery

### Backup Strategy

| Component | Method | Frequency | Retention |
|-----------|--------|-----------|-----------|
| PostgreSQL | pg_basebackup + WAL | Continuous | 30 days |
| Redis | RDB + AOF | Hourly | 7 days |
| Vault | Raft snapshots | Daily | 90 days |
| Kubernetes | Velero | Daily | 30 days |

### PostgreSQL Backup Script

```bash
#!/bin/bash
# backup-postgres.sh

BACKUP_DIR=/backup/postgresql
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${DATE}"

# Create base backup
pg_basebackup \
  -h localhost \
  -U replicator \
  -D "${BACKUP_PATH}" \
  -Ft \
  -z \
  -P \
  --wal-method=stream

# Archive to S3-compatible storage (MinIO)
aws s3 cp \
  "${BACKUP_PATH}" \
  "s3://backups/postgresql/${DATE}/" \
  --recursive \
  --endpoint-url http://minio.internal:9000

# Cleanup old backups
find ${BACKUP_DIR} -type d -mtime +7 -exec rm -rf {} \;
```

---

## Security Checklist

- [ ] All traffic encrypted with TLS 1.2+
- [ ] Network segmentation with VLANs and firewalls
- [ ] Vault for all secrets (no plaintext)
- [ ] mTLS between services
- [ ] RBAC in Kubernetes
- [ ] PostgreSQL SSL with client certificates
- [ ] Redis TLS and AUTH
- [ ] WAF (ModSecurity) on load balancers
- [ ] Intrusion detection (OSSEC/Wazuh)
- [ ] Regular vulnerability scanning
- [ ] Audit logging enabled everywhere
- [ ] HSM for Vault unseal keys (production)

---

## Disaster Recovery

### RTO/RPO Targets

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single node failure | < 5 minutes | 0 |
| Availability zone failure | < 15 minutes | < 1 minute |
| Complete site failure | < 4 hours | < 15 minutes |

### DR Runbook

1. **Detect**: Monitoring alerts on failure
2. **Assess**: Determine scope (node/zone/site)
3. **Failover**:
   - Database: Patroni auto-failover or manual promotion
   - Redis: Cluster auto-failover
   - Kubernetes: Node replacement or cluster rebuild
4. **Restore**: If data loss, restore from backup
5. **Verify**: Run integration tests
6. **Postmortem**: Document and improve

---

## References

- [AWS Deployment](./aws.md)
- [Azure Deployment](./azure.md)
- [GCP Deployment](./gcp.md)
