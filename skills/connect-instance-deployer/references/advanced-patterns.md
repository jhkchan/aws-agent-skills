# Advanced Patterns (load on demand) — Connect Instance Deployer

Expert-knowledge deep dives, misconceptions, dependency tables, provisioning recipes, and recent features moved verbatim from SKILL.md. Loaded on demand.

---

## Mindset — three Connect design misconceptions (moved from SKILL.md)

- **"A contact flow is just an IVR menu."** It is not. A contact
  flow is a JSON spec DAG of typed blocks: Action (PlayPrompt,
  InvokeLambda, TransferToQueue, InvokeAmazonLex), Branch
  (CheckHoursOfOperation, Compare, EvaluateAttribute), Terminal
  (Disconnect). The drag-and-drop console edits this JSON;
  programmatic deployments author it directly. Treating it as a
  flat menu misses Lambda-driven dynamic routing and Lex-driven
  conversational IVR.

- **"A routing profile is just a queue assignment."** It is not. A
  routing profile associates an agent with queues AND specifies
  the SKILL REQUIREMENTS that determine which contacts the agent
  handles. Without skills, routing is pure queue-and-priority.
  With skills, contacts route to the agent with the highest
  proficiency matching the contact's required skill. Misdesigning
  skill requirements produces "the contact routed to the wrong
  agent" tickets.

- **"IVR means pressing 1 or 2."** Modern IVR is conversational
  via Amazon Lex V2. The InvokeAmazonLex block invokes a Lex bot
  to elicit an intent and fill slots through natural-language
  conversation. The bot returns an intent and slots to the flow,
  which branches on those values. Treating IVR as touch-tone only
  misses the conversational IVR pattern.

---

## Configuration dependency graph (moved from SKILL.md)

Connect configurations are NOT independent. Instance before flows;
flows reference queues and Lambda functions; routing profiles
reference queues and skills; phone numbers are claimed at instance
level.

