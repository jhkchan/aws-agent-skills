# Example usage: opensearch-snapshot-troubleshooter

A walkthrough showing the skill diagnosing a
`repository_verification_exception` that mimics a corrupt snapshot,
demonstrating the symptom-to-layer triage, the IAM-vs-corruption
decision (verification failure is almost always IAM, not blob
corruption), the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and
the bucket-policy root cause.

## Input (user prompt)

> Our OpenSearch domain `prod-logs-cluster` started failing manual
> snapshots yesterday. Every snapshot attempt returns
> `repository_verification_exception`. We thought the snapshot was
> corrupt and spent two hours debugging the S3 blobs. Help us find
> the actual root cause.

```text
DomainName: prod-logs-cluster
EngineVersion: OpenSearch_2.13
Repository: s3-backups
Bucket: prod-os-snapshots-us-east-1
BucketRegion: us-east-1
SnapshotRoleArn: arn:aws:iam::111111111111:role/opensearch-snapshot-role
SnapshotRoleTrustPolicy: lists
  "Service": "opensearchservice.amazonaws.com"
  with aws:SourceAccount condition — CORRECT
SnapshotRoleIdentityPolicy: grants s3:PutObject, s3:GetObject,
  s3:DeleteObject, s3:ListBucket on the bucket ARN — CORRECT
BucketPolicy:
  {
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "opensearchservice.amazonaws.com"},
        "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::prod-os-snapshots-us-east-1",
          "arn:aws:s3:::prod-os-snapshots-us-east-1/*"]
      }
    ]
  }
Note: Bucket policy principal is the SERVICE PRINCIPAL, not the
  snapshot role ARN.

Last log line: "repository_verification_exception:
  [[s3-backups]] verification failed"

Verification-file check:
  s3 ls s3://prod-os-snapshots-us-east-1/s3-backups/verification-file-*
  returns one object (write succeeded), but the read-back by the
  OpenSearch S3 client fails with AccessDenied.

PUT _snapshot body (registration succeeded, returned 200):
  {
    "type": "s3",
    "settings": {
      "bucket": "prod-os-snapshots-us-east-1",
      "region": "us-east-1",
      "base_path": "s3-backups",
      "iam_role_arn": "arn:aws:iam::111111111111:role/opensearch-snapshot-role",
      "compress": true
    }
  }
```

## Skill output

