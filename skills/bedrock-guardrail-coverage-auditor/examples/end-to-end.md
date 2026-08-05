# End-to-end usage scenario: bedrock-guardrail-coverage-auditor

A walkthrough showing the skill auditing a Bedrock Guardrail that has strong
filters but incomplete model coverage (INCOMPLETE_COVERAGE) plus a hidden
DRAFT-version reference risk, demonstrating the per-request guardrail model,
severity aggregation, and the coverage-remediation workflow.

## Input (user prompt)

> We deployed a Bedrock Guardrail for our customer support platform. The
> guardrail has HIGH on sexual and violence, MEDIUM on hate and insult,
> grounding at 0.55. Three of our five resources reference it. Is this
> production-ready?

Guardrail configuration:

```yaml
name: prod-content-guard
guardrailId: grn-abc123
status: READY
version: 1

contentPolicy:
  filtersConfig:
    - type: SEXUAL, inputStrength: HIGH, outputStrength: HIGH
    - type: VIOLENCE, inputStrength: HIGH, outputStrength: HIGH
    - type: HATE, inputStrength: MEDIUM, outputStrength: HIGH
    - type: INSULT, inputStrength: MEDIUM, outputStrength: MEDIUM

contextualGroundingPolicy:
  filtersConfig:
    - type: GROUNDING, threshold: 0.55
    - type: RELEVANCE, threshold: 0.55

blockedInputMessaging: "Your request was blocked by the content policy."
blockedOutputsMessaging: "The response was blocked by the content policy."
```

Resource coverage:

```text
1. Agent: customer-support-agent    guardrail: grn-abc123 v1    COVERED
2. Agent: content-writer-agent      guardrail: NONE             UNGUARDED
3. KB:    product-docs-kb           guardrail: grn-abc123 v1    COVERED
4. App:   chat-app (converse)       guardrailIdentifier: NONE   UNGUARDED
5. App:   summarizer-app (converse) guardrailIdentifier: NONE   UNGUARDED
```

## Skill output

```text
GUARDRAIL: prod-content-guard (grn-abc123)
VERDICT: INCOMPLETE_COVERAGE
RISK: HIGH
REASON: Guardrail is READY with strong content filters and proper grounding,
but 3 of 5 Bedrock resources omit the guardrail identifier — those resources
are completely unguarded (Step 2). The guardrail filter configuration is
sound, but filter strength is irrelevant for any resource that does not pass
the guardrail ID at invocation time.
FINDINGS:
  - [HIGH] Agent "content-writer-agent" has no guardrailConfiguration — all
    user input and model output bypasses every filter (Step 2)
  - [HIGH] Application "chat-app" calls converse without guardrailIdentifier
    (Step 2)
  - [HIGH] Application "summarizer-app" calls converse without
    guardrailIdentifier (Step 2)
  - [OK] Guardrail status READY (Step 1)
  - [OK] All four core categories at outputStrength >= MEDIUM (Step 3)
  - [OK] Grounding threshold 0.55, relevance 0.55 (Step 4)
  - [OK] Blocked messaging configured (Step 5)
REMEDIATION:
  1. Add guardrailConfiguration to agent "content-writer-agent":
     aws bedrock update-agent --agent-id agent-bbb \
       --guardrail-configuration guardrailIdentifier=grn-abc123,guardrailVersion=1
  2. Update chat-app and summarizer-app to pass guardrailIdentifier="grn-abc123"
     and guardrailVersion="1" in every converse call.
  3. After adding coverage, verify by checking CloudWatch metrics for
     GuardrailIntervention events from each resource.
  4. Pin production callers to version "1" (numbered), not DRAFT — DRAFT
     version changes are live and unversioned.
```

## What the skill caught that a generic assistant misses

1. **The per-request guardrail model.** A generic assistant says "3 of 5
   resources don't have the guardrail." The skill explains that guardrails
   are passed per `converse` call, not attached to models — an application
   that omits `guardrailIdentifier` bypasses every filter regardless of
   what guardrails exist in the account. The filter strength is irrelevant
   for unguarded call paths.

2. **Coverage as a percentage with named resources.** The skill reports
   40% coverage (2 of 5) and lists each unguarded resource by name, making
   the remediation actionable rather than vague.

3. **DRAFT version risk flagged proactively.** Even though the current
   deployment references version 1 (numbered), the skill warns about
   pinning to DRAFT — preventing a future operator from accidentally
   switching to DRAFT and creating a live-edit risk.

4. **Grounding threshold validated.** The 0.55 threshold is in the
   recommended production range (0.51–0.75). A generic assistant might
   flag it as "too low" or not evaluate it at all.

## Slash-command invocation

```
/aws:audit-bedrock-guardrail-coverage
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Bedrock guardrail coverage before production launch"
```

The orchestrator emits
`[Phase: Audit | Skills routed: bedrock-guardrail-coverage-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the coverage gap:

```bash
# Verify all agents now reference the guardrail
aws bedrock list-agents --profile default --query \
  'agentSummaries[*].[agentName,guardrailConfiguration]'

# Check for guardrail interventions in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name GuardrailIntervention \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Sum \
  --profile default

# Verify the guardrail version referenced by each resource
aws bedrock get-agent --agent-id agent-bbb --profile default \
  --query 'guardrailConfiguration'
```

Then monitor CloudWatch for `GuardrailIntervention` events from each
resource for 1-2 weeks to confirm the guardrail is actively intercepting.
