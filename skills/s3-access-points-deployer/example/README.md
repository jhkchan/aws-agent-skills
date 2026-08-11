# End-to-End Example: S3 Access Points Deployment (VPC-only)

A walkthrough showing how to use the `s3-access-points-deployer` skill
from invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are setting up a VPC-only access point on a shared data lake bucket
so an internal analytics service can read and write only its own prefix.
The bucket already meets the production baseline (BPA, SSE-KMS,
versioning). You need:

- Access point reachable only from VPC `vpc-0abc123def456`
- Per-team prefix scoping: `team-a/`
- The global bucket hostname bypassed blocked (true VPC-only)
- Per-AP Block Public Access
- An alias usable in internal DNS

Bucket: `prod-shared-data`
Region: `us-east-1`
Account: `123456789012`
AP name: `team-a-vpc-ap`
Role: `arn:aws:iam::123456789012:role/TeamARole`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-s3-access-points
```

Then paste the access-point requirements.

### Option B: Natural language

```
You: "Provision a VPC-only access point for prod-shared-data in
      us-east-1, account 123456789012. AP name team-a-vpc-ap, VPC
      vpc-0abc123def456. Team A's role TeamARole should read/write
      the team-a/ prefix only. Include the bucket-policy Deny that
      blocks the global hostname and enable per-AP BPA."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create s3 access point"
```

Output:

```
[Phase: Deploy | Skills routed: s3-access-points-deployer]
Primary route: s3-access-points-deployer (score: 19)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ACCESS_POINT: team-a-vpc-ap
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Bucket baseline verified (BPA, SSE-KMS, versioning)
  [✓] Network origin: VPC (vpc-0abc123def456)
  [✓] VPC endpoint + private DNS configured (vpce-0def456)
  [✓] Access point created: team-a-vpc-ap (alias: team-a-vpc-ap-12ab34cd.s3-accesspoint.us-east-1.amazonaws.com)
  [✓] Access point policy: principal TeamARole, prefix team-a/
  [✓] Through-AP-only bucket-policy Deny (s3:DataAccessPointArn)
  [✓] Per-AP Block Public Access: all 4 settings True
  [OPTIONAL] Object Lambda / MRAP / cross-account: none
VERIFICATION_COMMANDS:
  aws s3control get-access-point --account-id 123456789012 --name team-a-vpc-ap
  aws s3control get-access-point-policy --account-id 123456789012 --name team-a-vpc-ap
  aws s3control get-access-point-public-access-block --account-id 123456789012 --name team-a-vpc-ap
  aws s3api get-bucket-policy --bucket prod-shared-data
  aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=vpc-0abc123def456
```

---

## Step 3 — Provisioning commands

```bash
# Step 4: Create the VPC-origin access point
aws s3control create-access-point \
  --account-id 123456789012 \
  --name team-a-vpc-ap \
  --bucket prod-shared-data \
  --vpc-configuration VpcId=vpc-0abc123def456

# Step 5: Access point policy (note the AP ARN, not the bucket ARN)
aws s3control put-access-point-policy \
  --account-id 123456789012 \
  --name team-a-vpc-ap \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "TeamAPrefixReadWrite",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/TeamARole"},
      "Action": ["s3:GetObject","s3:PutObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:us-east-1:123456789012:accesspoint/team-a-vpc-ap",
        "arn:aws:s3:us-east-1:123456789012:accesspoint/team-a-vpc-ap/team-a/*"
      ]
    }]
  }'

# Step 6: Through-AP-only bucket-policy Deny (the critical invariant)
aws s3api put-bucket-policy \
  --bucket prod-shared-data \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "RequireThroughAccessPoint",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::prod-shared-data",
        "arn:aws:s3:::prod-shared-data/*"
      ],
      "Condition": {
        "StringNotEqualsIfExists": {
          "s3:DataAccessPointArn": "arn:aws:s3:us-east-1:123456789012:accesspoint/team-a-vpc-ap"
        },
        "Null": {"aws:SourceVpc": "false"}
      }
    }]
  }'

# Step 7: Per-AP Block Public Access
aws s3control put-access-point-public-access-block \
  --account-id 123456789012 \
  --name team-a-vpc-ap \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

## Step 4 — Post-deployment verification

```bash
aws s3control get-access-point --account-id 123456789012 --name team-a-vpc-ap
# Expected: NetworkOrigin=VPC, VpcConfiguration.VpcId=vpc-0abc123def456

aws s3control get-access-point-policy --account-id 123456789012 --name team-a-vpc-ap
# Expected: TeamARole principal with team-a/ prefix scope

aws s3control get-access-point-public-access-block --account-id 123456789012 --name team-a-vpc-ap
# Expected: all 4 settings True

aws s3api get-bucket-policy --bucket prod-shared-data
# Expected: RequireThroughAccessPoint statement with s3:DataAccessPointArn

aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=vpc-0abc123def456
# Expected: gateway endpoint for com.amazonaws.us-east-1.s3
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Through-AP-only Deny | Not included | Bucket-policy Deny on `Null: s3:DataAccessPointArn` | Without this, the bucket is still reachable via the global hostname by any principal with `s3:GetObject`. The VPC-only claim is false. |
| AP policy Resource ARN | `arn:aws:s3:::prod-shared-data` | `arn:aws:s3:us-east-1:123456789012:accesspoint/team-a-vpc-ap` | Requests through the AP present the AP ARN, not the bucket ARN. A bucket-ARN policy matches nothing. |
| Per-AP Block Public Access | Skipped | All 4 settings True | Account-level BPA propagates but per-AP BPA gives explicit visibility into the AP's posture, critical for cross-account scenarios. |
| VPC endpoint requirement | Skipped | Verified before AP creation | VPC-origin AP without a VPC endpoint is unreachable from inside the VPC; operators fall back to the global hostname, defeating VPC-only. |
| Alias capture | Skipped | Verified and surfaced | The auto-generated alias is the DNS-compatible hostname the application will use; skipping the capture forces a later lookup. |

---

## Related artifacts

- **Skill definition:** `skills/s3-access-points-deployer/SKILL.md`
- **Policy templates:** `skills/s3-access-points-deployer/references/access-point-policy-examples.md`
- **Provisioning CLI commands:** `skills/s3-access-points-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-s3-access-points.md`
- **Eval suite:** `skills/s3-access-points-deployer/evals/evals.json`
- **Legacy test cases:** `skills/s3-access-points-deployer/eval/test-cases.yaml`
