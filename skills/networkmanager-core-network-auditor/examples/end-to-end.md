# End-to-end usage scenario: networkmanager-core-network-auditor

A walkthrough showing the skill auditing a Cloud WAN core network that
has a permissive resource policy (PERMISSIVE_POLICY) and a CIDR overlap
(CIDR_OVERLAP), demonstrating severity aggregation, the
State-vs-Status distinction, and the ordered classification logic.

## Input (user prompt)

> Audit this Cloud WAN core network before we open it to the shared-
> services team. The prod VPC and non-prod VPC are both attached.

```text
Core network id: core-network-prod-shared
Core network ARN: arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-prod-shared
OwnerAccountId: 111111111111
State: AVAILABLE
Policy generation (LATEST): 5
Policy generation (LIVE): 5

Attachments:
  - AttachmentId: attachment-prod-vpc
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-east-1:111111111111:vpc/vpc-prod
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: ATTACHED
    EdgeLocation: us-east-1
    Segment: prod
    Cidrs: [10.0.0.0/16, 10.1.0.0/16]
  - AttachmentId: attachment-nonprod-vpc
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-west-2:111111111111:vpc/vpc-nonprod
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: ATTACHED
    EdgeLocation: us-west-2
    Segment: non-prod
    Cidrs: [10.0.1.0/24]
  - AttachmentId: attachment-shared-vpc
    ResourceType: vpc
    ResourceArn: arn:aws:ec2:us-east-1:222222222222:vpc/vpc-shared
    AttachmentType: VPC
    State: AVAILABLE
    AttachmentStatus: ATTACHED
    EdgeLocation: us-east-1
    Segment: shared-services
    Cidrs: [10.2.0.0/24]

Resource policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "networkmanager:*",
      "Resource": "arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-prod-shared"
    },
    {
      "Sid": "PartnerAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
      "Action": "networkmanager:*",
      "Resource": "arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-prod-shared"
    }
  ]
}

Core network policy (segment-actions):
  - segment: prod
    share-with: [prod, shared-services]
  - segment: non-prod
    share-with: [non-prod, shared-services]
  - segment: shared-services
    share-with: [prod, non-prod, shared-services]
```

## Skill output

```text
CORE_NETWORK: core-network-prod-shared
VERDICT: CIDR_OVERLAP
REASON: attachment-prod-vpc CIDR 10.0.0.0/16 overlaps with
attachment-nonprod-vpc CIDR 10.0.1.0/24 across the prod and non-prod
segments — traffic to addresses in the overlap range may route to
either VPC (Step 2). Additionally, the resource policy grants
networkmanager:* to a cross-account principal (222222222222) with no
restrictive condition (Step 3).
FINDINGS:
  - [CIDR_OVERLAP] attachment-prod-vpc CIDR 10.0.0.0/16 overlaps with
    attachment-nonprod-vpc CIDR 10.0.1.0/24 (the /24 is inside the /16)
    across prod/non-prod segments — silent routing ambiguity (Step 2)
  - [PERMISSIVE_POLICY] Resource policy statement "PartnerAccess" grants
    networkmanager:* to cross-account principal 222222222222 with no
    condition — external account can create/modify attachments and
    inject routes (Step 3)
  - [OK] All three attachments are ATTACHED with State AVAILABLE (Step 1)
  - [OK] LATEST policy generation (5) equals LIVE (5) (Step 5)
REMEDIATION:
  1. CIDR_OVERLAP — Re-IP the non-prod VPC to a disjoint range (e.g.,
     10.99.0.0/24) or restrict attachment-nonprod-vpc's advertised
     subnets to exclude the overlap. Cloud WAN does not validate
     overlaps at creation — enforce disjoint CIDR ranges manually.
  2. PERMISSIVE_POLICY — Replace the cross-account root principal in
     "PartnerAccess" with the specific role ARN the shared-services
     team uses (e.g., arn:aws:iam::222222222222:role/shared-svc-core)
     and add aws:SourceAccount: "222222222222" as a condition. Back
     up the current policy first:
     aws networkmanager get-resource-policy \
       --resource-arn arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-prod-shared \
       --output json > /tmp/resource-policy-backup.json
```

## What the skill caught that a generic assistant misses

1. **The CIDR overlap is silent.** A generic assistant might notice the
   overlap but not explain that Cloud WAN accepts it without error —
   there is no creation-time validation. The skill identifies the exact
   overlap (10.0.1.0/24 is inside 10.0.0.0/16) and explains that
   traffic to addresses in the overlap range may route to either VPC
   depending on route-table evaluation order.

2. **The cross-account root principal is flagged correctly.** A naive
   auditor might flag the same-account root principal
   (`111111111111:root` + `networkmanager:*`) as permissive. The skill
   recognises it as the NORMAL root-of-trust delegation and only flags
   the cross-account `222222222222:root` principal.

3. **The multi-CIDR VPC is considered.** The prod VPC advertises BOTH
   `10.0.0.0/16` and `10.1.0.0/16` (primary + secondary). The skill
   checks every CIDR, not just the primary — the secondary
   `10.1.0.0/16` does not overlap with any other attachment, but a
   generic assistant might miss that the secondary exists at all.

4. **Severity aggregation.** The verdict is CIDR_OVERLAP (the worst
   finding), but the FINDINGS list shows both the CIDR_OVERLAP and
   PERMISSIVE_POLICY findings independently, so the operator can triage
   each issue separately.

## Slash-command invocation

```
/aws:audit-networkmanager-core-network
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this Cloud WAN core network before opening to shared services"
```

The orchestrator emits
`[Phase: Audit | Skills routed: networkmanager-core-network-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policy, validate the core network posture:

```bash
# Verify the cross-account principal was scoped down
aws networkmanager get-resource-policy \
  --resource-arn arn:aws:networkmanager:us-east-1:111111111111:core-network/core-network-prod-shared \
  --profile default --output json | jq '.Statement[] | .Principal'

# Confirm all attachments are ATTACHED
aws networkmanager list-attachments \
  --core-network-id core-network-prod-shared \
  --profile default --output json | jq '.Attachments[] | {AttachmentId, AttachmentStatus}'

# Verify LIVE matches LATEST
aws networkmanager get-core-network-policy \
  --core-network-id core-network-prod-shared --policy-version LIVE \
  --profile default --output json | jq '.CoreNetworkPolicy.PolicyVersionId'
```
