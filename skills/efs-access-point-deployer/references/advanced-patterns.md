# Advanced Patterns (load on demand) — EFS Access Points Deployer

Skill overview, the reasoning framework behind the 9-step order, the three expert heuristics, the ECS/EKS (Step 7) and Lambda (Step 8) integration deep-dives, and recent AWS features, moved verbatim from SKILL.md.

---

## What this skill does (moved from SKILL.md)

Provisions EFS Access Points and surrounding primitives (per-AZ
mount targets, IAM file-system policy, amazon-efs-utils mount
helper, TLS, EFS CSI driver wiring, Lambda mount config) with
production defaults. The skill walks a 9-step procedure, surfaces
the silent-failure modes unique to EFS (most dangerous: the file-
system policy is NOT enforced unless the mount uses the access-point
ARN; a mount target in a different AZ from the client still works
but silently incurs cross-AZ fees and latency; the AP's POSIX
identity overrides the NFS credential, so files are created with a
different owner than the caller expects), and emits a READY_TO_DEPLOY
checklist verifying every item against actual state. The single most
common incident this skill prevents: an operator creates an access
point, applies a restrictive file-system policy, but mounts via the
file-system DNS name (not the access-point alias) — the policy's
`AccessPointArn` condition matches nothing, the mount succeeds, and
the IAM restriction is a dead letter.

## Reasoning framework (why the provisioning order matters) (moved from SKILL.md)

EFS Access Points look like "a named entry point to a file system"
but the underlying model has four traps:

1. **The access point is a separate ARN with its own root directory
   and POSIX identity, but the FILE SYSTEM POLICY is what enforces
   IAM.** Effective permission on a request through the AP =
   (file-system policy) ∩ (IAM identity policy). A file-system policy
   that references the AP ARN via `elasticfilesystem:AccessPointArn`
   only takes effect when the mount uses the access-point alias —
   mounting via `fs-xxxxxxx.efs.<region>.amazonaws.com` bypasses the
   condition silently.

2. **The access point's POSIX identity overrides the NFS credential.**
   When the AP has a `PosixUser` configured, files created through
   that AP are owned by the AP's uid/gid, NOT the uid/gid the client
   sent. Operators who expect "the calling user owns the file" get
   surprising ownership that breaks downstream permission checks.

3. **A mount target in a different AZ from the client still works.**
   EFS does NOT error on cross-AZ mounts; it charges cross-AZ data-
   transfer fees (typically $0.01/GB in each direction) and adds
   10-50 ms of latency per operation. Operators discover this only on
   the bill, weeks later. One mount target per AZ where compute runs
   is the invariant.

4. **The `tls` mount option requires amazon-efs-utils; with the
   legacy `mount -t nfs4` path, the option is silently ignored.**
   Operators who set `tls` in fstab but mount via plain `nfs4` get a
   plaintext mount with no error. TLS uses port 2049 over a stunnel
   wrapper — the same port, but the helper wraps the connection.

## Expert heuristic: the access-point-enforcement myth (moved from SKILL.md)

The most dangerous misconception: "I configured a file-system policy
with an `AccessPointArn` condition, so the file system is access-
point-only." It is not.

```text
Operator thinks:                      What actually happens:
File-system policy with                 File-system policy with
  AccessPointArn condition →              AccessPointArn condition →
  file system only reachable              file system still reachable
  through the named access point          via fs-xxxxxxx.efs.<region>.amazonaws.com
                                          (condition matches nothing on that path;
                                           mount succeeds; IAM is bypassed)
```

The `elasticfilesystem:AccessPointArn` condition key is set ONLY when
the client mounts via the access-point alias
(`fs-xxxxxxx.access-point-yyyyyyyy.<region>.efs.amazonaws.com`). A
mount via the file-system DNS name does NOT set the key; the policy's
condition evaluates to false; the `Deny` does not fire. Remedy:
(1) keep the file-system policy's `Deny` with
`Null: { elasticfilesystem:AccessPointArn: true }` to deny any mount
that did NOT come through an access point, AND (2) ensure every
client mount command uses the access-point alias. The DNS-name bypass
is the #1 EFS production incident.

## Expert heuristic: cross-AZ mount targets (moved from SKILL.md)

EFS allows mounting across AZs without error. The mount succeeds,
files are accessible, but every byte incurs cross-AZ data-transfer
charges ($0.01/GB each direction) and every operation picks up
10-50 ms of cross-AZ latency. At 1 TB/day with 100 ECS tasks in one
AZ mounting a single-AZ FS, this is ~$600/month and 50 ms p99 on
every file open — with no error in any log. Remedy: one mount
target in every AZ where any client runs; the
`MountTargets[].AvailabilityZoneName` set MUST be a superset of the
compute AZs.

## Expert heuristic: CSI driver access points and Lambda concurrency (moved from SKILL.md)

