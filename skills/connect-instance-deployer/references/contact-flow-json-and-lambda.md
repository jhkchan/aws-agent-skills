# Contact Flow JSON and Lambda — Connect Instance Deployer

Deep reference on the contact flow JSON spec (Version, StartAction,
Actions, Transitions, Parameters), block categories (Action, Branch,
Transfer, Terminal), the InvokeLambda block (FunctionARN,
InvocationTimeLimitSeconds, Transitions, Exceptions), the Lambda
resource policy requirement for connect.amazonaws.com, Lambda event
payload structure, and common flow-authoring pitfalls. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Contact flow JSON structure

A contact flow is a JSON object with three top-level keys:

```json
{
  "Version": "2024-07-30",
  "StartAction": "<identifier-of-start-block>",
  "Actions": [
    /* list of action objects */
  ]
}
```

Each action object has:

| Field | Purpose |
|---|---|
| `Identifier` | Unique ID within the flow (referenced by Transitions.NextAction) |
| `Type` | Block type: Action, Branch, Transfer, Terminal |
| `Parameters` | Block-specific parameters (e.g., FunctionARN, QueueArn, BotAliasArn) |
| `Transitions` | NextAction (next block) and Conditions / Exceptions (branching) |

## Block categories

### Action blocks

| Block | Purpose |
|---|---|
| PlayPrompt | Play an audio prompt (text-to-speech or audio file) |
| InvokeLambda | Invoke a Lambda function |
| InvokeAmazonLex | Invoke a Lex V2 bot for conversational IVR |
| TransferToQueue | Transfer to a queue |
| TransferToFlow | Transfer to another contact flow |
| SetAttributes | Set contact attributes (key-value) |
| SetRecordingBehavior | Enable/disable recording for the contact |
| StartMediaStreaming | Start audio streaming to Kinesis Video |
| CreateTask | Create a Task channel contact |

### Branch blocks

| Block | Purpose |
|---|---|
| CheckHoursOfOperation | Branch on whether the queue is open |
| CheckPhoneNumber | Branch on the called number |
| CheckStoredCustomerInput | Branch on stored DTMF input |
| Compare | Branch on attribute comparison |
| EvaluateAttribute | Branch on attribute value |
| GetCustomerInput | Collect DTMF or speech input |
| Loop | Loop back to a previous block (with limits) |

### Transfer blocks

| Block | Purpose |
|---|---|
| TransferToQueue | Transfer to a queue (terminal for this flow) |
| TransferToFlow | Transfer to another flow |
| TransferToAgent | Transfer to a specific agent |

### Terminal blocks

| Block | Purpose |
|---|---|
| Disconnect | End the call |

## InvokeLambda block — full anatomy

The InvokeLambda block is the integration point for dynamic IVR
logic. The Lambda receives a Connect event payload, performs
business logic (database lookup, decision), and returns JSON that
updates contact attributes.

```json
{
  "Identifier": "lookup-customer",
  "Type": "Action",
  "Parameters": {
    "FunctionARN": "arn:aws:lambda:us-east-1:123456789012:function:lookup-customer",
    "InvocationTimeLimitSeconds": "5"
  },
  "Transitions": {
    "NextAction": "play-greeting",
    "Exceptions": [
      {"NextAction": "transfer-default", "Error": "Lambda.AccessDenied"},
      {"NextAction": "transfer-default", "Error": "Lambda.Timeout"},
      {"NextAction": "transfer-default", "Error": "Lambda.GenericError"}
    ]
  }
}
```

**Critical fields:**
- `FunctionARN`: ARN of the Lambda function (cross-account is
  supported but requires the Lambda resource policy).
- `InvocationTimeLimitSeconds`: max wait for Lambda response
  (default 5s; max 60s). If the Lambda exceeds this, Connect fires
  the `Lambda.Timeout` exception.
- `Transitions.Exceptions`: graceful fallback for each error type.
  Without exceptions, a Lambda failure traps the contact in the flow.

## Lambda resource policy

Connect invokes Lambda via the `connect.amazonaws.com` service
principal. The Lambda function MUST have a resource policy granting
this principal invoke permission.

```bash
aws lambda add-permission \
  --function-name lookup-customer \
  --statement-id connect-invoke \
  --action lambda:InvokeFunction \
  --principal connect.amazonaws.com \
  --source-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID"
```

**Without this policy:** the InvokeLambda block returns
`Lambda.AccessDenied` at run time. The flow creates successfully
(API does not validate Lambda policies at create-time), but every
contact that hits the block fails.

Verify the policy:

```bash
aws lambda get-policy --function-name lookup-customer
# Look for: "Principal": {"Service": "connect.amazonaws.com"}
```

## Lambda event payload

Connect sends a JSON event to the Lambda function with the
following structure:

