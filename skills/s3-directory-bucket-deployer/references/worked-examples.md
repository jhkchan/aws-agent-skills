# Worked Examples — s3-directory-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

### Perfect example output — PREREQUISITES_MISSING


```text
DIRECTORY_BUCKET_SPEC: my-app-data--use1-az1--x-s3
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] AZ ID resolved: use1-az1 (from AZ name us-east-1a)
  [✓] Directory bucket name format: my-app-data--use1-az1--x-s3 verified
  [✗] Directory bucket created: not yet created — run create-directory-bucket with --data-redundancy SingleAvailabilityZone
  [✗] Encryption: not configured — specify SSE-S3 or SSE-KMS key
  [✗] Bucket policy: not configured — use s3express ARN format
  [✗] Zone-affinity compute: EC2 deployed in use1-az2, NOT use1-az1 — relocate compute to bucket's AZ
  [N/A] Table bucket: not applicable
  [✗] Unsupported features: operator requested CRR — directory buckets do NOT support cross-region replication
VERIFICATION_COMMANDS:
  aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,Placement.AvailabilityZoneId]' --output table
  aws s3api list-buckets --query 'Buckets[?Name==`my-app-data--use1-az1--x-s3`]' --output json
```

**Self-check before emit:**
- [ ] All 8 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] Directory bucket name shows the full `base--az-id--x-s3` format?
- [ ] Bucket creation verification cites `BucketType: Directory`?
- [ ] Zone-affinity compute cites the specific AZ ID matching the bucket?
- [ ] Table bucket (if applicable) cites the `s3tables` API?
- [ ] Unsupported features (CRR, versioning, Object Lock) confirmed absent?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?
