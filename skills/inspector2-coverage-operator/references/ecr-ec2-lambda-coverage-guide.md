# EC2, ECR, and Lambda coverage diagnostic guide

This reference covers the per-resource-type scan mechanics, the
common coverage gaps, and the diagnostic flow for each resource
type in Amazon Inspector v2.

## EC2 coverage

### Scan types

- **Standard scan (network reachability):** analyzes the Security
  Group, route table, and internet exposure of the instance. No
  agent required.
- **Standard host-agent scan:** runs the Inspector agent via SSM to
  collect OS-level CVE inventory.
- **Deep inspection:** adds package-level inventory via the SSM
  association `AmazonInspector-ManageAWSAgent`.

### Required prerequisites

1. SSM agent installed (Amazon Linux 2/2023, Ubuntu, Windows
   Server, macOS have it pre-installed on recent AMIs).
2. IAM instance profile with `AmazonSSMManagedInstanceCore`.
3. VPC endpoints OR NAT gateway OR public IP for SSM communication.
4. `PingStatus: Online` from `ssm describe-instance-information`.
5. For deep inspection: SSM association
   `AmazonInspector-ManageAWSAgent` in `Associated: true` state.

### Common coverage gaps

| Symptom | Root cause | Fix |
|---|---|---|
| `AGENT_NOT_INSTALLED` | SSM agent missing on the AMI | Install the agent and reboot |
| `AGENT_OFFLINE` | `PingStatus: ConnectionLost` | Reboot the agent or instance |
| `DEEP_INSPECTION_NOT_ACTIVE` | SSM association missing | Create `AmazonInspector-ManageAWSAgent` association |
| `UNSUPPORTED_OS` | OS not in Inspector's supported list | Check release notes or upgrade the OS |
| Instance never appears | Wrong region | Verify enable state in the correct region |

## ECR coverage

### Scan types

- **Basic:** uses the native ECR CVE list (open-source Clair
  successor). Faster, less comprehensive.
- **Enhanced (`ecr-enhanced`):** pulls the Inspector agent for
  deep package inventory. More comprehensive, slower.

### Configuration

- `scanOnPush: true` on the repository: every pushed image is
  scanned automatically.
- `scanOnPush: false`: manual `start-image-scan` per image.
- Enhanced scan must be enabled at the registry/region level.

### Common coverage gaps

| Symptom | Root cause | Fix |
|---|---|---|
| No scans on new images | `scanOnPush: false` | `put-image-scanning-configuration --image-scanning-configuration scanOnPush=true` |
| `imageScanStatus: FAILED` | Image manifest too large or malformed | Reduce image layers or fix manifest |
| Enhanced scan unavailable | Region unsupported | Move repository or fall back to `basic` |
| Concurrent scans serial | Per-repo rate limit | Use `scanOnPush: true` for high-volume registries |

## Lambda coverage

### Scan types

- **LAMBDA_FUNCTION:** scans the function configuration and
  package manifest.
- **LAMBDA_CODE:** enabled alongside LAMBDA resource type; scans
  function code and dependencies for known CVEs.

### Supported runtimes (2026)

- `python3.x` (3.9, 3.10, 3.11, 3.12)
- `nodejs.x` (18.x, 20.x, 22.x)
- `java11`, `java17`, `java21`
- `provided.al2023` (with custom layers)

**Unsupported runtimes** (`dotnet`, `ruby`, `go` on `provided.al2`)
are silently skipped — they do NOT appear in `list-coverage`. Track
as a known gap.

### Layer permissions

Inspector requires `lambda:GetLayerVersion` on each layer used by
the function. Without it, the layer is not scanned.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "inspector2.amazonaws.com"
      },
      "Action": "lambda:GetLayerVersion",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:layer:my-layer:*"
    }
  ]
}
```

### Versioning semantics

- `$LATEST` is scanned.
- Published versions are scanned once (on publish).
- Aliases (`prod`, `staging`) are NOT scanned independently —
  coverage follows the version they point to.

For continuous coverage, keep `$LATEST` as the deployment target
and re-publish versions on every change.

### Common coverage gaps

| Symptom | Root cause | Fix |
|---|---|---|
| Function absent from `list-coverage` | Unsupported runtime | Switch runtime or accept as gap |
| Layer not scanned | Layer policy missing Inspector principal | Add `lambda:GetLayerVersion` grant |
| Published version not rescanned | Versions scan once | Republish on code change |
| Code scan status `PENDING` long | Queue backpressure | Wait 5-30 min; if persists, contact support |

## Cross-resource coverage audit

```bash
# Coverage by resource type per region
aws inspector2 list-coverage --region us-east-1 --output table

# Coverage gap summary
aws inspector2 list-coverage \
  --filter-criteria 'SCAN_STATUS=_NOT_EQUALS=COMPLETED' \
  --region us-east-1 \
  --output table

# Per-account status
aws inspector2 batch-get-account-status \
  --account-ids 111111111111 222222222222 \
  --region us-east-1
```

For org-wide coverage aggregation across regions, integrate with
AWS Security Hub — Inspector findings auto-publish.