```json
{
  "Name": "ContactFlowEvent",
  "Details": {
    "ContactData": {
      "Attributes": {"key1": "value1"},
      "Channel": "VOICE",
      "ContactId": "abc-123",
      "CustomerEndpoint": {"Address": "+18005551234", "Type": "TELEPHONE_NUMBER"},
      "SystemEndpoint": {"Address": "+12065557890", "Type": "TELEPHONE_NUMBER"},
      "InstanceId": "inst-abc123",
      "MediaType": "AUDIO"
    },
    "Parameters": {"param1": "value1"}
  }
}
```

**Common fields used:**
- `CustomerEndpoint.Address`: caller phone number (E.164).
- `Attributes`: contact attributes set earlier in the flow.
- `Parameters`: parameters passed from the InvokeLambda block.

## Lambda response

The Lambda returns JSON. Top-level keys become contact attributes
(retrievable via `$.External.<key>` in subsequent flow blocks).

```python
import json

def lambda_handler(event, context):
    phone = event['Details']['ContactData']['CustomerEndpoint']['Address']
    # Business logic: look up customer by phone
    customer = lookup_customer(phone)
    return {
        'customer_id': customer['id'],
        'loyalty_tier': customer['tier'],
        'Name': customer['name'],
        'department': route_call(customer['tier'])
    }
```

In subsequent flow blocks, reference these via:
- `$.External.customer_id`
- `$.External.loyalty_tier`
- `$.External.department`

## Exception handling

Lambda invocations can fail in three ways:

| Exception | Cause | Mitigation |
|---|---|---|
| `Lambda.AccessDenied` | Lambda resource policy missing or wrong principal | Add permission via `aws lambda add-permission` |
| `Lambda.Timeout` | Lambda exceeded InvocationTimeLimitSeconds | Increase the limit, or optimize Lambda (warm starts, caching) |
| `Lambda.GenericError` | Lambda threw an exception (e.g., DB connection failed) | Add try/except in Lambda, return a default response |

**Always handle all three.** Without exceptions, the contact is
trapped in the flow with no graceful fallback.

## Terraform example

```hcl
resource "aws_connect_contact_flow" "main" {
  instance_id = aws_connect_instance.main.id
  name        = "inbound-main-flow"
  type        = "CONTACT_FLOW"
  description = "Main inbound flow with Lambda lookup"

  content = jsonencode({
    Version      = "2024-07-30"
    StartAction  = "start"
    Actions = [
      { Identifier = "start", Type = "Branch", Parameters = {}, Transitions = { NextAction = "lookup-customer" } },
      {
        Identifier = "lookup-customer"
        Type       = "Action"
        Parameters = {
          FunctionARN                = aws_lambda_function.lookup_customer.arn
          InvocationTimeLimitSeconds = "5"
        }
        Transitions = {
          NextAction = "play-greeting"
          Exceptions = [
            { NextAction = "transfer-default", Error = "Lambda.AccessDenied" },
            { NextAction = "transfer-default", Error = "Lambda.Timeout" }
          ]
        }
      },
      { Identifier = "end", Type = "Terminal", Parameters = { Disconnect = true } }
    ]
  })
}

# Lambda permission for Connect
resource "aws_lambda_permission" "connect_invoke" {
  statement_id  = "connect-invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lookup_customer.function_name
  principal     = "connect.amazonaws.com"
  source_arn    = aws_connect_instance.main.arn
}
```

## Common flow-authoring pitfalls

1. **Dangling resource references.** A flow referencing a non-
   existent queue, Lambda, or Lex bot creates successfully but fails
   at run time. Pre-flight check every referenced resource.

2. **Missing Lambda resource policy.** Without the policy granting
   `connect.amazonaws.com`, InvokeLambda returns AccessDenied at run
   time. The flow API does not validate Lambda policies at create
   time.

3. **No exception handling on InvokeLambda.** Lambda can fail with
   AccessDenied, Timeout, or GenericError. Without exception
   transitions, the contact is trapped.

4. **Using Lex V1 in new flows.** Lex V1 is on a deprecation path.
   Use Lex V2 via the InvokeAmazonLex block (different block name
   and parameters).

5. **Workflow type mismatch.** Contact flows have types
   (CONTACT_FLOW, CUSTOMER_QUEUE, CUSTOMER_HOLD, etc.). Each type
   fires at a specific contact lifecycle stage. Mismatched types
   cause the flow to never run.

6. **Flow content too large.** The flow content JSON has a size
   limit (256 KB). Large flows with many blocks may exceed this.
   Split into multiple flows and use TransferToFlow.

7. **Contact attributes vs External attributes.** `$.Attributes.X`
   is for attributes set via SetAttributes.
   `$.External.X` is for attributes returned by Lambda. Mixing them
   up produces null values.
