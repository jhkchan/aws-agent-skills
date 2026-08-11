# Eval: three-az-cluster-with-activation

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — 3-AZ cluster, one-time activation (CSR → self-signed cert), 2 CO users, daily backups, PKCS#11 client, FIPS 140-2 Level 3 posture

## Prompt

Create a CloudHSM cluster "cloudhsm-prod" in us-east-1 across 3 AZs
(us-east-1a subnet-aaa, us-east-1b subnet-bbb, us-east-1c
subnet-ccc), VPC vpc-aaa11122, security group sg-cloudhsm-prod,
hsm1.medium. Perform one-time activation with our in-house
customerCA. Create 2 CO users (admin, officer2) with CO password
stored in Secrets Manager. Enable daily automatic backups.
Configure the PKCS#11 client. Workload: nginx SSL/TLS offload.
Tags: Environment=production, Workload=tls-offload,
Owner=platform-team.
