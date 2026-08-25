---
name: efs-access-point-deployer
description: 'Provisions EFS Access Points and dependent primitives with production defaults: root-directory auto-creation, POSIX user identity (uid, gid, secondary groups), directory ownership and permission bits, per-AZ mount targets in every compute subnet, IAM file-system policy with elasticfilesystem:AccessPointArn enforcement, amazon-efs-utils mount helper with TLS encryption in transit, EFS Intelligent-Tiering lifecycle for cost control, ECS/EKS integration via the EFS CSI driver (access-point-per-pod), and Lambda file-system mounts. Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with every item verified and copy-pasteable efs / elasticfilesystem / ecs / eks / lambda CLI. Use when creating an application-specific EFS entry point, enforcing IAM-based access, mounting EFS from ECS/EKS/Lambda, enabling encryption in transit, or hardening an existing access point. Triggers: EFS access point, mount EFS, POSIX identity, EFS CSI driver, EFS file system policy, encryption in transit, EFS Lambda.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with efs (create-access-point, put-file-system-policy, describe-mount-targets, describe-file-systems, describe-lifecycle-configuration), ec2 (describe-subnets, describe-availability-zones), ecs, eks, lambda (create-function, update-function-configuration), and cloudformation / terraform aws_efs_access_point / aws_efs_mount_target equivalents.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new EFS Access Point (with root directory, POSIX user identity, and directory permissions), enforcing IAM-based access to EFS via a file-system policy keyed on elasticfilesystem:AccessPointArn, deploying per-AZ mount targets across all compute subnets, mounting EFS from ECS/EKS via the EFS CSI driver (one access point per pod), mounting EFS from a Lambda function with VPC config, enabling TLS encryption in transit via amazon-efs-utils, or configuring EFS Intelligent-Tiering lifecycle for cost control. Do NOT invoke for plain EFS file-system creation without access points (use efs-file-system-deployer), for FSx (separate primitives), or for EFS access-point troubleshooting (use efs-mount-troubleshooter).
  activation_triggers: EFS access point, create access point EFS, mount EFS, POSIX identity EFS, EFS CSI driver, EFS file system policy, elasticfilesystem AccessPointArn, encryption in transit EFS, amazon-efs-utils, EFS mount target, EFS Lambda mount, EFS Intelligent-Tiering, ECS EFS volume, EKS EFS persistent volume
  invocation_schema: 'Input: either (a) a file-system ID + access point name + root directory path + POSIX identity (uid/gid) + directory permissions, or (b) a multi-AZ mount-target spec (subnet list + security groups), or (c) a container/Lambda integration spec (ECS task, EKS storage class, or Lambda function ARN). Output: deterministic ACCESS_POINT / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per the STRICT output contract, where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, efs, elastic-file-system, access-point, posix, mount-target, amazon-efs-utils, efs-csi-driver, file-system-policy, encryption-in-transit, tls, intelligent-tiering, efs-ia, ecs, eks, lambda, cloudops, deploy
  tags: aws, efs, access-point, posix, mount-target, encryption-in-transit, deploy, storage
  dependencies: aws-orchestrator
---

# EFS Access Points Deployer

## What this skill does

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (9 steps), verdict thresholds | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 9-step order matters; POSIX identity semantics | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "policy doesn't take effect" |
| **Expert heuristic** | The access-point-enforcement myth; cross-AZ mount targets; CSI driver access points | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **9-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent silent exposure / data-plane bugs | Review before deploy |
| **STRICT output contract** | Required ACCESS_POINT / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | EFS CSI driver GA, Lambda GA, Intelligent-Tiering, automatic backups | Stay current |

## Quick reference — provisioning summary (9 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm file-system baseline (encryption at rest, throughput mode, lifecycle) | — | AP inherits FS weaknesses |
| 2 | Verify a mount target exists in every AZ where compute runs | Yes | cross-AZ charges + latency; mount fails in AZ without target |
| 3 | Install / verify amazon-efs-utils (or EFS CSI driver on EKS) | Yes | TLS option silently ignored; mount uses port 2049 plain |
| 4 | Create the access point (root directory, POSIX user, directory permissions) | Yes | wrong uid/gid = files owned by unintended identity |
| 5 | Attach file-system policy with IAM enforcement (optional but recommended) | Yes | policy without AccessPointArn condition = dead text |
| 6 | Mount via the access point with TLS (`tls` mount option) | Yes | mount via FS DNS name bypasses AP enforcement silently |
| 7 | (ECS/EKS) Wire the access point into task/pod via EFS CSI driver | Yes | missing access point = per-pod isolation lost |
| 8 | (Lambda) Configure function with VPC + access-point ARN | Yes | wrong VPC = mount timeout |
| 9 | Verify every configuration item against actual state + emit checklist | — | silent no-ops |

