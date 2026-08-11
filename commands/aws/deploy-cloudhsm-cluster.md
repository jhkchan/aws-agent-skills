---
description: Provision an AWS CloudHSM cluster with production-grade defaults (cluster creation in a VPC with subnets across 2+ AZs for HA, HSM instance creation, one-time cluster activation via CSR → self-signed cert, crypto officer/user management, daily automatic + on-demand backups, cross-region backup copy, PKCS#11/JCE/PCSC library integration, SSL/TLS offload, FIPS 140-2 Level 3 compliance, network security group, CN-to-cluster-ID mapping, degradation recovery). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create cloudhsm cluster"
  - "deploy cloudhsm cluster"
  - "aws cloudhsm"
  - "cloudhsm cluster"
  - "activate cloudhsm"
  - "hsm instance"
  - "crypto officer"
  - "cloudhsm backup"
  - "cross-region backup cloudhsm"
  - "copy backup to region"
  - "pkcs#11 library"
  - "jce provider"
  - "fips 140-2 level 3"
  - "cn-to-cluster-id"
  - "hsm degradation"
  - "hsm recovery"
routes_to: cloudhsm-cluster-deployer
---

# /aws:deploy-cloudhsm-cluster

Activate the `cloudhsm-cluster-deployer` skill and provision an AWS
CloudHSM cluster with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Cluster creation (VPC + ≥2 AZ subnets; subnet list is immutable)
2. HSM instance creation (one per AZ)
3. Cluster activation (one-time CSR → self-signed cert upload)
4. Crypto officer / user management (CO password is NOT recoverable)
5. HSM backups (daily automatic + on-demand)
6. Cross-region backup copy (DR — restore creates new cluster-id)
7. HA across AZs (≥2 AZs in the SAME cluster)
8. PKCS#11 / JCE / PCSC library integration
9. SSL/TLS offload (HSM-held private key)
10. FIPS 140-2 Level 3 compliance posture
11. Network security group (narrowest workload CIDR)
12. CN-to-cluster-ID mapping (client TLS bootstrap)
13. Degradation recovery (create replacement, sync, delete)

## When to use

- You need to create a CloudHSM cluster.
- You are activating an HSM (CSR → signed cert upload).
- You are configuring CO/users, quorum, or password policies.
- You are configuring backups (daily + on-demand + cross-region).
- You are integrating PKCS#11/JCE clients.
- You are configuring SSL/TLS offload against CloudHSM.
- You are recovering from HSM degradation.

## When NOT to use

- **AWS KMS** — use `kms-key-deployer`. KMS is multi-tenant
  regional; CloudHSM is single-tenant FIPS 140-2 Level 3.
- **ACM certificates** — use `acm-certificate-deployer`.
- **AWS Signer** — use `signer-signing-profile-deployer`.
- **Auditing existing CloudHSM clusters** — use CloudHSM audit
  skills.

## How to invoke

### Slash command

```
/aws:deploy-cloudhsm-cluster
```

Then provide: cluster name, VPC ID, subnet IDs (one per AZ, ≥2
AZs), HSM type, security group ID, customer CA (for activation),
CO user list, CO password storage plan, backup retention,
cross-region destination (if DR), workload integration (PKCS#11
or JCE), tags.

### Natural language

Any of these routes to the same skill:

- "create a CloudHSM cluster across 3 AZs"
- "activate a CloudHSM cluster with my in-house CA"
- "configure crypto officer quorum for CloudHSM"
- "copy CloudHSM backups to us-west-2 for DR"
- "recover a degraded HSM in my CloudHSM cluster"

### CLI routing

```bash
node cli/bin/cli.js route "create a cloudhsm cluster"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create CloudHSM resources. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-cloudhsm-cluster

     Create a CloudHSM cluster cloudhsm-prod across 3 AZs in
     us-east-1. Activate with our in-house CA. Two CO users,
     password in Secrets Manager. Daily backups plus cross-region
     copy to us-west-2. Configure PKCS#11 for nginx TLS offload.

Skill:
  CLOUDHSM: cluster-abc123def (1a, 1b, 1c)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] HSMs: 3 across 3 AZs
    [✓] Activation: CSR → in-house CA (ONE-TIME)
    [✓] CO: admin, officer2 (Secrets Manager)
    [✓] Cross-region backup copy: us-west-2
    [✓] PKCS#11 client configured
  VERIFICATION_COMMANDS:
    aws cloudhsmv2 describe-clusters --filters clusterIds=cluster-abc123def --region us-east-1
    aws cloudhsmv2 describe-backups --filters clusterIds=cluster-abc123def --region us-east-1
```

## References

- Skill definition: `skills/cloudhsm-cluster-deployer/SKILL.md`
- Cluster activation + CO guide: `skills/cloudhsm-cluster-deployer/references/cluster-activation-and-users.md`
- Backups + HA + recovery guide: `skills/cloudhsm-cluster-deployer/references/backups-and-ha.md`
- Eval suite: `skills/cloudhsm-cluster-deployer/evals/evals.json`
