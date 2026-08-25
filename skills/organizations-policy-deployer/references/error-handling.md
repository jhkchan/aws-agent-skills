# Error Handling — Organizations Policy Deployer

Deployment failure deep dives. Loaded on demand by the skill.

## Error handling

### Account locked out after FullAWSAccess detach

- An Allow-list SCP was not attached BEFORE detaching
  `FullAWSAccess`, OR the Allow-list did not include break-glass
  actions. Recover from the management account: re-attach
  `FullAWSAccess` (or attach the Allow-list), then retry.

### AttachPolicy fails with quota error

- The target already has 5 SCPs attached (inclusive of
  `FullAWSAccess`). Detach an unused SCP or request a quota
  increase via Support. The limit is per-entity.

### SCP attached but no effect

- Either (a) the SCP is `DISABLED` (enable with `update-policy`),
  (b) for an Allow-list strategy `FullAWSAccess` is still
  attached at the same entity (detach it), or (c) the action is
  not permitted by IAM in the member account (SCPs only filter).

### simulate-custom-policy shows Allowed but the call is blocked

- `simulate-custom-policy` simulates IAM, NOT Organizations. The
  actual SCP effect is invisible to it. Verify via
  `list-policies-for-target` along the hierarchy and a post-
  attach CloudTrail observation.

### Tag policy not blocking non-compliant tags

- The `enforced_for` list does not include the resource type.
  Add the resource type (e.g., `ec2:instance`) and re-attach.
  Without `enforced_for`, tag policies are audit-only.