**Critical ordering constraints:** file-system baseline before AP (the
AP does not override FS-level weaknesses); mount targets before AP
creation (an AP without a mount target in the client's AZ forces a
cross-AZ hop with no error); amazon-efs-utils before TLS (the `tls`
mount option is silently ignored if the helper is absent); AP before
file-system policy (the policy condition references AP ARNs); AP
before the container/Lambda integration (the CSI driver and Lambda
mount both reference the AP ARN). Rationale and the silent-failure
table are below.

## Activation keywords

EFS access point, create EFS access point, POSIX identity EFS, EFS
root directory, EFS directory permissions, EFS file-system policy,
elasticfilesystem:AccessPointArn, EFS IAM enforcement, amazon-efs-
utils, EFS mount helper, EFS TLS, EFS encryption in transit, EFS
mount target, EFS cross-AZ mount, EFS CSI driver, EKS EFS PV, ECS
EFS volume, Lambda EFS mount, EFS Intelligent-Tiering, EFS
lifecycle, EFS Infrequent Access.

## Invocation contract (hard requirement)

When this skill is invoked with an EFS access-point provisioning
request, the agent MUST respond with the checklist defined in
§"STRICT output contract" using the literal all-caps labels
`ACCESS_POINT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

## Reasoning framework (why the provisioning order matters)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Access point | file system exists in same region | AP root-directory path that doesn't exist on the FS is auto-created — but with the AP's permissions, not the operator's intended umask | per-application scoping |
| Mount target | subnet + security group in an AZ | **only one mount target per AZ per FS; adding a second in the same AZ errors, but a client in an AZ without a target silently cross-AZ mounts** | in-AZ mount |
| amazon-efs-utils | package installed on the host | `tls` mount option silently ignored if helper missing; mount succeeds as plain NFS | TLS encryption in transit |
| File-system policy | file system exists | **policy with `AccessPointArn` condition is dead text when the client mounts via the FS DNS name; no error, mount succeeds, IAM bypassed** | IAM-based access control |
| EFS CSI driver (EKS) | IRSA role with elasticfilesystem:* | storage class referencing non-existent AP → pod stuck in ContainerCreating; surfaces only in kubelet logs | per-pod EFS volumes |
| EFS volume (ECS) | task role with ClientMount + ClientWrite + ClientRootAccess | task role missing `ClientWrite` → mount succeeds read-only with no error | ECS task EFS |
| Lambda file system | function in a VPC; mount target in each function subnet | **mount target in only one subnet → cold starts in the other AZ time out silently** | Lambda EFS |
| Intelligent-Tiering lifecycle | file system exists | policy with `TransitionAfter` 0 days is invalid; wrong `TransitionAfter`/`TransitionTo` combinations silently accepted | cost control |

**The silent-failure rows are the ones a baseline model misses.**
Cross-AZ mounts, ignored `tls` options, bypassed access-point
conditions, and Lambda cold-start timeouts all return success or
wrong-shaped errors. Only Step 9 verification catches the gap.

## Expert heuristic: the access-point-enforcement myth

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic: cross-AZ mount targets

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic: CSI driver access points and Lambda concurrency

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| File system exists and meets baseline | AP inherits FS weaknesses (no encryption, wrong throughput mode) | `aws efs describe-file-systems --file-system-id <FS_ID>` |
| Account ID | Required for AP ARN construction | `aws sts get-caller-identity --query Account --output text` |
| Region | FS and AP are region-scoped | `aws configure get region` |
| Mount target in every compute AZ | Cross-AZ mounts incur cost + latency | `aws efs describe-mount-targets --file-system-id <FS_ID>` |
| Security group allows 2049 from client to mount-target SG | Mount hangs without it | `aws ec2 describe-security-groups --group-ids <MT_SG>` |
| amazon-efs-utils installed | Required for `tls` mount option | `which mount.efs` |
| EFS CSI driver installed (EKS) | Required for dynamic AP provisioning | `kubectl get pods -n kube-system -l app=efs-csi-controller` |
| EFS lifecycle policy (Intelligent-Tiering) | Without it, no IA tier transition | `aws efs describe-lifecycle-configuration --file-system-id <FS_ID>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 9-step provisioning procedure

### Step 1 — Confirm file-system baseline

