---
description: Provision a CloudFront KeyValueStore (KVS) with production-grade defaults (cloudfront-js-2.0 function runtime, KVS-function linkage, A/B testing routing, feature flags, IP allowlists, 1 MB size limit, eventual consistency model). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create cloudfront keyvaluestore"
  - "cloudfront kvs"
  - "kvs cloudfront functions"
  - "cloudfront key value store"
  - "cloudfront ab testing edge"
  - "edge feature flags"
  - "cloudfront feature flags kvs"
  - "cloudfront ip allowlist kvs"
  - "cloudfront ip blocklist kvs"
  - "cf.openkvs"
  - "cloudfront-js-2.0"
  - "kvs 1mb limit"
  - "kvs propagation"
  - "cloudfront edge redirect kvs"
  - "cloudfront functions kvs"
routes_to: cloudfront-keyvaluestore-deployer
---

# /aws:deploy-cloudfront-keyvaluestore

Activate the `cloudfront-keyvaluestore-deployer` skill and provision a
CloudFront KeyValueStore with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. KVS creation (store + key-value pairs)
2. Key-value pair management (put/get/delete)
3. CloudFront Functions integration (cf.openKvs)
4. A/B testing routing via KVS
5. Feature flags via KVS
6. IP allowlists / blocklists via KVS
7. KVS size limits (1 MB store, key/value constraints)
8. KVS propagation and eventual consistency
9. Recent features

## When to use

- You need to create a CloudFront KeyValueStore.
- You are integrating CloudFront Functions with KVS for edge routing.
- You need edge-side A/B testing or canary routing.
- You need feature flags that toggle without function redeployment.
- You need IP allowlist or blocklist logic in CloudFront Functions.
- You need KVS-driven URL redirects or rewrites.

## When NOT to use

- **Lambda@Edge** — different runtime, no KVS access.
- **CloudFront origin failover** — use origin groups, not KVS.
- **Caching behavior changes** — use cache policies, not KVS.
- **Auditing existing distributions** — use
  `cloudfront-distribution-auditor`.

## How to invoke

### Slash command

```
/aws:deploy-cloudfront-keyvaluestore
```

Then provide: KVS name, use case (A/B testing, feature flags, IP
allowlist, redirects), CloudFront distribution ID, function name,
function runtime (cloudfront-js-2.0 required), key schema.

### Natural language

Any of these routes to the same skill:

- "create a CloudFront KeyValueStore for A/B testing"
- "set up edge feature flags with KVS"
- "use KVS to block IPs at the CloudFront edge"
- "integrate CloudFront Functions with a KeyValueStore"
- "create a KVS-driven redirect function"

### CLI routing

```bash
node cli/bin/cli.js route "create cloudfront keyvaluestore"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create CloudFront
KeyValueStores or integrate them with CloudFront Functions. The output
checklist feeds into verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-cloudfront-keyvaluestore

     Create a CloudFront KeyValueStore named ab-testing-kvs for
     A/B testing. I need a CloudFront Function named ab-test-router
     that reads the KVS to route traffic between variant-a and
     variant-b. Distribution E1234567890ABC. Account: 123456789012.

Skill:
  KVS_DEPLOYMENT: ab-testing-kvs
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] KVS store: ab-testing-kvs — created
    [✓] Store size: ~200 bytes / 1 MB
    [✓] Key schema: kebab-case with ab- prefix
    [✓] Use case: A/B testing
    [✓] Function runtime: cloudfront-js-2.0
    [✓] Function stage: LIVE (published)
    [✓] KVS-function link: associated
    [✓] Distribution: E1234567890ABC
    [✓] Propagation: eventual consistency acknowledged
  VERIFICATION_COMMANDS:
    aws cloudfront-keyvaluestore describe-key-value-store --kvs-arn <arn>
    aws cloudfront-keyvaluestore list-keys --kvs-arn <arn>
    aws cloudfront describe-function --name ab-test-router
```

## References

- Skill definition: `skills/cloudfront-keyvaluestore-deployer/SKILL.md`
- Functions KVS API detail: `skills/cloudfront-keyvaluestore-deployer/references/kvs-functions-integration.md`
- Provisioning CLI commands: `skills/cloudfront-keyvaluestore-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/cloudfront-keyvaluestore-deployer/evals/evals.json`
