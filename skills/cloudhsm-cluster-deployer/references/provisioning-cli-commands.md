# Provisioning CLI Commands

## Cluster Creation
```bash
aws cloudhsmv2 create-cluster \
  --hsm-type hsm1.medium \
  --subnet-ids subnet-aaa11122 subnet-bbb22233 \
  --backup-retention-policy Type=DAYS,Value=7
```

## HSM Creation
```bash
aws cloudhsmv2 create-hsm \
  --cluster-id cluster-xxx \
  --availability-zone us-east-1a \
  --ip-address 10.0.1.10
```

## Cluster Activation
1. Describe clusters to get CSR
2. Sign CSR with your CA
3. Initialize cluster with signed certificate
4. Wait for cluster to reach ACTIVATED state

## User Management
```
cloudhsm-cli --mode user add-user --username co_admin --role crypto-officer --password <password>
```

## NEVER Patterns
1. Never deploy single-AZ for production workloads
2. Never skip CSR signing (cluster must be activated)
3. Never store crypto officer password in plaintext
4. Never ignore backup retention policy
5. Never use same password across environments