An access point does NOT remediate FS-level weaknesses. Confirm the
file system has encryption at rest (`Encrypted: true`), an
appropriate throughput mode (`bursting` for most workloads,
`provisioned` for high sustained), and a lifecycle policy for
Intelligent-Tiering if cost control is desired.

```bash
aws efs describe-file-systems --file-system-id <FS_ID> \
  --query 'FileSystems[0].[Encrypted,ThroughputMode,ProvisionedThroughputInMibps]'
aws efs describe-lifecycle-configuration --file-system-id <FS_ID>
```

**Common mistake:** skipping this step because "the AP will enforce
access." The AP controls identity, not encryption or throughput; an
unencrypted FS stays unencrypted.

### Step 2 — Verify mount targets in every compute AZ

For every AZ where ECS tasks, EKS pods, EC2 instances, or Lambda
functions run, confirm a mount target exists. Each AZ may have only
ONE mount target per file system.

```bash
aws efs describe-mount-targets --file-system-id <FS_ID> \
  --query 'MountTargets[].[AvailabilityZoneName,SubnetId,IpAddress,MountTargetId]' --output table

# Compute AZs
aws ecs describe-clusters --clusters <CLUSTER> \
  --query 'clusters[0].defaultCapacityProviderStrategy'
aws ec2 describe-subnets --subnet-ids <SUBNET_IDS> \
  --query 'Subnets[].[AvailabilityZone,SubnetId]' --output table
```

If any compute AZ lacks a mount target, create one:

```bash
aws efs create-mount-target \
  --file-system-id <FS_ID> \
  --subnet-id <SUBNET_ID> \
  --security-groups <MT_SG_ID>
```

**Common mistake:** provisioning a mount target only in the AZ where
the operator's laptop bastion runs; the production ECS task in AZ-B
cross-AZ mounts, silently costing $0.01/GB in each direction.

### Step 3 — Install / verify amazon-efs-utils

The `tls` mount option requires the amazon-efs-utils package. Without
it, `mount -o tls` falls back to plain NFS with no error.

```bash
# Amazon Linux 2023
sudo dnf install -y amazon-efs-utils

# Ubuntu
sudo apt-get install -y amazon-efs-utils

# Verify
which mount.efs
mount -t efs
```

For EKS, install the EFS CSI driver as an add-on:

```bash
aws eks create-addon --cluster-name <CLUSTER> --addon-name aws-efs-csi-driver \
  --service-account-role-arn <IRSA_ROLE_ARN>
```

**Common mistake:** assuming `mount -t nfs4` honors the `tls` option.
Only `mount -t efs` (amazon-efs-utils) wraps the connection in a
stunnel TLS tunnel.

### Step 4 — Create the access point

The access point defines the root directory path, the POSIX identity
for file operations through the AP, and the directory permissions for
auto-creation of the root path.

```bash
aws efs create-access-point \
  --name <AP_NAME> \
  --file-system-id <FS_ID> \
  --posix-user Uid=<UID>,Gid=<GID>,SecondaryGids=<GID1>,<GID2> \
  --root-directory Path=/data/team-a,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=0750}
```

The `PosixUser` (optional but recommended) overrides the NFS
credential: every file operation through the AP runs as that uid/gid,
regardless of the calling client's identity. `RootDirectory.Path` is
the visible root for mounts through the AP; `CreationInfo` controls
how the path is auto-created if it does not exist.

**Common mistake:** setting `PosixUser.Uid=0` (root) "to avoid
permission issues." Every file written through the AP is then owned
by root, breaking downstream least-privilege checks; use the
application's actual uid.

**If it fails:** `AccessDenied` means the caller lacks
`elasticfilesystem:CreateAccessPoint`. `FileSystemNotFound` is a
wrong-region call. `RootDirectory.Path` MUST start with `/`.

### Step 5 — Attach file-system policy with IAM enforcement

The file-system policy is the IAM-level access control. Apply it with
a `Deny` statement keyed on the absence of an access-point ARN to
force all mounts through access points.

```bash
aws efs put-file-system-policy --file-system-id <FS_ID> --policy file://fs-policy.json
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowThroughAccessPointOnly",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<ACCOUNT>:role/<APP_ROLE>" },
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
        "elasticfilesystem:ClientRootAccess"
      ],
      "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>"
    },
    {
      "Sid": "DenyNonAccessPointMounts",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "elasticfilesystem:ClientMount",
      "Resource": "arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:file-system/<FS_ID>",
      "Condition": {
        "Null": { "elasticfilesystem:AccessPointArn": "true" }
      }
    }
  ]
}
```

