# Org-mode Inspector enablement and delegated admin guide

This reference documents the org-mode enablement model for Amazon
Inspector v2 — when to use it, the one-way door semantics, and how
`autoEnable` interacts with existing members.

## Org-mode vs standalone

**Standalone:** the account is not in an Organization (or
Inspector org-mode is not configured). Enable Inspector per region
per resource type via `aws inspector2 enable --account-ids <self>`.

**Org-mode:** the Organization has a delegated admin account for
Inspector. Member accounts are managed centrally. The delegated
admin performs enable/disable on behalf of members and sets
`autoEnable` defaults for new members.

## One-way door: delegated admin enablement

Once `enable-delegated-admin-account` succeeds:

- The target account becomes the Inspector delegated admin for the
  org.
- Member accounts can no longer self-enable / self-disable.
- Disassociation requires `disable-delegated-admin-account` from the
  Organizations management account.

## autoEnable semantics

`update-organization-configuration --auto-enable` sets the default
state for NEW member accounts that join the org AFTER the call.
Existing members retain their pre-call state — even if
`autoEnable.ec2: true`, an existing member with EC2 disabled does
NOT flip to enabled.

To remediate existing members:

```bash
# From the delegated admin
aws inspector2 enable \
  --account-ids 333333333333 444444444444 \
  --resource-types EC2 ECR LAMBDA
```

## Delegated admin prerequisites

1. Caller is the Organizations management account.
2. No existing delegated admin (or replacing explicitly).
3. Target account is in the same Organizations root.
4. Target account accepts the
   `AWSServiceRoleForAmazonInspector2AdminRole` service-linked role.

## Member association

From the delegated admin:

```bash
aws inspector2 associate-member --account-id 333333333333
```

- Member must already be in the org.
- After association, `list-members` returns `relationshipStatus:
  ENABLED`.
- Member accounts are non-idempotent: re-associating an ENABLED
  member returns `ConflictException`.

## Member cap

The default org-wide member limit is 1000 member accounts. When
`maxAccountLimitReached: true`, additional associations are
BLOCKED. Disassociate unused members to free capacity.

## Cross-region coverage

Inspector coverage is reported per region. A member account enabled
in `us-east-1` is NOT automatically enabled in `us-west-2`. The
delegated admin enables per region explicitly:

```bash
for region in us-east-1 us-west-2 eu-west-1; do
  aws inspector2 enable \
    --account-ids 333333333333 \
    --resource-types EC2 ECR LAMBDA \
    --region $region
done
```

## Disassociation and revoke

```bash
# From the delegated admin
aws inspector2 disassociate-member --account-id 333333333333

# From the Organizations management account — full revoke
aws inspector2 disable-delegated-admin-account \
  --delegated-admin-account-id 222222222222
```

Disassociation moves the member to `relationshipStatus: DISABLED`
but does NOT disable Inspector for already-scanned resources. Full
disable requires explicit `disable` from the delegated admin.
