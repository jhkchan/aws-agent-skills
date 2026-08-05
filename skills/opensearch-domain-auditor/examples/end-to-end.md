# End-to-end usage scenario: opensearch-domain-auditor

A walkthrough showing the skill auditing an internet-facing production
OpenSearch domain that has a public wildcard data-plane grant (PUBLIC_ACCESS)
compounded by FGAC disabled (NO_FGAC) and an AWS-managed KMS key (CONFIG_GAP).
Demonstrates worst-finding aggregation, the immutability reasoning for
encryption layers, and the assume-breach remediation workflow.

## Input (user prompt)

> Audit this OpenSearch domain before we onboard payments traffic. The
> domain currently hosts shared analytics dashboards.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "es:ESHttp*",
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/logs-prod/*"
    }
  ]
}
```

Domain configuration:

- EngineVersion: OpenSearch_2.11
- ClusterConfig: DedicatedMasterEnabled true, DedicatedMasterType
  m5.large.search, DedicatedMasterCount 3, InstanceType m5.large.search,
  InstanceCount 3, ZoneAwarenessEnabled true
- EncryptionAtRestOptions: Enabled true, KmsKeyId aws/es (AWS-managed)
- NodeToNodeEncryptionOptions: Enabled true
- DomainEndpointOptions.EnforceHTTPS: true
- AdvancedSecurityOptions.Enabled: false
- LogPublishingOptions: SEARCH_SLOW_LOGS + INDEX_SLOW_LOGS enabled
- VPCOptions: absent (internet-facing)

## Skill output

```text
DOMAIN: logs-prod
VERDICT: PUBLIC_ACCESS
REASON: Access policy Statement "OpenAccess" grants es:ESHttp* to Principal
"*" with no restrictive condition (Step 2a) — any AWS account holder can
read, write, or delete every document and index via the OpenSearch REST
API. FGAC is also disabled, compounding the data-plane exposure, and the
AWS-managed KMS key strips audit-trail control.
FINDINGS:
  - [PUBLIC_ACCESS] Principal "*" + es:ESHttp* with no condition (Step 2a)
    — data-plane blast-radius multiplier: total document/index exposure
  - [NO_FGAC] AdvancedSecurityOptions.Enabled is false on an internet-facing
    domain (Step 3a) — no per-index/per-role enforcement layer
  - [CONFIG_GAP] EncryptionAtRestOptions.KmsKeyId is aws/es — AWS-managed
    key, no customer CloudTrail Decrypt audit trail, no rotation control,
    no customer key policy (Step 4e)
  - [OK] NodeToNodeEncryptionOptions.Enabled is true (Step 4a)
  - [OK] DedicatedMasterType m5.large.search x 3 across 3 AZs (Step 4b)
  - [OK] LogPublishingOptions publishes SEARCH_SLOW_LOGS and INDEX_SLOW_LOGS
    (Step 4c)
REMEDIATION:
  1. PUBLIC_ACCESS — Immediately remove the wildcard principal from
     Statement "OpenAccess" or restrict via aws:SourceAccount. Back up the
     policy first:
     aws opensearch describe-domain-access-policy --domain-name logs-prod \
       --output json > /tmp/logs-prod-policy-backup.json
  2. PUBLIC_ACCESS — Assume breach. Audit CloudTrail for es:ESHttp* events
     from external principals during the exposure window. Reindex
     compromised indices into a fresh domain.
  3. NO_FGAC — Prerequisite: NTN must be on (it is). Enable FGAC with an
     IAM master (recommended over internal user database):
     aws opensearch update-domain-config --domain-name logs-prod \
       --advanced-security-options 'Enabled=true,InternalUserDatabaseEnabled=false,MasterUserOptions={MasterUserARN=arn:aws:iam::111111111111:role/opensearch-master}'
     Then define roles and role mappings via the Security plugin REST API.
  4. CONFIG_GAP — Plan a CMK migration (requires domain recreation).
     Customer-managed CMK provides CloudTrail Decrypt logging and
     customer-controlled rotation.
```

## What the skill caught that a generic assistant misses

1. **The es:ESHttp* data-plane multiplier.** A generic assistant says
   "the access policy is permissive." The skill explains that
   `es:ESHttp*` to `Principal: "*"` is total REST API exposure — every
   document readable, every index deletable, every mapping mutable. The
   data plane is the OpenSearch REST API, not a single record.

2. **FGAC is independent from the access policy.** A naive auditor flags
   the access policy but treats FGAC as a "nice-to-have." The skill
   classifies FGAC-disabled-on-internet-facing as NO_FGAC (HIGH) —
   because even with a restrictive access policy, any principal granted
   `es:ESHttp*` has unrestricted access to every index. FGAC adds the
   per-index enforcement layer that the access policy cannot provide.

3. **AWS-managed `aws/es` is not "encrypted = OK."** Many auditors treat
   any `EncryptionAtRestOptions.Enabled: true` as a pass. The skill
   distinguishes customer-managed CMK (audit trail, rotation, policy
   control) from AWS-managed `aws/es` (opaque, no rotation control, no
   policy) — a CONFIG_GAP finding, not OK.

4. **The immutability reasoning for remediation.** Generic advice says
   "enable FGAC." The skill surfaces the prerequisite chain: FGAC
   requires NTN requires HTTPS. On this domain NTN is on, so FGAC can be
   enabled in-place. If NTN were off, the skill would flag domain
   recreation as the only remediation path (NTN is immutable).

5. **The assume-breach workflow.** Generic advice says "remove the
   access." The skill's remediation includes auditing CloudTrail for
   `es:ESHttp*` events during the exposure window and reindexing
   compromised data — because the documents may have already been
   exfiltrated.

## Slash-command invocation

```
/aws:audit-opensearch-domain
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this OpenSearch domain before we onboard payments traffic"
```

The orchestrator emits
`[Phase: Audit | Skills routed: opensearch-domain-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the access policy, validate the domain posture:

```bash
# Verify the wildcard principal was removed
aws opensearch describe-domain-access-policy --domain-name logs-prod \
  --profile default --output json | jq '.accessPolicy.Policy.Statement[].Principal'

# Confirm FGAC is enabled after the update-domain-config call
aws opensearch describe-domain-config --domain-name logs-prod \
  --profile default --query 'DomainConfig.AdvancedSecurityOptions.Options.Enabled'

# Confirm slow log publishing is still wired
aws opensearch describe-domain-config --domain-name logs-prod \
  --profile default --query 'DomainConfig.LogPublishingOptions.Options'
```

Then monitor CloudTrail for `es:ESHttp*` events from unexpected principals
for 1-2 weeks. The snapshot-based reindex into a fresh CMK-encrypted domain
is the long-term remediation for the AWS-managed-key gap.