The `Deny` reads: "Deny any mount that did not come through an
access point." Mounts via the AP alias set the `AccessPointArn` key
and proceed (subject to the Allow); mounts via the FS DNS name do
NOT set the key and are denied.

**Common mistake:** including only the `Allow` statement and assuming
it enforces access-point-only access. Without the explicit `Deny`,
the absence of an `Allow` for direct mounts is NOT sufficient — the
identity-based IAM policy can still grant direct mount. The `Deny`
with the Null condition is what closes the bypass.

### Step 6 — Mount via the access point with TLS

The mount command MUST use the access-point alias, not the file-
system DNS name. Only `mount -t efs` (amazon-efs-utils) honors the
`tls` option.

```bash
# EC2 / on-prem
sudo mkdir -p /mnt/efs/team-a
sudo mount -t efs -o tls,accesspoint=<AP_ID> <FS_ID>:/ /mnt/efs/team-a

# fstab equivalent
<FS_ID>:/ /mnt/efs/team-a efs _netdev,tls,accesspoint=<AP_ID> 0 0
```

The `accesspoint=<AP_ID>` mount option routes the mount through the
named AP; the AP's root directory becomes the visible root of the
mount. The `tls` option wraps the NFS connection in TLS via stunnel.

**Common mistake:** using `mount -t nfs4 -o tls ...` and assuming
TLS is enabled. Plain `nfs4` mounts silently ignore `tls`. The mount
succeeds, traffic is plaintext, and operators have no signal that
encryption in transit is off.

### Step 7 — (ECS/EKS) Wire the access point into the task / pod

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 8 — (Lambda) Configure function with VPC + access-point ARN

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

Moved verbatim to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) - load on demand (see References below).

## NEVER do these things

These anti-patterns cause silent exposure, data-plane bugs, or
compliance violations. Each is observed in real production incidents
— the "why it's wrong" line is the post-mortem finding.

1. **NEVER assume a file-system policy with an `AccessPointArn`
   condition enforces access-point-only mounts.** Why it's wrong: the
   condition key is set ONLY when the client mounts via the access-
   point alias. Mounts via the FS DNS name do NOT set the key; the
   condition matches nothing; the policy is dead text. The remedy is
   a `Deny` with `Null: { elasticfilesystem:AccessPointArn: true }`
   AND ensuring every client mount uses the AP alias.

2. **NEVER mount EFS with `mount -t nfs4 -o tls` and call it
   encrypted in transit.** Why it's wrong: the `tls` option is
   honored only by `mount -t efs` (amazon-efs-utils). Plain `nfs4`
   mounts silently ignore it; the mount succeeds, traffic is
   plaintext, and operators have no signal. Always use `mount -t efs`
   and verify the helper is installed.

3. **NEVER configure a Lambda function to mount EFS from subnets in
   only one AZ of a multi-AZ VPC.** Why it's wrong: Lambda may place
   cold starts in any configured subnet; if that AZ lacks a mount
   target, the EFS mount silently cross-AZ hops or times out at 50s
   (`EFSMountFailureException`). Configure subnets in every AZ where
   the function may be placed.

4. **NEVER omit `elasticfilesystem:ClientRootAccess` from the EFS
   CSI driver's IRSA role.** Why it's wrong: without
   `ClientRootAccess`, the driver can mount but cannot enforce the
   access point's root-directory permissions. Pods see a different
   file tree than the AP specifies, breaking per-pod isolation with
   no error in the controller logs.

5. **NEVER provision EFS without Intelligent-Tiering for stale-data
   workloads.** Why it's wrong: EFS Standard is ~$0.30/GB-month; IA
   is ~$0.016/GB-month — an 18x cost delta. Without a lifecycle
   policy transitioning inactive files after 7-90 days, costs
   escalate silently. Configure `TransitionTo IA`; monitor
   `StorageBytes` by `StorageClass` dimension.

## Output format

