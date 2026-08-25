# ECR Push/Pull Troubleshooter — diagnostic commands (moved from SKILL.md

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Account-wide pre-flight commands (moved from SKILL.md)

```bash
# 1. Registry settings (encryption, public alias, replication source)
aws ecr describe-registry --output json

# 2. Auth token (decode base64 to read username:password; valid for 12h)
aws ecr get-authorization-token --output json | \
  jq '.authorizationData[0] | {proxyEndpoint, expiresAt, token: (.authorizationToken | @base64d)}'

# 3. Repository configuration (imageTagMutability, scan-on-push, encryption)
aws ecr describe-repositories --repository-names <repo> --output json

# 4. Repository resource-based policy (cross-account grants live here)
aws ecr get-repository-policy --repository-name <repo> --output json 2>/dev/null || \
  echo "No repository policy (default deny for cross-account)"

# 5. Lifecycle policy (rule order matters — first match wins)
aws ecr get-lifecycle-policy --repository-name <repo> --output json 2>/dev/null || \
  echo "No lifecycle policy"

# 6. AWS Health (regional ECR events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

## Repository-state short-circuit (moved from SKILL.md)

| `describe-repositories` field | Effect on diagnosis |
|---|---|
| `imageTagMutability: IMMUTABLE` | A push with an existing tag fails with `image tag already exists` — route to TAG_IMMUTABILITY before any policy work. |
| `imageScanningConfiguration.scanOnPush: true` | Every push triggers a scan; downstream gates may block deploy on `HIGH`/`CRITICAL`. Route to SCAN_BLOCKING when the error is from the deploy pipeline. |
| `encryptionConfiguration.encryptionType: KMS` | Pushes need `kms:GenerateDataAccess`; pulls need `kms:Decrypt`. Route to KMS on any KMS.AccessDeniedException. |
| `encryptionConfiguration.encryptionType: AES256` | No caller-side KMS permission needed — do NOT chase KMS for AES256 repos. |
| Empty repository policy | Cross-account pulls fail with `denied`; same-account pulls succeed via IAM. Route to POLICY_REPOSITORY for cross-account. |

## Step 2: AUTH_TOKEN_EXPIRED probes (moved from SKILL.md)

```bash
# Verify the token's expiry (the token is base64(AWS:<signed-url>))
aws ecr get-authorization-token --output json | \
  jq '.authorizationData[0] | {proxyEndpoint, expiresAt, decoded: (.authorizationToken | @base64d)}'

# Check what docker has cached
cat ~/.docker/config.json | jq '.auths'
```

## Step 3: AUTH_IAM_DENIED probe (moved from SKILL.md)

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names ecr:GetAuthorizationToken \
  --output json --profile <p>
```

## Step 4: POLICY_IAM probe (moved from SKILL.md)

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names ecr:BatchCheckLayerAvailability ecr:BatchGetImage \
                ecr:GetDownloadUrlForLayer ecr:PutImage \
                ecr:InitiateLayerUpload ecr:UploadLayerPart \
                ecr:CompleteLayerUpload \
  --resource-arns arn:aws:ecr:<region>:<account>:repository/<repo> \
  --output json --profile <p>
```

## Step 5: POLICY_REPOSITORY probe (moved from SKILL.md)

```bash
aws ecr get-repository-policy --repository-name <repo> \
  --region <region> --output json --profile <p>
```

## Step 5: POLICY_REPOSITORY fix — set-repository-policy cross-account (moved from SKILL.md)

```bash
aws ecr set-repository-policy --repository-name <repo> --region <region> \
  --policy-text '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "CrossAccountPull",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<caller-account>:root"},
      "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
                 "ecr:BatchCheckLayerAvailability"]
    }]
  }' --profile <p>
```

## Step 6: LIFECYCLE_DELETED probes (moved from SKILL.md)

```bash
aws ecr get-lifecycle-policy --repository-name <repo> --output json --profile <p>
aws ecr describe-images --repository-name <repo> --output json --profile <p> | \
  jq '.imageDetails[] | {imageTags, imagePushedAt, imageSizeInBytes}'

# CloudTrail shows the ECR service principal deleting images
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=BatchDeleteImage \
  --start-time $(date -d '-24 hours' +%s) --end-time $(date +%s) \
  --output json | jq '.Events[] | select(.CloudTrailEvent | contains("<repo>"))'
