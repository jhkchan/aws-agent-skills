# End-to-End Example: Route 53 Weighted-Canary Routing Deployment

A walkthrough showing how to use the `route53-routing-policy-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are rolling out a new API version to 10% of traffic via weighted
DNS routing. You need:

- Two weighted A records for `api.example.com`
- Primary target 10.0.0.10 (weight 90) with its own health check
- Canary target 10.0.0.20 (weight 10) with its own health check
- Atomic change-batch POST (both records in one call)
- 60-second TTL for fast canary re-normalization when a HC flips
- `test-dns-answer` verification

Hosted zone: `Z2DABCDEFGHIJK` (example.com)
Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-route53-routing-policy
```

Then paste the routing requirements.

### Option B: Natural language

```
You: "Provision weighted routing for api.example.com in zone
      Z2DABCDEFGHIJK. Primary 10.0.0.10 weight 90, canary 10.0.0.20
      weight 10. Health checks on HTTPS /healthz for both, atomic
      change-batch, TTL 60."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create route 53 weighted routing policy"
```

Output:

```
[Phase: Deploy | Skills routed: route53-routing-policy-deployer]
Primary route: route53-routing-policy-deployer (score: 21)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
RECORD_SET: api.example.com A (routing policy: weighted)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Hosted zone confirmed: Z2DABCDEFGHIJK (example.com)
  [✓] Routing policy: weighted
  [✓] Target(s): primary 10.0.0.10 (w=90, hc-aaa), canary 10.0.0.20 (w=10, hc-bbb)
  [✓] Health check(s): hc-aaa (HTTPS /healthz, 30s, threshold 3), hc-bbb (same)
  [✓] Change-batch atomic: CREATE 2 records (single POST, weighted set complete before apply)
  [OPTIONAL] Optional feature: none
  [✓] TTL applied: 60s (rationale: weighted canary needs fast re-normalization on HC flip)
VERIFICATION_COMMANDS:
  aws route53 test-dns-answer --hosted-zone-id Z2DABCDEFGHIJK --record-name api.example.com. --record-type A
  aws route53 get-health-check-status --health-check-id hc-aaa
  aws route53 get-health-check-status --health-check-id hc-bbb
  aws route53 list-resource-record-sets --hosted-zone-id Z2DABCDEFGHIJK --query 'ResourceRecordSets[?Name==`api.example.com.`]'
```

---

## Step 3 — Provisioning commands

```bash
# Step 4: Create the two health checks FIRST (records reference their IDs)
HC_PRIMARY=$(aws route53 create-health-check \
  --caller-reference "$(date +%s)-primary" \
  --health-check-config '
    Type=HTTPS,
    Port=443,
    ResourcePath=/healthz,
    FullyQualifiedDomainName=10.0.0.10,
    RequestInterval=30,
    FailureThreshold=3,
    EnableSNI=true,
    MeasureLatency=true
  ' --query 'HealthCheck.Id' --output text)

HC_CANARY=$(aws route53 create-health-check \
  --caller-reference "$(date +%s)-canary" \
  --health-check-config '
    Type=HTTPS,
    Port=443,
    ResourcePath=/healthz,
    FullyQualifiedDomainName=10.0.0.20,
    RequestInterval=30,
    FailureThreshold=3,
    EnableSNI=true,
    MeasureLatency=true
  ' --query 'HealthCheck.Id' --output text)

# Step 5: Atomic change-batch (both weighted records in a single POST)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2DABCDEFGHIJK \
  --change-batch "{
    \"Changes\": [
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"api.example.com.\",
          \"Type\": \"A\",
          \"SetIdentifier\": \"primary\",
          \"Weight\": 90,
          \"HealthCheckId\": \"$HC_PRIMARY\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"10.0.0.10\"}]
        }
      },
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"api.example.com.\",
          \"Type\": \"A\",
          \"SetIdentifier\": \"canary\",
          \"Weight\": 10,
          \"HealthCheckId\": \"$HC_CANARY\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"10.0.0.20\"}]
        }
      }
    ]
  }"
```

---

## Step 4 — Post-deployment verification

```bash
# Resolve as a client would — verify the weighted split is live
aws route53 test-dns-answer \
  --hosted-zone-id Z2DABCDEFGHIJK \
  --record-name api.example.com. \
  --record-type A

# Confirm each health check is Healthy
aws route53 get-health-check-status --health-check-id $HC_PRIMARY
aws route53 get-health-check-status --health-check-id $HC_CANARY

# Confirm both records are present
aws route53 list-resource-record-sets \
  --hosted-zone-id Z2DABCDEFGHIJK \
  --query 'ResourceRecordSets[?Name==`api.example.com.`]'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Per-record health checks | Skipped | Both records reference HCs | Weighted sends dead targets their allotted percentage without HC. The HC lets Route 53 re-normalize weights when a target fails. |
| Atomic change-batch | Two separate POSTs | Single POST with both records | Sequential POSTs leave a window where only one record exists; Route 53 routes 100% to it, defeating the canary. |
| TTL=60 | TTL=300 | TTL=60 with rationale | A 300s TTL caches the dead canary IP for 5 minutes per resolver. 60s bounds the bad-canary exposure window. |
| `test-dns-answer` verification | Skipped | Required in checklist | The only way to confirm the weighted set is live and returning both records without a real client. |
| `get-health-check-status` verification | Skipped | Required in checklist | A record referencing a not-yet-healthy HC is omitted from rotation; the canary silently receives 0% until HC flips Healthy. |

---

## Related artifacts

- **Skill definition:** `skills/route53-routing-policy-deployer/SKILL.md`
- **Change-batch templates:** `skills/route53-routing-policy-deployer/references/routing-policy-change-batches.md`
- **Health check & ARC procedures:** `skills/route53-routing-policy-deployer/references/health-check-and-arc-procedures.md`
- **Slash command:** `commands/aws/deploy-route53-routing-policy.md`
- **Eval suite:** `skills/route53-routing-policy-deployer/evals/evals.json`
- **Legacy test cases:** `skills/route53-routing-policy-deployer/eval/test-cases.yaml`