```
ACCESS_POINT: <ap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] File-system baseline (encryption, throughput mode): verified
  [✓|✗] Mount targets in every compute AZ: <count> AZs covered
  [✓|✗] amazon-efs-utils / CSI driver installed: verified
  [✓|✗] Access point created: <AP_NAME> (root: /<path>, uid: <uid>, gid: <gid>)
  [✓|✗] File-system policy: AccessPointArn Deny present
  [✓|✗] Mount via AP alias with TLS: verified
  [✓|✗] (ECS/EKS) Integration wired: <ECS task role | EKS storage class>
  [✓|✗] (Lambda) Function VPC + access-point ARN: configured
  [✓|✗] Intelligent-Tiering lifecycle: <N> days to IA
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
ACCESS_POINT: <ap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] File-system baseline (encryption, throughput mode): verified
  [✓|✗] Mount targets in every compute AZ: <count> AZs covered
  [✓|✗] amazon-efs-utils / CSI driver installed: verified
  [✓|✗] Access point created: <AP_NAME> (root: /<path>, uid: <uid>, gid: <gid>)
  [✓|✗] File-system policy: AccessPointArn Deny present
  [✓|✗] Mount via AP alias with TLS: verified
  [✓|✗] (ECS/EKS) Integration wired: <ECS task role | EKS storage class>
  [✓|✗] (Lambda) Function VPC + access-point ARN: configured
  [✓|✗] Intelligent-Tiering lifecycle: <N> days to IA
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 9
   checklist items.** Every item MUST appear with a status marker:
   `[✓]`, `[✗]`, or `[OPTIONAL]` (e.g., Lambda when no Lambda is
   involved). Omitting a row implies it was not evaluated.

2. **NEVER mark the file-system policy as `[✓]` without confirming
   the `Deny` with `Null: { elasticfilesystem:AccessPointArn: true }`.**
   An `Allow` with the AP ARN is NOT sufficient — identity-based IAM
   can still grant direct mount. The Deny is what closes the bypass;
   without it, "access-point-only" is a false claim.

3. **NEVER mark the mount via AP alias as `[✓]` without confirming
   the client uses `mount -t efs` (not `mount -t nfs4`) AND the
   `accesspoint=<AP_ID>` option.** `nfs4` mounts silently ignore
   `tls`; without `accesspoint=`, the AP's root directory is bypassed
   and the file-system policy's AccessPointArn condition matches
   nothing.

4. **NEVER mark the EKS CSI driver integration as `[✓]` without
   confirming the IRSA role includes `elasticfilesystem:ClientRootAccess`.**
   Without it, the driver mounts but cannot enforce the AP's
   directory permissions; pods see a different file tree than the AP
   specifies, with no error in the controller logs.

5. **NEVER mark mount targets as `[✓]` without listing every compute
   AZ and matching it to a mount target.** A bare `[✓] Mount targets:
   verified` is non-compliant — list the AZs covered and the count.
   `MountTargets[].AvailabilityZoneName` MUST be a superset of the
   compute AZs.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] No mount target in us-west-2b — create one in subnet-2`. A
   bare `[✗]` with no explanation is non-compliant.

### Perfect example output — READY_TO_DEPLOY

```text
ACCESS_POINT: team-a-ap
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] File-system baseline: fs-abc123def, Encrypted=true, ThroughputMode=bursting
  [✓] Mount targets in every compute AZ: 3 AZs covered (use1-az1, use1-az2, use1-az3)
  [✓] amazon-efs-utils installed on EC2 ASG; EFS CSI driver v1.7.0 on EKS
  [✓] Access point created: team-a-ap (root: /data/team-a, uid: 1000, gid: 1000, perms: 0750)
  [✓] File-system policy: Deny on Null:AccessPointArn + Allow through AP
  [✓] Mount via AP alias with TLS: mount -t efs -o tls,accesspoint=fsap-xyz
  [OPTIONAL] (ECS/EKS) Integration: not requested for this deploy
  [OPTIONAL] (Lambda) Function VPC + AP: not requested for this deploy
  [✓] Intelligent-Tiering lifecycle: TransitionTo IA after 30 days
VERIFICATION_COMMANDS:
  aws efs describe-access-points --access-point-id fsap-xyz
  aws efs describe-file-system-policy --file-system-id fs-abc123def
  aws efs describe-mount-targets --file-system-id fs-abc123def
  aws efs describe-lifecycle-configuration --file-system-id fs-abc123def
```

### Perfect example output — PREREQUISITES_MISSING

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

**Self-check before emit:**
- [ ] All 9 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] File-system policy Deny uses `Null: { elasticfilesystem:AccessPointArn: true }`?
- [ ] Mount command uses `mount -t efs` with `accesspoint=` option?
- [ ] EKS CSI driver IRSA role includes `ClientRootAccess`?
- [ ] Mount targets cover EVERY compute AZ (list them)?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — skill overview, reasoning framework, the three expert heuristics, Steps 7-8 (ECS/EKS/Lambda integration) deep-dives, and recent AWS features, moved verbatim from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — secondary example output (PREREQUISITES_MISSING), moved verbatim from SKILL.md
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — pre-existing provisioning CLI reference, extended with the Step 9 verification command listing moved verbatim from SKILL.md
- [references/file-system-policy-examples.md](references/file-system-policy-examples.md) — pre-existing file-system policy JSON examples
