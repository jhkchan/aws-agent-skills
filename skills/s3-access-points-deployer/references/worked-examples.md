# Worked Examples — S3 Access Points Deployer

Load-on-demand output templates and example blocks moved verbatim from
SKILL.md.

## Output format (generic template)

```
ACCESS_POINT: <ap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bucket baseline (BPA, SSE, versioning): verified
  [✓|✗] Network origin: Internet | VPC (VPC ID: <id>)
  [✓|✗] VPC endpoint + private DNS: configured (VPC origin only)
  [✓|✗] Access point created: <AP_NAME> (alias: <alias>)
  [✓|✗] Access point policy: attached (principal: <role>, prefix: <prefix>)
  [✓|✗] Through-AP-only bucket-policy Deny: present (s3:DataAccessPointArn)
  [✓|✗] Per-AP Block Public Access: all 4 settings True (VPC origin)
  [✓|✗] Optional feature: Object Lambda | MRAP | cross-account | none
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## Perfect example output — PREREQUISITES_MISSING

```text
ACCESS_POINT: team-a-vpc-ap
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Bucket baseline: prod-shared-data, BPA all 4 True, SSE-S3
  [✓] Network origin: VPC (VPC ID: vpc-0abc123)
  [✗] VPC endpoint: no gateway endpoint for com.amazonaws.us-east-1.s3 in VPC vpc-0abc123 — create endpoint with AP-scoped policy first
  [✓] Access point created: team-a-vpc-ap (alias: team-a-vpc-ap-12ab34cd.s3-accesspoint.us-east-1.amazonaws.com)
  [✓] Access point policy: attached, principal TeamAReadRole, prefix team-a/
  [✗] Through-AP-only bucket-policy Deny: NOT present — bucket still bypassable via global hostname
  [✓] Per-AP Block Public Access: all 4 settings True
  [OPTIONAL] Object Lambda / MRAP / cross-account: none
VERIFICATION_COMMANDS:
  aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=vpc-0abc123
  aws s3api get-bucket-policy --bucket prod-shared-data
```