```

## Step 8: REPLICATION_LAG probes (moved from SKILL.md)

```bash
aws ecr describe-registry --output json --profile <p>
aws ecr get-replication-configuration --region <source-region> --output json --profile <p>
aws ecr describe-images --repository-name <repo> --region <dest-region> --output json --profile <p>
```

## Step 9: KMS_ACCESS_DENIED probes (moved from SKILL.md)

```bash
aws ecr describe-repositories --repository-names <repo> --output json | \
  jq '.repositories[0].encryptionConfiguration'
aws kms describe-key --key-id <kms-key-id> --output json | \
  jq '.KeyMetadata.{KeyState, KeyManager, Origin}'
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names kms:GenerateDataAccess kms:Decrypt \
  --resource-arns arn:aws:kms:<region>:<account>:key/<key-id> \
  --output json --profile <p>
```

## Step 10: REGISTRY_ALIAS_MISMATCH probe (moved from SKILL.md)

```bash
# Identify which registry the URI points at:
# - public.ecr.aws/<alias>/<repo>             -> ECR Public
# - <account>.dkr.ecr.<region>.amazonaws.com  -> ECR Private
aws ecr-public describe-registries --output json --profile <p> | \
  jq '.registries[] | {registryId, aliases: [.aliases[] | .name]}'
```

## Step 11: SCAN_BLOCKING probe (moved from SKILL.md)

```bash
aws ecr describe-image-scan-findings \
  --repository-name <repo> --image-id imageTag=<tag> \
  --output json --profile <p> | \
  jq '.imageScanFindings.findings[] | select(.severity == "HIGH" or .severity == "CRITICAL")'
```

## Step 12: TAG_IMMUTABILITY probe (moved from SKILL.md)

```bash
aws ecr describe-repositories --repository-names <repo> --output json | \
  jq '.repositories[0].imageTagMutability'
```

## Step 12: TAG_IMMUTABILITY fix — put-image-tag-mutability (moved from SKILL.md)

```bash
aws ecr put-image-tag-mutability --repository-name <repo> \
  --image-tag-mutability MUTABLE --profile <p>
```

## Step 13: MANIFEST_INVALID / ARCHITECTURE_MISMATCH probes (moved from SKILL.md)

```bash
# Inspect the manifest (multi-arch manifests return a list)
docker manifest inspect <registry-uri>/<repo>:<tag> 2>/dev/null || \
  aws ecr batch-get-image --repository-name <repo> \
    --image-ids imageTag=<tag> --output json --profile <p> | \
  jq '.images[0].imageManifest' | head -50

# Fargate platform / Lambda architecture determine host platform
aws ecs describe-tasks --cluster <cluster> --tasks <task-id> --output json | \
  jq '.tasks[0] | {platformVersion}'
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.Architectures'
```

## Step 13: manifest/architecture pattern table (moved from SKILL.md)

| Pattern | Cause |
|---|---|
| `no matching manifest for platform linux/amd64 in the manifest list` | The tag points to a single-arch arm64 image; the host is x86_64 (or vice-versa). Build a multi-arch manifest with `docker buildx`. |
| Fargate task fails after pull with `Exec format error` | Image is single-arch and was force-pulled onto an incompatible host (rare — Fargate matches on manifest). |
| Lambda `ImagePullException: Image architecture arm64 incompatible` | Lambda with `Architectures: [x86_64]` cannot run an arm64-only image. Set `Architectures: [arm64]` OR rebuild for x86_64. |

## Step 14: PULL_THROUGH_CACHE probe (moved from SKILL.md)

```bash
aws ecr describe-pull-through-cache-rules --region <region> --output json --profile <p>
```

## Step 14: pull-through-cache pattern table (moved from SKILL.md)

| Pattern | Cause |
|---|---|
| `upstream registry does not exist` | Upstream URI is wrong, or upstream is unreachable from the region (network/egress). |
| Pull loops / never caches | Local cached repository name does not match the rule's prefix; `ecrRepositoryPrefix` misconfigured. |
| `KMS.AccessDeniedException` on pull-through | Cache writes to a KMS-encrypted repo; caller lacks `kms:Decrypt` on the local key. |
| Pull from a credentialled upstream fails | Upstream secret (Secrets Manager) is missing or stale; rule cannot authenticate to the upstream. |

## Step 15: LAYER_DOWNLOAD_FAILED probe (moved from SKILL.md)

```bash
aws ecr batch-check-layer-availability \
  --repository-name <repo> \
  --layer-digests sha256:<digest-1> sha256:<digest-2> \
  --output json --profile <p>
```
