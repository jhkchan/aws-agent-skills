# End-to-End Example: EFS Access Points Deployment

A walkthrough showing how to use the `efs-access-point-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are setting up an EFS access point on a shared data-lake file
system so an internal analytics application can read and write only
its own subdirectory. The file system already meets the production
baseline (encryption at rest, bursting throughput, Intelligent-
Tiering lifecycle). You need:

- Access point with POSIX identity uid 1000, gid 1000
- Root directory `/data/team-a`, auto-created with perms 0750
- File-system policy that forces access-point-only mounts
  (Deny on `Null:AccessPointArn`)
- TLS encryption in transit
- Mount from EC2 ASG across three AZs

File system: `fs-0abc123def`
Region: `us-east-1`
Account: `123456789012`
AP name: `team-a-ap`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-efs-access-point
```

Then paste the access-point requirements.

### Option B: Natural language

```
You: "Provision an EFS access point for fs-0abc123def in
      us-east-1, account 123456789012. AP name team-a-ap, POSIX
      uid 1000 gid 1000, root /data/team-a with perms 0750.
      Attach the file-system policy that forces access-point-only
      mounts via the Null:AccessPointArn Deny, and mount with TLS."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create efs access point"
```

Output:

```
[Phase: Deploy | Skills routed: efs-access-point-deployer]
Primary route: efs-access-point-deployer (score: 19)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ACCESS_POINT: team-a-ap
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] File-system baseline: fs-0abc123def, Encrypted=true, ThroughputMode=bursting
  [✓] Mount targets in every compute AZ: 3 AZs covered (use1-az1, use1-az2, use1-az3)
  [✓] amazon-efs-utils installed on EC2 ASG
  [✓] Access point created: team-a-ap (root: /data/team-a, uid: 1000, gid: 1000, perms: 0750)
  [✓] File-system policy: Deny on Null:AccessPointArn + Allow through AP
  [✓] Mount via AP alias with TLS: mount -t efs -o tls,accesspoint=fsap-xxxx
  [OPTIONAL] (ECS/EKS) Integration: not requested for this deploy
  [OPTIONAL] (Lambda) Function VPC + AP: not requested for this deploy
  [✓] Intelligent-Tiering lifecycle: TransitionTo IA after 30 days
VERIFICATION_COMMANDS:
  aws efs describe-access-points --file-system-id fs-0abc123def
  aws efs describe-file-system-policy --file-system-id fs-0abc123def
  aws efs describe-mount-targets --file-system-id fs-0abc123def
  aws efs describe-lifecycle-configuration --file-system-id fs-0abc123def
```

---

## Step 3 — Provisioning commands

```bash
# Step 4: Create the access point
AP_ID=$(aws efs create-access-point \
  --name team-a-ap \
  --file-system-id fs-0abc123def \
  --posix-user Uid=1000,Gid=1000,SecondaryGids=2000 \
  --root-directory Path=/data/team-a,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=0750} \
  --query AccessPointId --output text)
echo "Access point ID: $AP_ID"

# Step 5: File-system policy with the AccessPointArn Deny (critical)
aws efs put-file-system-policy --file-system-id fs-0abc123def --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowThroughAccessPoint",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::123456789012:role/TeamAAppRole" },
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
        "elasticfilesystem:ClientRootAccess"
      ],
      "Resource": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-0abc123def",
      "Condition": {
        "StringEquals": {
          "elasticfilesystem:AccessPointArn": "arn:aws:elasticfilesystem:us-east-1:123456789012:access-point/'"$AP_ID)"'"
        }
      }
    },
    {
      "Sid": "DenyNonAccessPointMounts",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "elasticfilesystem:ClientMount",
      "Resource": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-0abc123def",
      "Condition": { "Null": { "elasticfilesystem:AccessPointArn": "true" } }
    }
  ]
}'

# Step 6: Mount via the access point with TLS (uses mount -t efs, NOT nfs4)
sudo mkdir -p /mnt/efs/team-a
sudo mount -t efs -o tls,accesspoint=$AP_ID fs-0abc123def:/ /mnt/efs/team-a
```

---

## Step 4 — Post-deployment verification

```bash
aws efs describe-access-points --access-point-id $AP_ID
# Expected: PosixUser.Uid=1000, RootDirectory.Path=/data/team-a

aws efs describe-file-system-policy --file-system-id fs-0abc123def
# Expected: two statements — AllowThroughAccessPoint + DenyNonAccessPointMounts

aws efs describe-mount-targets --file-system-id fs-0abc123def
# Expected: 3 mount targets in 3 distinct AZs

aws efs describe-lifecycle-configuration --file-system-id fs-0abc123def
# Expected: TransitionToIA after 30 days

# Confirm the mount is using TLS (stunnel process visible)
mount | grep efs
sudo ss -tnp | grep 2049
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Null:AccessPointArn Deny | Omitted | Explicit Deny in file-system policy | Without the Deny, identity-based IAM can still grant direct mounts via `fs-<id>.efs.<region>.amazonaws.com`, bypassing the access-point-only intent. |
| Mount via `mount -t efs` | `mount -t nfs4 -o tls` | `mount -t efs -o tls,accesspoint=<AP_ID>` | Plain `nfs4` silently ignores the `tls` option; the mount succeeds but traffic is plaintext. |
| Mount target in every compute AZ | Provisioned only in one AZ | 3 AZs covered, listed explicitly | A cross-AZ mount succeeds but silently incurs $0.01/GB each direction and 10-50 ms latency per op. |
| POSIX identity uid 1000 | Omitted (uses NFS credential) | Explicit PosixUser Uid=1000,Gid=1000 | Without the explicit PosixUser, files are created with the calling client's uid, breaking downstream ownership checks. |
| Intelligent-Tiering verification | Skipped | Confirmed via describe-lifecycle-configuration | Without a lifecycle policy, costs escalate at Standard pricing (~$0.30/GB-month vs $0.016/GB-month IA). |

---

## Related artifacts

- **Skill definition:** `skills/efs-access-point-deployer/SKILL.md`
- **Policy templates:** `skills/efs-access-point-deployer/references/file-system-policy-examples.md`
- **Provisioning CLI commands:** `skills/efs-access-point-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-efs-access-point.md`
- **Eval suite:** `skills/efs-access-point-deployer/evals/evals.json`
- **Legacy test cases:** `skills/efs-access-point-deployer/eval/test-cases.yaml`
