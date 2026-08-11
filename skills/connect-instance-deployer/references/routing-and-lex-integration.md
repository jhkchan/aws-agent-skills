# Routing Profiles and Lex Integration — Connect Instance Deployer

Deep reference on routing profiles (queue associations, skill
requirements, proficiency levels, media concurrency), the skills-
based routing model (skill on instance + proficiency on agent +
required skill on contact), Amazon Lex V2 integration for IVR
(InvokeAmazonLex block, bot alias, intent elicitation, slot
filling, locale matching), and common routing/IVR pitfalls. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Routing profiles

A routing profile associates an agent with one or more queues and
optionally defines skill requirements that determine which contacts
the agent handles.

### Anatomy of a routing profile

| Element | Purpose |
|---|---|
| Queues | Ordered list of queues the agent handles (with priority and delay) |
| Media concurrencies | Max concurrent contacts per channel (VOICE, CHAT, TASK) |
| Skill requirements (optional) | Skills the agent must have (with proficiency level) — applies to the routing profile's agents |
| Default outbound queue | Queue used for outbound contacts |
| Tags | Free-form key-value |

```bash
aws connect create-routing-profile \
  --instance-id inst-abc123 \
  --name "tier-1-sales-support" \
  --description "Tier-1 agents handling Sales and Support" \
  --default-outbound-queue-id "$DEFAULT_QUEUE_ID" \
  --queue-configs '[
    {"QueueReference": {"QueueId": "'"$SALES_QUEUE_ID"'", "Channel": "VOICE"}, "Priority": 1, "Delay": 0},
    {"QueueReference": {"QueueId": "'"$SUPPORT_QUEUE_ID"'", "Channel": "VOICE"}, "Priority": 2, "Delay": 0}
  ]' \
  --media-concurrencies '[{"Channel": "VOICE", "Concurrency": 1}]'
```

### Queue priority and delay

Each queue association has a `Priority` (lower = higher priority)
and `Delay` (seconds before the contact rings the agent). Contacts
in priority-1 queues ring before priority-2 queues, regardless of
wait time.

**Common pattern:**
- Sales queue: priority 1, delay 0 (answer immediately)
- Support queue: priority 2, delay 0 (answer if no sales contacts)
- Callback queue: priority 3, delay 30 (defer callbacks)

### Media concurrency

Max concurrent contacts per channel per agent. Set per routing
profile (not per agent).

| Channel | Typical concurrency |
|---|---|
| VOICE | 1 (one call at a time) |
| CHAT | 3-5 (multiple chats) |
| TASK | 5-10 (multiple tasks) |

## Skills-based routing model

Skills-based routing has three components. ALL THREE must be
configured for skills-based routing to work; without all three,
routing silently degrades to queue-priority routing.

| Component | Where it lives | Example |
|---|---|---|
| Skill | Instance (defined once) | "Sales", "Support", "Tier 2" |
| Skill proficiency | User (per-agent) | Agent A: Sales=5, Support=3 |
| Required skill | Contact (via SetAttributes or TransferToQueue) | Contact X: Sales, proficiency ≥ 4 |

### Skill definition (instance level)

Skills are defined at the instance level via the Connect console
or the user-provisioning API. Each skill has a name and (optionally)
proficiency levels 1-5.

### Skill proficiency (agent level)

Each user (agent) is assigned proficiencies on skills via
`create-user` / `update-user-routing-profile` or the console.

```bash
aws connect create-user \
  --instance-id inst-abc123 \
  --phone-config ... \
  --routing-profile-id "$ROUTING_PROFILE_ID" \
  --security-profile-id "$SECURITY_PROFILE_ID" \
  --username "agent.alice" \
  ...
```

Skill proficiencies are set via the console or via
`update-user-routing-profile` with skill proficiency lists.

### Required skill (contact level)

Contacts specify required skills via contact attributes set in the
flow (SetAttributes) or via TransferToQueue with skill parameters.

```json
{
  "Identifier": "set-required-skill",
  "Type": "Action",
  "Parameters": {
    "Attributes": {"requiredSkill": "Sales", "requiredProficiency": "4"}
  },
  "Transitions": {"NextAction": "transfer-sales"}
}
```

### How routing matches

When a contact enters a queue, Connect evaluates which agents in
the queue's associated routing profiles are eligible:

```text
Contact X: requiredSkill=Sales, requiredProficiency=4
  → Find agents with Sales skill AND proficiency ≥ 4
  → Among eligible agents, order by:
    1. Queue priority (lower = first)
    2. Agent's proficiency on the required skill (higher = first)
    3. Longest idle (tiebreaker)
```

If no agent has the required skill at the required proficiency, the
contact waits in queue indefinitely (or until the queue's
HoursOfOperation closes).

## Amazon Lex V2 integration for IVR

The InvokeAmazonLex block invokes a Lex V2 bot for conversational
IVR. The bot elicits an intent and fills slots through natural-
language conversation, then returns intent + slots to the flow.

### Prerequisites

- **Lex V2 bot exists** with at least one published alias (not
  DRAFT).
- **Bot's locale matches the Connect instance language.** en_US
  bot for en_US instance.
