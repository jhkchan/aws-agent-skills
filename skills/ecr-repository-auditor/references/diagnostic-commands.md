# Diagnostic Commands (load on demand) — ECR Repository Auditor

Pre-flight command listings, sweep pagination, and remediation CLI sequences moved verbatim from SKILL.md. Loaded on demand.

---

## Multi-repo / account-wide sweep note (pagination) (moved from SKILL.md)

**Multi-repo / account-wide sweep note (pagination):** when auditing every
repo in an account, `aws ecr describe-repositories` returns at most 100 per
page via `--max-results`. Use `--next-token` to page through all repositories;
iterating only the first page silently skips repos in other lifecycle stages.
For each repo, also page `aws ecr describe-images --repository-name <name>`
(caps at 100/page) and `aws ecr get-lifecycle-policy-preview` — both silently
truncate. Always drain `nextToken` to completion.

## Live-account pre-flight checks (moved from SKILL.md)

1. Verify the caller's identity can run `ecr:PutImageScanningConfiguration` and
   `ecr:PutLifecyclePolicy` if remediation is intended — most read-only auditor
   roles CANNOT, and remediation commands will fail with `AccessDenied`.
   Surface this BEFORE the operator approves the change.
2. Verify CloudTrail is logging ECR data events (`DeleteImage`, `PutImage`) —
   ECR management events (`CreateRepository`, `DeleteRepository`) are on by
   default, but `PutImage`/`BatchDeleteImage` are data events that must be
   explicitly enabled on the trail. Without them, image-tampering forensics
   have no signal.
3. Snapshot `aws ecr describe-images --repository-name <name>` BEFORE any policy
   edit — image digests and tags are not versioned. A PutImage overwrites a tag
   with no history. Compare pre/post to detect tag mutations during the
   remediation window.

## Remediation guidance (moved from SKILL.md)

### For PUBLIC — wildcard/cross-account pull or push (Step 1a-1d)

1. **Immediately** remove the wildcard or cross-account principal from the
   repositoryPolicy, or add a strong condition (`aws:SourceVpce`,
   `aws:SourceAccount`, `aws:SourceArn`) to scope the grant.
   ```bash
   # Back up the current policy
   aws ecr get-repository-policy --repository-name <name> --registry-id <id> \
     --output json > /tmp/<name>-policy-backup.json

   # Apply the tightened policy (provide the new policy document)
   aws ecr set-repository-policy --repository-name <name> --registry-id <id> \
     --policy-text file://new-policy.json
   ```
2. **Assume breach.** Audit CloudTrail for `ecr:BatchGetImage` and
   `ecr:GetDownloadUrlForLayer` events from external principals during the
   exposure window. Any image they pulled should be considered inspected —
   rotate secrets found in image layers and rebuild images with a clean base.
3. If cross-account pull is **intentional** (e.g., a shared services account),
   replace `Principal: "*"` with the specific external role ARN and add
   `aws:SourceAccount` / `aws:SourceArn` conditions.

### For NO_SCAN — scanOnPush disabled or unscanned images (Step 2)

1. Enable scan-on-push:
   ```bash
   aws ecr put-image-scanning-configuration --repository-name <name> \
     --registry-id <id> --image-scanning-configuration scanOnPush=true
   ```
2. Manually scan existing unscanned images:
   ```bash
   for digest in $(aws ecr describe-images --repository-name <name> \
     --registry-id <id> --query 'imageDetails[?imageScanStatus==null].imageDigest' \
     --output text); do
     aws ecr start-image-scan --repository-name <name> --registry-id <id> \
       --image-id imageDigest=$digest
   done
   ```
3. For production repos, enable enhanced scanning (Amazon Inspector
   integration) for continuous re-scanning against the latest CVE database:
   ```bash
   aws ecr put-registry-scanning-configuration \
     --scanning-configuration scanType=ENHANCED,repositoryFilters=[{repositoryName=<name>}] \
     --profile <profile>
   ```
   Note: enhanced scanning is configured at the registry level, not per-repo.

### For NO_LIFECYCLE — no lifecycle policy (Step 3)

1. Create a lifecycle policy that retains the last N tagged images and deletes
   untagged images after 1 day:
   ```bash
   cat > /tmp/lifecycle.json << 'EOF'
   {
     "rules": [
       {
         "rulePriority": 1,
         "description": "Delete untagged images after 1 day",
         "selection": { "tagStatus": "untagged", "countType": "sinceImagePushed", "countUnit": "days", "countNumber": 1 },
         "action": { "type": "expire" }
       },
       {
         "rulePriority": 2,
         "description": "Keep last 10 tagged images",
         "selection": { "tagStatus": "any", "countType": "imageCountMoreThan", "countNumber": 10 },
         "action": { "type": "expire" }
       }
     ]
   }
   EOF
   ```
2. **Dry-run first** — verify which images would be deleted:
   ```bash
   aws ecr get-lifecycle-policy-preview --repository-name <name> --registry-id <id> \
     --policy-text file:///tmp/lifecycle.json --output json
   ```
3. Apply the policy:
   ```bash
   aws ecr put-lifecycle-policy --repository-name <name> --registry-id <id> \
     --lifecycle-policy-text file:///tmp/lifecycle.json
   ```

### For CONFIG_GAP — tag mutability (Step 4)

1. Set tag immutability:
   ```bash
   aws ecr put-image-tag-mutability --repository-name <name> \
     --registry-id <id> --image-tag-mutability IMMUTABLE
   ```
2. Verify:
   ```bash
   aws ecr describe-repositories --repository-names <name> --registry-id <id> \
     --query 'repositories[0].imageTagMutability' --output text
   ```

### For CONFIG_GAP — condition-restricted cross-account (Step 1e)

1. Validate the condition is still correct and the named VPC endpoint or
   account still exists.
2. Convert the Allow-based restriction to an explicit Deny (deny all except
   the trusted account/endpoint) — Deny statements cannot be accidentally
   widened by adding a new Allow.
3. For `aws:SourceVpce`, verify the VPC endpoint is still in use and has not
   been deleted (a deleted endpoint ID makes the condition unmatchable,
   silently blocking all access).

### For OK

1. No remediation required for the current posture.
2. Recommend enabling enhanced scanning if not already on (defense-in-depth
   for production repos).
3. Recommend adding a Deny statement for `aws:SecureTransport: false` to
   enforce TLS for all ECR API calls (defense-in-depth).
4. For repos with cross-region replication, verify replicas are also audited
   — they inherit the source repositoryPolicy.
