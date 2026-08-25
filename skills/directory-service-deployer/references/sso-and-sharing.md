# SSO and Directory Sharing — Directory Service Deployer

Deep reference on SSO via IAM Identity Center (identity source
configuration, permission sets, user/group management) and cross-
account directory sharing (share-directory API, handshake flow,
accepter-side acceptance, constraints). Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## SSO via IAM Identity Center

### Connecting IAM Identity Center to a directory

IAM Identity Center (formerly AWS SSO) can use a Directory Service
directory as its identity source. This enables SSO for the AWS
Management Console and SAML 2.0 applications.

**Via AWS Console:**
1. Navigate to IAM Identity Center in the AWS Console.
2. Go to Settings > Identity source.
3. Select "AWS Directory Service" as the identity source type.
4. Select the directory from the dropdown.
5. Confirm — IAM Identity Center now authenticates users against
   the directory.

**Key constraint:** Only ONE directory can be connected per account
at a time. Switching to a different directory disconnects all
existing SSO users and permission sets.

### User and group management

- Users and groups are managed WITHIN the directory (using Active
  Directory tools, AWS Console directory management, or the DS API).
- Permission sets (AWS access policies) are assigned to users or
  groups in IAM Identity Center.
- Changes in the directory (new users, group membership changes)
  propagate to IAM Identity Center automatically (within a sync
  interval).

```bash
# Create a user in the directory
aws ds create-alias \
  --directory-id d-aaa111222 \
  --alias corp \
  --region us-east-1

# List users (via the directory)
aws ds describe-directory-data \
  --directory-id d-aaa111222 \
  --region us-east-1
```

### Permission sets

Permission sets define what AWS access a user or group gets. They
are managed in IAM Identity Center, not in the directory.

```bash
# Create a permission set
aws sso-admin create-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-xxx \
  --name "DeveloperAccess" \
  --description "Developer access to AWS accounts" \
  --session-duration "PT8H" \
  --region us-east-1

# Assign the permission set to a group
aws sso-admin create-instance-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-xxx \
  --target-type AWS_ACCOUNT \
  --target-id 123456789012 \
  --principal-type GROUP \
  --principal-id "Developers" \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-xxx/ps-xxx \
  --region us-east-1
```

### SSO troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| Users cannot log in | Directory not connected as identity source | Verify IAM Identity Center identity source is set to the correct directory |
| User changes not reflected | Sync delay (can be up to 15 minutes) | Wait for sync, or trigger a manual sync from IAM Identity Center |
| Permission set not working | Permission set not assigned to the user/group | Check assignment in IAM Identity Center |
| Cannot switch directories | Only one directory per account | Disconnect current directory first, then connect the new one |

## Cross-account directory sharing

### Share flow

Directory sharing allows other AWS accounts to access a Managed
Microsoft AD directory managed in your account. This enables
centralized directory management without replicating directories.

```text
Directory sharing flow:
  1. Owner account shares the directory (share-directory)
     → Shared directory status: Pending
  2. Target account accepts (accept-shared-directory)
     → Shared directory status: Shared
  3. Target account can now use the directory for EC2 domain join,
     SSO, and application authentication
  4. Owner can unshare at any time (unshare-directory)
     → All target-account resources referencing the directory break
```

### Sharing commands

```bash
# Owner shares the directory
aws ds share-directory \
  --directory-id d-aaa111222 \
  --share-target Id=999999999999,Type=ACCOUNT \
  --share-method HANDSHAKE \
  --region us-east-1

# Target account accepts
aws ds accept-shared-directory \
  --shared-directory-id d-xxx \
  --region us-east-1

# Verify from the owner account
aws ds describe-shared-directories \
  --owner-directory-id d-aaa111222 \
  --region us-east-1

# Verify from the target account
aws ds describe-directories \
  --region us-east-1 --output table
# The shared directory appears as type "SharedMicrosoftAD"
```

### Sharing constraints

- Only Managed Microsoft AD directories can be shared.
- The shared directory is available for read-only directory
  configuration in the target account; users can be managed in the
  shared directory.
- The target account can use the shared directory for:
  - EC2 seamless domain join
  - IAM Identity Center SSO
  - Application authentication
- Unsharing breaks all target-account resources that reference the
  directory (EC2 instances, SSO connections, applications).

### Directory sharing with AWS Organizations

For organizations with many accounts, directory sharing can be
simplified using AWS Organizations integration:

```bash
# Share with all accounts in an OU
aws ds share-directory \
  --directory-id d-aaa111222 \
  --share-target Id=ou-xxx-xxxxxxxx,Type=ORGANIZATIONAL_UNIT \
  --share-method HANDSHAKE \
  --region us-east-1
```

This shares the directory with all accounts in the specified OU.
Each account still needs to accept the shared directory.

### Common sharing pitfalls

1. **Forgetting the acceptance step.** The target account must call
   `accept-shared-directory`. The directory is not available until
   accepted.

2. **Unsharing without warning.** Unsharing immediately breaks all
   target-account resources. Coordinate with the target account
   before unsharing.

3. **Trying to share Simple AD or AD Connector.** Only Managed
   Microsoft AD can be shared. Simple AD and AD Connector do not
   support sharing.

4. **Region mismatch.** The shared directory is only available in
   the region where it was created. The target account must use the
   same region.

## Terraform examples

```hcl
# Share directory with another account
resource "aws_directory_service_shared_directory" "shared" {
  directory_id      = aws_directory_service_directory.managed_ad.id
  share_method      = "HANDSHAKE"
  share_notes       = "Shared with dev account"

  target {
    id   = "999999999999"
    type = "ACCOUNT"
  }
}

# IAM Identity Center permission set
resource "aws_ssoadmin_permission_set" "developer" {
  instance_arn     = aws_ssoadmin_instance.main.arn
  name             = "DeveloperAccess"
  description      = "Developer access"
  session_duration = "PT8H"
}

# Inline policy for the permission set
resource "aws_ssoadmin_managed_policy_attachment" "developer_readonly" {
  instance_arn       = aws_ssoadmin_instance.main.arn
  permission_set_arn = aws_ssoadmin_permission_set.developer.arn
  managed_policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
```

---

## Step 8 — Cross-account directory sharing commands (moved from SKILL.md)

```bash
# Share the directory with another account
aws ds share-directory \
  --directory-id d-aaa111222 \
  --share-target Id=999999999999,Type=ACCOUNT \
  --share-method HANDSHAKE \
  --region us-east-1

# Target account accepts
aws ds accept-shared-directory \
  --shared-directory-id d-xxx \
  --region us-east-1

# Verify
aws ds describe-shared-directories \
  --owner-directory-id d-aaa111222 \
  --region us-east-1
```