- **Bot has intents** with sample utterances and slot types.
- **(Optional) Lambda fulfillment** on the bot for back-end logic.

### InvokeAmazonLex block

```json
{
  "Identifier": "lex-ivr",
  "Type": "Action",
  "Parameters": {
    "BotAliasArn": "arn:aws:lex:us-east-1:123456789012:bot-alias/CustomerService:Prod",
    "Intent": "RouteCall",
    "Slots": {"department": null},
    "SessionAttributes": {"caller_id": "$.CustomerEndpoint.Address"}
  },
  "Transitions": {
    "NextAction": "branch-on-department",
    "Exceptions": [
      {"NextAction": "transfer-default", "Error": "Lex.Timeout"}
    ]
  }
}
```

**Critical fields:**
- `BotAliasArn`: ARN of the Lex V2 bot alias (NOT the bot ID
  alone). The alias must reference a published version.
- `Intent`: the intent to elicit (Lex elicits this intent and
  fills the slots via conversation).
- `Slots`: initial slot values (use null to let Lex elicit them).
- `SessionAttributes`: passed to Lex for context.
- `Exceptions`: handle Lex.Timeout (bot didn't respond in time).

### Branching on Lex response

After InvokeAmazonLex, the flow branches on the returned slot
values.

```json
{
  "Identifier": "branch-on-department",
  "Type": "Branch",
  "Parameters": {"ComparisonValue": "$.Lex.slots.department"},
  "Transitions": {
    "Conditions": [
      {"NextAction": "transfer-sales", "Condition": {"Operator": "Equals", "Value": "Sales"}},
      {"NextAction": "transfer-support", "Condition": {"Operator": "Equals", "Value": "Support"}}
    ],
    "NextAction": "play-sorry"
  }
}
```

### Lex V1 vs V2

| Feature | Lex V1 | Lex V2 |
|---|---|---|
| Block name | (older flow blocks) | `InvokeAmazonLex` |
| Bot identifier | Bot name + alias | Bot alias ARN |
| Status | Deprecation path | Current |
| Recommendation | Do NOT use for new deployments | Use for all new deployments |

**For new deployments:** always use Lex V2 via the InvokeAmazonLex
block. Lex V1 is on a deprecation path.

## Verifying routing profiles

```bash
aws connect describe-routing-profile \
  --instance-id inst-abc123 \
  --routing-profile-id "$ROUTING_PROFILE_ID"

aws connect list-routing-profile-queues \
  --instance-id inst-abc123 \
  --routing-profile-id "$ROUTING_PROFILE_ID"
```

## Verifying Lex integration

```bash
aws lexv2-models describe-bot-alias \
  --bot-id <bot-id> \
  --bot-alias-id <alias-id>

aws lexv2-models describe-bot-locale \
  --bot-id <bot-id> \
  --bot-version <version> \
  --locale-id en_US

aws lexv2-runtime recognize-text \
  --bot-id <bot-id> \
  --bot-alias-id <alias-id> \
  --locale-id en_US \
  --text "I need sales help" \
  --session-id test-session-1
```

## Terraform example

```hcl
resource "aws_connect_routing_profile" "tier1" {
  instance_id           = aws_connect_instance.main.id
  name                  = "tier-1-sales-support"
  description           = "Tier-1 agents handling Sales and Support"
  default_outbound_queue_id = aws_connect_queue.default.id

  queue_configs {
    queue_reference {
      queue_id = aws_connect_queue.sales.id
      channel  = "VOICE"
    }
    priority = 1
    delay    = 0
  }

  queue_configs {
    queue_reference {
      queue_id = aws_connect_queue.support.id
      channel  = "VOICE"
    }
    priority = 2
    delay    = 0
  }

  media_concurrencies {
    channel     = "VOICE"
    concurrency = 1
  }
}
```

## Common routing and IVR pitfalls

1. **Routing profile without skills.** Without skill requirements,
   routing silently degrades to queue-priority. Define skills at
   the instance level and set proficiencies on agents.

2. **Required proficiency too high.** If no agent has the required
   proficiency, the contact waits indefinitely. Verify the agent
   pool has agents meeting the required proficiency before launch.

3. **Queue priority vs skills interaction.** Queue priority
   determines which queue an agent pulls from; skills determine
   which contacts within that queue the agent is eligible for. A
   high-priority contact in a low-priority queue still waits
   behind the high-priority queue.

4. **Lex V1 in new flows.** Lex V1 is on a deprecation path. Use
   Lex V2 via the InvokeAmazonLex block.

5. **DRAFT Lex alias in production.** Connect invokes published
   aliases. DRAFT changes can break the flow silently. Use a
   versioned alias with controlled promotion.

6. **Locale mismatch.** A non-en_US bot in an en_US instance (or
   vice versa) produces unexpected IVR behavior. Verify locale
   match.

7. **No Lex timeout fallback.** Lex can time out on slow paths.
   Without an exception transition, the contact is trapped. Always
   set `Lex.Timeout` → fallback.

8. **Forgetting to publish the Lex bot.** Changes to a Lex bot
   must be published to a version, and the alias must be updated
   to point to the new version. Otherwise Connect invokes the old
   version.
