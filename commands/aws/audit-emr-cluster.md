---
description: Audit an EMR cluster for encryption gaps (S3, local-disk, in-transit), over-permissive IAM roles, Kerberos auth, block public access, and debug logging posture.
nl_triggers:
  - "audit this EMR cluster"
  - "check EMR encryption"
  - "is my EMR cluster encrypted"
  - "EMR security configuration"
  - "EMR IAM role too permissive"
  - "EMR in-transit encryption"
  - "EMR local disk encryption"
  - "Kerberos EMR"
  - "block public access EMR"
  - "harden EMR cluster"
  - "EMR debug logging"
  - "EMR instance profile role"
  - "EMR service role audit"
  - "EMR AutoScaling role"
  - "S3 SSE-KMS EMR"
  - "LUKS EMR encryption"
  - "Spark cluster security audit"
  - "Hadoop cluster encryption"
routes_to: emr-cluster-auditor
---

# /aws:audit-emr-cluster

Activate the `emr-cluster-auditor` skill and audit an EMR cluster
configuration for security exposure across encryption, IAM roles,
authentication, and configuration completeness.

## What it does

Reads an EMR cluster configuration (describe-cluster output +
SecurityConfiguration contents + IAM role policies) and applies the ordered
classification logic:

1. Encryption gate — any missing layer (S3, local-disk, in-transit) produces
   NO_ENCRYPTION (Step 1). The SecurityConfiguration must be fetched separately
   via `describe-security-configuration` — the cluster metadata only returns
   the config name.
2. IAM role audit — service role, EC2 instance profile, and AutoScaling role
   evaluated for wildcard actions, privilege escalation (PassRole), and
   kms:Decrypt blast radius (Step 2).
3. Configuration completeness — debug logging, Block Public Access, Kerberos
   authentication, VisibleToAllUsers, single-master HA (Step 3).
4. Aggregation — worst finding wins (NO_ENCRYPTION > OVERPERMISSIVE_ROLE >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per cluster:

```text
CLUSTER: <cluster-id>
VERDICT: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step Na)>
  - [CONFIG_GAP] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an EMR cluster configuration (describe-cluster + SecurityConfiguration +
IAM roles) and ask any of:

- "audit this EMR cluster"
- "is my EMR cluster encrypted?"
- "check EMR security configuration"
- "are the EMR IAM roles over-permissive?"
- "is Kerberos enabled on EMR?"
- "is Block Public Access configured?"
- "harden this EMR cluster before production"

A bare cluster-id or cluster name + any audit verb ("audit this cluster",
"check EMR encryption") also routes here via the orchestrator.

## Inputs

- EMR cluster metadata: ReleaseLabel, SecurityConfiguration (name),
  ServiceRole, Ec2InstanceAttributes.IamInstanceProfile, AutoScalingRole,
  LogUri, KerberosAttributes, VisibleToAllUsers, InstanceGroups.
- SecurityConfiguration contents: the parsed encryption settings from
  `describe-security-configuration`. The cluster metadata only returns the
  config name — the contents MUST be fetched separately.
- IAM role policies: service role, EC2 instance profile, and AutoScaling role
  policy documents (inline + managed).
- Block Public Access configuration (region-level).

## Outputs

- One VERDICT block per cluster (multiple findings aggregate to the worst
  verdict by precedence: NO_ENCRYPTION > OVERPERMISSIVE_ROLE > CONFIG_GAP > OK).
- Enumerated FINDINGS list with per-finding step citation.
- Specific remediation: create/update SecurityConfiguration, scope IAM roles,
  enable debug logging, enable Block Public Access, enable Kerberos.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for EMR analytics security).
- `/aws:audit-kms-key-policy` for auditing the KMS keys referenced by the
  EMR SecurityConfiguration encryption settings.
- `/aws:audit-iam-least-privilege` for deeper IAM policy analysis of the
  EMR service, EC2, and AutoScaling roles.
