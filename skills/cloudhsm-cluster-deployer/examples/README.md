# Example: Deploy AWS CloudHSM Cluster

## Scenario
Deploy a 2-AZ CloudHSM cluster with CSR activation and crypto officer setup.

## Steps
1. Create cluster with 2 subnet IDs in different AZs
2. Retrieve CSR from describe-clusters
3. Sign CSR with internal CA
4. Initialize cluster with signed certificate
5. Create HSM instances (one per AZ)
6. Create crypto officer user
7. Configure PKCS#11/JCE client
8. Verify FIPS compliance

## Key Decisions
- 2 AZs minimum for HA
- hsm1.medium for general-purpose workloads
- 7-day backup retention
- CO password must meet CloudHSM complexity requirements
