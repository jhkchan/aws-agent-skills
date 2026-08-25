# RAM Resource Share Deployer — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

### Step 9: Verification and post-deployment checks (moved from SKILL.md)

```bash
# Verify the resource share
aws ram get-resource-shares \
  --resource-share-arns arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List principals in the share
aws ram list-principals \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List resources in the share
aws ram list-resources \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List permission associations
aws ram list-resource-share-permissions \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1
```

## Pre-flight safety checks (run before any provisioning CLI) (moved from SKILL.md)

- **Confirm Organizations all features enabled (for org/OU sharing):**
  ```bash
  aws organizations describe-organization --query 'Organization.FeatureSet' --output text
  aws organizations list-organizational-units-for-parent --parent-id r-root
  ```

- **Confirm the resource exists:**
  ```bash
  aws ram list-resources --resource-owner SELF
  aws ram list-resource-types
  ```

- **Confirm principal account IDs or ARNs are valid:**
  ```bash
  aws organizations list-accounts
  ```

- **Confirm available permissions for the resource type:**
  ```bash
  aws ram list-permissions --resource-type <type> --resource-owner SELF
  ```

