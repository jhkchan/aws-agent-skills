# End-to-end usage scenario: efs-filesystem-auditor

A walkthrough showing the skill auditing an EFS filesystem that has both a
public filesystem policy with ClientRootAccess (PUBLIC_POLICY) and missing
lifecycle + TLS enforcement, demonstrating severity aggregation, the
ClientRootAccess danger concept, and the assume-breach remediation workflow.

## Input (user prompt)

> Review this EFS filesystem before we attach it to the production data
> pipeline. It stores shared ML training datasets.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenMount",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
        "elasticfilesystem:ClientRootAccess"
      ],
      "Resource": "*"
    }
  ]
}
```

Filesystem metadata:
- Encrypted: true
- KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/prod-ml-key
- PerformanceMode: generalPurpose
- LifecyclePolicies: (none)
- Access points: 0

## Skill output

```text
FILESYSTEM: fs-prod-ml-datasets
VERDICT: PUBLIC_POLICY
REASON: Filesystem policy Statement "OpenMount" grants Principal "*" with
ClientMount + ClientWrite + ClientRootAccess and no restrictive condition —
any network-reachable client can mount with root privileges (Rule 2a).
Lifecycle policy and TLS enforcement are also missing.
FINDINGS:
  - [PUBLIC_POLICY] Principal "*" with ClientRootAccess and no condition
    (Rule 2a) — root-level mount access: any reachable client can read,
    modify, and delete every file with root privileges (no root squashing)
  - [CONFIG_GAP] No lifecycle policy configured (Rule 3a) — all training
    datasets remain in Standard storage indefinitely; unbounded cost growth
  - [CONFIG_GAP] No TLS enforcement: policy grants Client* without
    aws:SecureTransport condition (Rule 3b) — NFS traffic in plaintext
  - [CONFIG_GAP] No access points configured (Rule 3c) — no application-
    level POSIX isolation; any mounted client sees the full namespace
  - [OK] Encrypted at rest with KMS key prod-ml-key
REMEDIATION:
  1. PUBLIC_POLICY — Replace Principal "*" with specific IAM role ARNs
     (e.g., the ML pipeline role), or add elasticfilesystem:AccessPointArn
     condition to force access-point routing. Back up policy first.
  2. PUBLIC_POLICY — Assume breach. Audit CloudTrail for
     elasticfilesystem:ClientMount events from unexpected principals.
     Review mount-target security groups for broad port-2049 rules.
  3. CONFIG_GAP — Add lifecycle policy:
     aws efs put-lifecycle-configuration --file-system-id fs-prod-ml-datasets
     --lifecycle-policies TransitionToIA=AFTER_30_DAYS
  4. CONFIG_GAP — Add aws:SecureTransport condition to all Client* Allow
     statements, or add a Deny on aws:SecureTransport: false.
  5. CONFIG_GAP — Create access points for each ML pipeline consumer:
     aws efs create-access-point --file-system-id fs-prod-ml-datasets
     --name training --posix-user Uid=1000,Gid=1000
     --root-directory Path=/training
```

## What the skill caught that a generic assistant misses

1. **ClientRootAccess is total filesystem compromise.** A generic assistant
   says "Principal star is bad." The skill explains that
   `ClientRootAccess` grants root privileges — no root squashing, no
   file-level permission checks. Combined with `Principal: "*"`, any
   network-reachable client can read, modify, and delete every file on the
   filesystem with root authority.

2. **No filesystem policy would be fine — this policy is the problem.** The
   skill recognises that a MISSING filesystem policy is the secure default
   (IAM-governed). The issue is not "has a policy" — it is that the policy
   actively grants public root access.

3. **Severity aggregation with per-finding breakdown.** The verdict is
   PUBLIC_POLICY (worst finding), but the FINDINGS list shows the individual
   dimensions: the public root access is PUBLIC_POLICY, the lifecycle gap
   is CONFIG_GAP, the TLS gap is CONFIG_GAP, and encryption is OK. This
   lets the operator triage each finding independently.

4. **The assume-breach remediation workflow.** Generic advice says "remove
   the access." The skill's remediation includes auditing CloudTrail for
   ClientMount events during the exposure window and reviewing mount-target
   security groups — because the filesystem may have already been mounted
   by an unexpected client.

## Slash-command invocation

```
/aws:audit-efs-filesystem
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this EFS filesystem before we use it for the ML data pipeline"
```

The orchestrator emits
`[Phase: Audit | Skills routed: efs-filesystem-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policy, validate the filesystem posture:

```bash
# Verify the public principal was removed
aws efs describe-file-system-policy --file-system-id fs-prod-ml-datasets \
  --profile default --output json | jq '.Policy | fromjson | .Statement[] | .Principal'

# Confirm lifecycle policy is set
aws efs describe-lifecycle-policies --file-system-id fs-prod-ml-datasets \
  --profile default

# List access points
aws efs describe-access-points --file-system-id fs-prod-ml-datasets \
  --profile default
```

Then monitor CloudTrail for `elasticfilesystem:ClientMount` events from
unexpected principals for 1-2 weeks.
