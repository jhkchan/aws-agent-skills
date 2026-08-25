# Diagnostic Commands — S3 Public-Access Auditor

Audit enumeration and verification commands moved from SKILL.md. Load on demand.

## Access Points and MRAP: audit steps and CLI

Audit steps (when Access Point info is in the input):

1. Enumerate APs: `aws s3control list-access-points --account-id <acct>`
   (one per region; iterate regions).
2. For each AP, fetch its policy:
   `aws s3control get-access-point-policy --account-id <acct> --name <ap>`
3. Apply Rules 2 and 4 against the AP policy (in addition to the bucket
   policy). Resource matching for AP policies uses the AP ARN, not the
   bucket ARN — be permissive about Resource matching since AP policies
   commonly use `arn:aws:s3:::accesspoint/<name>/*` shorthand.
4. If ANY AP policy exposes the bucket, the verdict is **PUBLIC** with
   reason "Rule 2 (Access Point) — wildcard Allow on AP `<name>`; the
   bucket policy is bypassed for requests through the AP ARN".
5. If an AP policy uses `s3:DataAccess` or `s3:ExternalService` (bucket
  -managed permissions via S3 Access Grants), note it but do not classify
   as public — those are managed internally.

**MRAP-specific note:** an MRAP policy can route requests to ANY region's
bucket copy. A permissive MRAP policy exposes all underlying buckets in
all regions. Audit via `aws s3control get-multi-region-access-point-policy
--account-id <acct> --name <mrap>`.

## Procedural enumeration (large-account bulk audit)

1. **List all buckets (paginated):**
   ```bash
   # AWS CLI v2 auto-paginates; for very large accounts use --page-size
   aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n'
   ```
   For >10,000 buckets, set `--page-size 1000` and consider scripting with
   `boto3.Paginator` to avoid CLI truncation.

2. **Capture the account-level BPA ONCE** (it applies to all buckets):
   ```bash
   aws s3control get-public-access-block --account-id <acct>
   ```

3. **Per bucket, capture the 5 needed inputs in parallel:**
   ```bash
   for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n'); do
     aws s3api get-bucket-location              --bucket "$b" 2>/dev/null
     aws s3api get-public-access-block          --bucket "$b" 2>/dev/null
     aws s3api get-bucket-acl                   --bucket "$b" 2>/dev/null
     aws s3api get-bucket-policy                --bucket "$b" 2>/dev/null
     aws s3api get-bucket-ownership-controls    --bucket "$b" 2>/dev/null
   done > "/tmp/s3-audit-$(date +%s).jsonl"
   ```
   Wrap each in `2>/dev/null` and check exit codes — `NoSuchBucket`,
   `NoSuchPublicAccessBlockConfiguration`, and `AccessDenied` are common
   and should be classified as "data incomplete — manual review" rather
   than silently treated as SAFE.

4. **For Access-Point-aware audits,** enumerate APs per region:
   ```bash
   for r in us-east-1 us-west-2 eu-west-1 ap-southeast-2; do
     aws s3control list-access-points --profile default --region "$r" --account-id <acct>
   done
   ```
   Note: AP listing is region-scoped — a bucket in `us-east-1` may have
   APs in OTHER regions routing to it; iterate all enabled regions.

5. **Output one verdict per bucket** in the standard format below, and a
   summary table sorted by severity (CRITICAL → HIGH → AMBIGUOUS → SAFE).