| Configuration | Hard dependencies (silent failure without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Instance | Identity mode selected | Alias immutable; identity mode set at creation | flows, queues, routing profiles, phone numbers, users |
| Contact flow | Instance; flow JSON valid; referenced queues/Lambda exist | flow with dangling refs creates at API but fails at run time | inbound contact handling |
| Lambda function | Function deployed in same region; resource policy grants Connect invoke | without resource policy, Lambda invocations fail AccessDenied | dynamic IVR logic |
| Queue | Instance; HoursOfOperation defined | queue with no agents via routing profile holds contacts indefinitely | routing target |
| Routing profile | Instance; queues defined; skills defined (if used) | agent without routing profile cannot log in to CCP | agent routing |
| Skill | Instance; skill name unique | proficiency is set on the agent, not the skill | skills-based routing |
| User (agent) | Instance; routing profile + security profile assigned | SAML users managed in IdP; Connect-dir users via CreateUser | login to CCP, handle contacts |
| Phone number | Instance claimed via ClaimedPhoneNumber or porting | per-region; toll-free vs DID affects inbound | inbound voice |
| Lex bot (V2) | Dialect ID set; bot published; Connect integrated via InvokeAmazonLex | Lex V1 deprecated path | conversational IVR |
| Voice ID | Instance; domain created; consent disclosure in flow | enrollment requires caller consent | authentication, fraud |
| Contact Lens | Instance; language model; sentiment/redaction settings | post-call vs real-time (different features) | sentiment, transcription |
| Recording (S3+KMS) | S3 bucket with KMS; KMS key policy grants Connect | recordings encrypted with KMS | call recording storage |
| Real-time metrics | Instance | built-in; custom via Kinesis | operations |
| Historical metrics | Instance; CTR export configured | CTRs available 24 months; longer needs S3 | analytics |

**The contact-flow-block-references row is the one a baseline model
misses.** A model that authors a flow JSON without verifying
referenced queues, Lambda functions, and Lex bots will produce a
flow that creates at the API but fails at run time when a contact
hits the dangling reference.

**Cross-dependency gotchas:**
- A flow referencing a non-existent queue (or wrong queue ARN)
  creates successfully but every contact fails at TransferToQueue.
- A Lambda without a resource policy granting `connect.amazonaws.com`
  returns AccessDenied when the flow runs.
- A routing profile without skill requirements produces pure queue-
  priority routing (no skills-based matching).
- Phone numbers are per-region. US toll-free does not work in EU.
- Amazon Lex V1 is on a deprecation path; use Lex V2 via
  InvokeAmazonLex.

---

## Expert heuristic: contact flow JSON with Lambda invoke blocks (moved from SKILL.md)

A baseline model treats the flow as a touch-tone IVR. The correct
heuristic recognizes the flow as a DAG of typed blocks and the
InvokeLambda block as the integration point for dynamic IVR logic.

```text
Sample flow DAG:
  Start → CheckHoursOfOperation
            ├── (Open) → InvokeLambda(lookup_customer)
            │             ├── Return → PlayPrompt(greeting) → InvokeAmazonLex(route_call)
            │             │                              ├── intent=Sales    → TransferToQueue(Sales)
            │             │                              └── intent=Support  → TransferToQueue(Support)
            │             └── Error → TransferToQueue(Default)
            └── (Closed) → PlayPrompt(closed) → Disconnect

InvokeLambda block (JSON):
  Identifier: "lookup_customer", Type: "Action"
  Parameters: { FunctionARN, InvocationTimeLimitSeconds: 5 }
  Transitions: {
    NextAction: "play_greeting",
    Exceptions: [
      { NextAction: "transfer_default", Error: "Lambda.AccessDenied" },
      { NextAction: "transfer_default", Error: "Lambda.Timeout" }
    ]
  }
```

**Key implication:** Lambda invocations from Connect flows MUST
handle exceptions (AccessDenied, Timeout, GenericError). Without
exceptions, a Lambda failure traps the contact. The Lambda
resource policy MUST grant `connect.amazonaws.com` invoke with the
instance ARN as source.

---

## Expert heuristic: routing profile skill requirements (moved from SKILL.md)

A baseline model treats routing profiles as queue priorities. The
correct heuristic recognizes that skill requirements (skill name +
proficiency) determine which contacts route to which agents.

```text
Routing profile with skill requirements:
  Queues: Sales (priority 1), Support (priority 2)

  Agent A: Sales=5, Support=3
  Agent B: Support=5

Contact X (required skill: Sales, proficiency ≥ 4):
  → Agent A (Sales=5 ≥ 4)
  → Agent B INELIGIBLE (no Sales skill)

Contact Y (required skill: Support, proficiency ≥ 4):
  → Agent B (Support=5 ≥ 4)
  → Agent A INELIGIBLE for this contact (Support=3 < 4)
```

**Key implication:** skills are defined at the instance level,
proficiency is set on each agent per skill, and contacts specify
the required skill + proficiency via the contact flow. Without all
three, skills-based routing silently degrades to queue-priority.

---

## Expert heuristic: Lex bot integration for IVR (moved from SKILL.md)

A baseline model treats IVR as touch-tone menus. The correct
heuristic recognizes the InvokeAmazonLex block as the integration
point for conversational IVR.

```text
Flow with Lex IVR:
  Start → PlayPrompt("How can I help you?")
       → InvokeAmazonLex(bot=CustomerService, intent=RouteCall, slot=department)
            ├── Lex elicits slot via conversation:
            │     "Are you calling about Sales or Support?"
            │     Caller: "Sales" → slot filled {department: "Sales"}
            └── Lex returns intent=RouteCall, slots={department: Sales}
       → Branch on slot value:
            ├── department == "Sales"   → TransferToQueue(Sales)
            ├── department == "Support" → TransferToQueue(Support)
            └── unknown → loop back to InvokeAmazonLex
```

**Key implication:** the Lex bot must be a published alias (not
DRAFT) and the locale must match the Connect instance language.
Bot responses can be slow on cold paths; set session timeouts and
Lambda fallbacks.

---

## Step 1 — Instance creation CLI (moved from SKILL.md)

```bash
INSTANCE_ID=$(aws connect create-instance \
  --instance-name "my-connect-cc" \
  --IdentityManagementType SAML \
  --InboundCallsEnabled --OutboundCallsEnabled \
  --ClientToken "unique-token-1" \
  --query 'Id' --output text)
aws connect describe-instance --instance-id "$INSTANCE_ID"
```

For `CONNECT_MANAGED`, omit `--DirectoryId`. For
`EXISTING_DIRECTORY`, pass `--DirectoryId d-1234567890`.

---

## Step 4 — Queues and quick-connect lists (CLI) (moved from SKILL.md)

Queues are routing targets. Each queue has HoursOfOperation,
quick-connect list (for transfers), hold-flow, and outbound caller
ID.

```bash
QUEUE_ID=$(aws connect create-queue \
  --instance-id "$INSTANCE_ID" \
  --name "sales-queue" \
  --hours-of-operation-id <hours-of-operation-id> \
  --outbound-caller-id-number-id <phone-number-id> \
  --query 'QueueId' --output text)
```

Quick-connect (transfer target):

```bash
aws connect create-quick-connect --instance-id "$INSTANCE_ID" \
  --name "sales-escalation" \
  --quick-connect-config '{"QuickConnectType":"QUEUE","QueueConfig":{"QueueId":"'"$QUEUE_ID"'","ContactFlowId":"<flow-id>"}}'
```

---

## Step 6 — Agent hierarchy CLI (moved from SKILL.md)

```bash
HIERARCHY_GROUP_ID=$(aws connect create-user-hierarchy-group \
  --instance-id "$INSTANCE_ID" \
  --name "Sales - North America" \
  --parent-group-id <parent-group-id-or-omit> \
  --query 'HierarchyGroupId' --output text)
```

---

## Step 7 — Phone number claim CLI (toll-free, DID, porting) (moved from SKILL.md)

```bash
PHONE_NUMBER_ID=$(aws connect claim-phone-number \
  --instance-id "$INSTANCE_ID" \
  --target-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID" \
  --phone-number-description "Main inbound toll-free" \
  --phone-number-type TOLL_FREE \
  --phone-number +18005551234 \
  --query 'PhoneNumberId' --output text)
```

For DID: `--phone-number-type DID`. Porting: use the console or
`create-task` to start; requires a Letter of Authorization and may
take 2-4 weeks. Match phone number region to instance region.

---

## Step 10 — Voice ID (speaker enrollment, fraud) (moved from SKILL.md)

Amazon Connect Voice ID authenticates callers by voice biometrics.

Prerequisites: Voice ID domain created; consent disclosure in the
flow (legal requirement); opt-in/opt-out handling.

```json
{
  "Identifier": "voice-id-enroll", "Type": "Action",
  "Parameters": {"VoiceIdDomainId": "<domain-id>", "VoiceIdOperation": "ENROLL_OR_AUTHENTICATE"},
  "Transitions": {
    "NextAction": "branch-on-voice-id-result",
    "Conditions": [
      {"NextAction": "high-confidence", "Condition": {"VoiceIdResult": "AUTHENTICATED_HIGH"}},
      {"NextAction": "low-confidence", "Condition": {"VoiceIdResult": "AUTHENTICATED_LOW"}},
      {"NextAction": "fraud-risk", "Condition": {"VoiceIdResult": "FRAUD_RISK_DETECTED"}}
    ]
  }
}
```

---

## Step 11 — Contact Lens (sentiment, transcription, redaction) (moved from SKILL.md)

| Feature | Mode | Use case |
|---|---|---|
| Real-time sentiment | Real-time | Supervisor alerts on negative sentiment |
| Post-call transcription | Post-call | Searchable call transcripts |
| Post-call summary | Post-call | Auto-generated issue + outcome summary |
| Sensitive-data redaction | Post-call | Mask credit card / SSN in transcript |
| Categories | Both | Auto-tag contacts by keyword / sentiment pattern |

```bash
aws connect update-instance-storage-config \
  --instance-id "$INSTANCE_ID" \
  --association-id <association-id> \
  --resource-type CONTACT_LENS
```

---

## Step 12 — Chat, voice, task channels (moved from SKILL.md)

| Channel | Provisioning |
|---|---|
| VOICE | Phone number claimed + contact flow |
| CHAT | Chat widget on website / mobile; chat contact flow |
| TASK | Task template created; task contact flow |

```bash
aws connect create-task-template \
  --instance-id "$INSTANCE_ID" \
  --name "follow-up-task" \
  --contact-flow-id <task-flow-id> \
  --fields '[{"Description":"Reason","Id":"reason","Type":"TEXT"}]' \
  --status ACTIVE
```

---

## Step 13 — S3 recording storage with KMS encryption (moved from SKILL.md)

```bash
aws s3api put-bucket-encryption \
  --bucket connect-recordings-123456789012 \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"arn:aws:kms:us-east-1:123456789012:key/abc123"}}]}'

aws connect associate-instance-storage-config \
  --instance-id "$INSTANCE_ID" \
  --resource-type CALL_RECORDINGS \
  --storage-config \
    '{"S3Config":{"BucketName":"connect-recordings-123456789012","BucketPrefix":"recordings","EncryptionConfig":{"EncryptionType":"KMS","KeyId":"arn:aws:kms:us-east-1:123456789012:key/abc123"}},"StorageType":"S3"}'
```

KMS key policy MUST grant `connect.amazonaws.com` Encrypt/Decrypt/
GenerateDataKey with `aws:SourceAccount` condition. Plain S3
recordings are unencrypted at rest — always use SSE-KMS.

---

## Step 14 — Real-time and historical metrics (moved from SKILL.md)

| Type | Source | Latency |
|---|---|---|
| Real-time (ContactFlow, RoutingProfile, Queue, Agent) | Instance built-in | Seconds |
| Historical (ContactTraceRecord) | S3 export or console | Up to 24 months |
| Custom real-time metrics | Kinesis stream | Seconds |

```bash
aws connect get-contact-metrics --instance-id "$INSTANCE_ID" \
  --filters '{"Queues":["'"$QUEUE_ID"'"],"Channels":["VOICE"]}'
```

---

## Step 15 — Recent features (moved from SKILL.md)

- **Amazon Q in Connect (2023-2026):** generative AI assistant for
  agents — real-time suggested responses and KB articles.
- **Customer Profiles (2023-2024):** unified profile store with
  event-triggered updates.
- **Amazon Connect Cases (2023-2024):** case management for
  multi-contact issues; integrates with Tasks.
- **Voice ID generative improvements (2024-2025):** reduced
  enrollment time, improved fraud-risk accuracy, multi-language.
- **Contact Lens real-time summaries (2024-2025):** generative AI
  summaries in real-time, not just post-call.
- **Amazon Lex V2 generative AI (2024-2025):** open-ended intent
  elicitation and assisted slot filling.
- **WebRTC media streaming (2024-2025):** browser-based voice
  reducing PSTN costs.
