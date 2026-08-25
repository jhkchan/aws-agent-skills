# Advanced Patterns — Tag Compliance Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

**One-line takeaway:** tag compliance is a four-layer pipeline —
**define** (Organizations TagPolicy with `enforced_for` and case-sensitive
key/value rules) → **detect** (Config `required-tags` and
`allowed-tag-values` rules flag non-compliant resources; Config CI changes
catch tag drift) → **propagate** (EventBridge + Lambda auto-tags new
resources and propagates inherited tags from EC2 to EBS volumes and ENIs)
→ **remediate** (SSM Automation adds or corrects missing tags; Config
re-evaluates and flips COMPLIANT). A gap in ANY layer produces a silent
failure: the policy is published but advisory, auto-tagging stamps tags
that humans later overwrite, drift goes undetected, or cost allocation
reports stay empty because no one activated the tag keys in Billing.

- **Organizations TagPolicy** without `enforced_for` is advisory only.
  AWS does not block non-compliant tag operations. The policy is
  documentation, not enforcement.
- **Case sensitivity** is a silent gap. A TagPolicy with
  `case_sensitive: true` treats `Environment` and `environment` as
  different keys. Config `required-tags` checks the exact key name in
  InputParameters. Auto-taggers must normalize casing before stamping.
- **EC2 tags do NOT propagate to EBS volumes or ENIs.** The `RunInstances`
  API tags only the instance. An EventBridge Lambda must call
  `ec2:create-tags` on child resources.
- **Cost allocation tags are NOT active by default.** A perfectly tagged
  fleet produces zero cost-dimension data until an administrator activates
  the tag keys via the Billing API or console.

## Step 0: Expert knowledge — non-obvious TagPolicy and Config behaviors

- **A TagPolicy attached to the org root cascades to all OUs and
  accounts, but a policy attached to a specific OU OVERRIDES (not
  merges) the root policy.** The effective tag policy is the policy
  attached to the closest ancestor. To add a key at the OU level
  without losing root keys, re-declare every parent key in the child.

- **`enforced_for` accepts resource types in `AWS::service::resource`
  format.** A typo like `AWS::EC2::instance` (lowercase) is silently
  ignored. Cross-reference the canonical resource-type list.

- **Config `required-tags` uses `InputParameters` as a JSON-encoded
  string.** Passing a map where the API expects
  `"{\"tag1Key\":\"Environment\"}"` silently drops the input.

- **The Resource Groups Tagging API is eventually consistent.** Tagging
  returns `SUCCESS` immediately but a follow-up `get-resources` within
  seconds may not reflect new tags. Sleep 10-15 seconds before re-querying.

- **EventBridge auto-taggers that derive Owner from the IAM principal
  must handle assumed-role sessions.** The `userIdentity.sessionContext`
  has `sessionIssuer.arn` (the role). Deriving a human owner from a role
  ARN requires a mapping table.

- **`allowed-tag-values` is a Config managed rule that accepts ONE tag
  key per invocation.** For 4 tag keys' value validation, deploy 4
  separate rules.

- **The `ce update-cost-allocation-tags-status` API has a propagation
  delay of up to 24 hours.** Do not re-activate or assume failure within
  that window. Poll the `ProcessingStatus` field.

- **Config configuration-item change events fire only for recorded
  resource types.** Tag drift on an unrecorded type is invisible.
  Extend the recorder scope before wiring drift detection.

## Configuration dependency graph

```
[Organizations: enable TAG_POLICY]
        |
        v
[Organizations: create + attach TagPolicy to root]
        |
        +-----------------------------+
        |                             |
        v                             v
[Config: recorder scope covers target types]   [IAM: auto-tagger Lambda role]
        |                             |
        v                             v
[Config: put required-tags + allowed-tag-values rules]   [EventBridge: put-rule + Lambda + DLQ]
        |                             |
        v                             v
[Config: put-remediation-configurations (manual)]   [SSM: create-document Custom-AddRequiredTag]
        |
        v
[Cost Explorer: update-cost-allocation-tags-status (payer)]
        |
        v
[CloudFormation: create-stack-set (OU-wide)]
```

**Hard ordering constraints:**

1. TAG_POLICY type MUST be enabled before `create-policy`.
2. Config recorder scope MUST include target types before rules deploy.
3. Auto-tagger Lambda role MUST exist before EventBridge target attaches.
4. SSM document MUST exist before `put-remediation-configurations`.
5. Cost allocation activation runs independently on the payer account.

## Recent AWS features (2024-2026)

- **TagPolicy `enforced_for` resource-type expansion:** Additional
  types including Lambda layers, Step Functions state machines. Re-check
  the supported-types list quarterly.
- **Cost Explorer API `ProcessingStatus`:** The 24-hour propagation
  delay is now visible in the API response. Poll instead of guessing.
- **CloudFormation StackSets drift detection:** Per-account drift on
  deployed Config rules via `detect-stack-set-drift`.
- **Resource Groups Tagging API pagination:** Longer TTL on
  `PaginationToken`, reducing bulk-enumeration restarts.

## Expert heuristic: tag-policy case sensitivity + EventBridge auto-tagger + Config detection

The most common tag-compliance failure is NOT a missing policy — it is a
policy that looks correct but silently does not enforce, because of
case-sensitivity mismatches and missing propagation to child resources.

**The rule (non-negotiable):**

> ALWAYS declare `case_sensitive` explicitly in the TagPolicy, ALWAYS
> normalize tag-key casing in the EventBridge auto-tagger Lambda before
> calling `create-tags`, and ALWAYS propagate tags from EC2 instances to
> their child EBS volumes and ENIs in the same Lambda handler. A policy
> that declares `Environment` but an auto-tagger that stamps
> `environment` produces a fleet that is TagPolicy-compliant but
> Config-NON_COMPLIANT.

**Case-sensitivity matrix:**

| System | Default case sensitivity | Override |
|---|---|---|
| Organizations TagPolicy | `case_sensitive: true` | `CaseSensitive: false` per key |
| Config `required-tags` | Exact match on InputParameters key | No override |
| Config `allowed-tag-values` | Exact match on key and value | No override |
| Cost Explorer (user-defined) | Case-insensitive on key, case-sensitive on value | No override |
| Resource Groups Tagging API | Case-sensitive on key | No override |

**EC2-to-child propagation diagnostic:** if Cost Explorer shows instance
costs tagged but EBS volume costs untagged, the auto-tagger is not
propagating. Verify the Lambda reads `BlockDeviceMappings[].Ebs.VolumeId`
and `NetworkInterfaces[].NetworkInterfaceId`, calls `ec2:create-tags`
in batch, and has `ec2:CreateTags` on `volume/*` and
`network-interface/*`.

**Surface in the output:** include `CASE_SENSITIVITY`, `CASE_NORMALIZATION`,
`PROPAGATION_COVERAGE`, and `VALIDATION_STATUS`. If
`VALIDATION_STATUS` is advisory or `PROPAGATION_COVERAGE` is incomplete,
do NOT mark the recommendation as AUTOMATION_DEPLOYED.