EKS pods mount EFS via the EFS CSI driver, which dynamically creates
access points per PVC by default. Two operational truths are missed:

1. **The CSI driver's IRSA role needs `elasticfilesystem:ClientRootAccess`.**
   Without it, the driver can mount but cannot enforce the access
   point's root-directory permissions; pods see a different file
   tree than expected. The role's policy MUST include
   `elasticfilesystem:ClientMount`, `ClientWrite`, AND
   `ClientRootAccess`.

2. **Lambda EFS throughput is bounded by the FS's
   `ProvisionedThroughputInMibps` once bursting is exhausted.**
   1,000 concurrent Lambda mounts hitting the same FS exhaust burst
   credits in minutes; throughput drops to baseline and Lambdas time
   out on file I/O with no error in the function's own metrics.
   Remedy: monitor `BurstCreditBalance` / `PercentIOLimit`, provision
   throughput for high-concurrency workloads, or shard across FSes.

## Step 7 — (ECS/EKS) Wire the access point into the task / pod (moved from SKILL.md)

#### 7a. ECS task definition with EFS volume

```bash
aws ecs register-task-definition --family <FAMILY> \
  --container-definitions file://containers.json \
  --volumes file://volumes.json
```

```json
// volumes.json
[{
  "name": "efs-team-a",
  "efsVolumeConfiguration": {
    "fileSystemId": "<FS_ID>",
    "transitEncryption": "ENABLED",
    "accessPointId": "<AP_ID>",
    "iam": "ENABLED"
  }
}]
```

The task execution role MUST include `elasticfilesystem:ClientMount`,
`ClientWrite`, and `ClientRootAccess` on the FS ARN. `transitEncryption:
ENABLED` enforces TLS at the ECS level (rejected if the mount helper
is absent from the AMI).

#### 7b. EKS storage class with EFS CSI driver

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: <FS_ID>
  directoryPerms: "700"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
```

The CSI driver dynamically creates one access point per PVC (within
the `gidRangeStart`-`gidRangeEnd` range). The IRSA role MUST include
`elasticfilesystem:CreateAccessPoint`, `DeleteAccessPoint`,
`ClientMount`, `ClientWrite`, AND `ClientRootAccess` — missing
`ClientRootAccess` silently produces a mount that ignores the AP's
directory permissions.

**Common mistake:** using `provisioningMode: efs-ap` with a static
`accessPointId`. The CSI driver supports both dynamic AP-per-PVC and
static AP; mixing the modes in one StorageClass silently produces
unexpected AP proliferation.

## Step 8 — (Lambda) Configure function with VPC + access-point ARN (moved from SKILL.md)

Lambda mounts EFS via the function's VPC config. Every function
subnet MUST have a corresponding mount target (see Step 2).

```bash
aws lambda update-function-configuration \
  --function-name <FN_NAME> \
  --vpc-config SubnetIds=<SUBNET1>,<SUBNET2>,SecurityGroupIds=<SG_ID> \
  --file-system-configs Arn=arn:aws:elasticfilesystem:<REGION>:<ACCOUNT>:access-point/<AP_ID>,LocalMountPath=/mnt/efs
```

The function role MUST include `elasticfilesystem:ClientMount`,
`ClientWrite`, and (optionally) `ClientRootAccess` on the FS ARN.
`LocalMountPath` MUST start with `/mnt/`.

**Common mistake:** configuring subnets in only one AZ of a multi-AZ
VPC. Cold starts in the other AZ silently time out (no mount target
→ cross-AZ hop → 50s EFS mount timeout). Configure subnets in every
AZ where the function may be placed.

## Recent AWS features (moved from SKILL.md)

- **EFS CSI driver dynamic provisioning (GA)**: `provisioningMode:
  efs-ap` creates one access point per PVC; the IRSA role MUST
  include `elasticfilesystem:ClientRootAccess` for the AP's directory
  permissions to take effect.
- **Lambda EFS (GA)**: functions mount via VPC + access-point ARN;
  every function subnet MUST have a corresponding mount target or
  cold starts time out at 50s with no error in logs.
- **EFS Intelligent-Tiering**: lifecycle policies transition files
  to IA after 7-90 days; `TransitionAfter` 0 is invalid. Monitor
  `StorageBytes` by `StorageClass` dimension. IA request pricing
  differs from Standard — read-heavy workloads may not save.
- **EFS automatic backups**: AWS Backup supports continuous
  (incremental) EFS backups; the backup role needs
  `elasticfilesystem:Backup` on the FS ARN.
- **EFS provisioned throughput**: pins throughput independent of
  storage size; required for high-concurrency workloads. Monitor
  `BurstCreditBalance`.
- **Cross-account EFS mounts**: a file-system policy can grant
  `elasticfilesystem:ClientMount` to a foreign account; the client
  still needs VPC peering or TGW reachability to the mount target.