```text
TARGET: prod-logs-cluster (repository: s3-backups)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Bucket policy on prod-os-snapshots-us-east-1 is keyed to
  the OpenSearch service principal
  (opensearchservice.amazonaws.com) instead of the snapshot role
  ARN (arn:aws:iam::111111111111:role/opensearch-snapshot-role).
  The role's session ARN does not match the service principal, so
  the read-back of the verification file fails with AccessDenied
  even though the write succeeded. The role trust policy and role
  identity policy are correct; only the bucket policy principal is
  wrong (Step 2).
LAYER: IAM_ROLE_S3_ACCESS
EVIDENCE:
  - Symptom: every snapshot attempt returns
    repository_verification_exception; registration (PUT _snapshot)
    returned 200, so the repository metadata is intact.
  - Probe: aws s3api get-bucket-policy --bucket
    prod-os-snapshots-us-east-1 returns a policy whose Principal is
    {"Service": "opensearchservice.amazonaws.com"} — the snapshot
    role ARN does not appear anywhere in the bucket policy.
  - Probe: aws iam simulate-principal-policy on the snapshot role
    returns Decision: implicitDeny for s3:GetObject on
    arn:aws:s3:::prod-os-snapshots-us-east-1/* because the bucket
    policy does not grant the role.
  - Probe: aws s3 ls s3://prod-os-snapshots-us-east-1/s3-backups/
    verification-file-* returns one object (write path works);
    OpenSearch's read-back fails because the role is not granted
    s3:GetObject in the bucket policy.
  - Passing: snapshot role trust policy lists
    opensearchservice.amazonaws.com with aws:SourceAccount
    condition (registration trust is correct).
  - Passing: snapshot role identity policy grants the required S3
    actions on the bucket ARN (identity policy is correct).
  - Passing: PUT _snapshot body includes correct bucket, region,
    iam_role_arn, and base_path (registration body is correct).
REMEDIATION:
  1. Update the bucket policy to grant the SNAPSHOT ROLE ARN
     (not the service principal) the required S3 actions:

     aws s3api put-bucket-policy --bucket prod-os-snapshots-us-east-1 --policy '{
       "Version": "2012-10-17",
       "Statement": [
         {"Sid": "ListBucketForSnapshot", "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::111111111111:role/opensearch-snapshot-role"},
          "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
          "Resource": "arn:aws:s3:::prod-os-snapshots-us-east-1"},
         {"Sid": "ReadWriteSnapshotObjects", "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::111111111111:role/opensearch-snapshot-role"},
          "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
          "Resource": "arn:aws:s3:::prod-os-snapshots-us-east-1/s3-backups/*"}
       ]
     }'

  2. Re-run verification:

     curl -X POST "https://$ENDPOINT/_snapshot/s3-backups/_verify?verbose=true"

  3. Take a new manual snapshot and confirm SUCCESS:

     curl -X PUT "https://$ENDPOINT/_snapshot/s3-backups/snap-verify-$(date +%s)"
     curl -sS "https://$ENDPOINT/_snapshot/s3-backups/_status" | jq '.snapshots[-1].state'

CONFIRM: Before updating the bucket policy, emit and await:
  "CONFIRM: About to overwrite the bucket policy on
   prod-os-snapshots-us-east-1 to grant the snapshot role ARN.
   Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished IAM failure from snapshot corruption.** A generic
   assistant says "the snapshot is corrupt, re-take it." The skill
   recognises that `repository_verification_exception` on the FIRST
   snapshot after registration is almost always IAM, not blob
   corruption — the snapshot never even ran.

2. **Identified the wrong principal in the bucket policy.** The skill
   reads the bucket policy and identifies that
   `"Principal": {"Service": "opensearchservice.amazonaws.com"}` is
   the bug. The service principal goes in the ROLE TRUST, not the
   bucket policy. The role's session ARN does not match the service
   principal.

3. **Confirmed via the verification-file asymmetry.** The
   verification-file check (write succeeded, read-back failed) is
   the smoking gun for a bucket-policy read-path block. A generic
   assistant does not know to look for this asymmetry.

4. **Ruled out the role identity policy with an authoritative probe.**
   `simulate-principal-policy` is authoritative; the skill uses it
   instead of eyeballing the JSON. The simulation returns
   `implicitDeny` for `s3:GetObject` on the bucket because the
   bucket policy is the missing grant.

5. **Recommended the bucket-policy fix, not a repository re-register.**
   The primary remediation is updating the bucket policy to grant
   the role ARN. Re-registering the repository (a common reflex)
   would overwrite the prior settings without fixing the underlying
   IAM gap.

## Slash-command invocation

```
/aws:troubleshoot-opensearch-snapshot
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why prod-logs-cluster snapshot verification fails"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: opensearch-snapshot-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate that snapshots succeed:

```bash
# Verify the new bucket policy grants the role
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::111111111111:role/opensearch-snapshot-role" \
  --action-names s3:GetObject s3:PutObject s3:ListBucket \
  --resource-arns "arn:aws:s3:::prod-os-snapshots-us-east-1" \
    "arn:aws:s3:::prod-os-snapshots-us-east-1/s3-backups/*" \
  --profile default --output json

# Verify the repository verifies cleanly
ENDPOINT=$(aws opensearch describe-domain --domain-name prod-logs-cluster \
  --query 'Domain.Endpoint' --output text --profile default)
curl -X POST "https://$ENDPOINT/_snapshot/s3-backups/_verify?verbose=true"

# Take a test snapshot and watch state
curl -X PUT "https://$ENDPOINT/_snapshot/s3-backups/snap-verify-$(date +%s)" --profile default
curl -sS "https://$ENDPOINT/_snapshot/s3-backups/_status" | jq '.snapshots[-1].state'
```

Then monitor the domain's `AutomatedSnapshotFailure` metric for 1-2
hours to confirm no new failures.
