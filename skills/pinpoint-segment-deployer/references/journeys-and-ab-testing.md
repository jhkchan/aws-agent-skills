# Journeys and A/B Testing — Pinpoint Segment Deployer

Deep reference on journey activities (ENTRY, SEND, WAIT,
CONDITIONAL_SPLIT, MULTIVARIATE_SPLIT, RANDOM_SPLIT, CONTROL, END),
the WaitTime requirement on event-conditional splits, journey DAG
validation, A/B test design with AdditionalTreatments and
HoldoutPercent, and the sample-size heuristic for MDE. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Journey activity model

A journey is a directed acyclic graph (DAG) of activities. Each
activity (except END) has a `NextActivity` referencing the next
activity by ID.

| Activity type | Purpose | Branches |
|---|---|---|
| ENTRY | Journey entry condition (event-based, segment-based, or dynamic) | → NextActivity |
| SEND | Send a message on a channel (email, SMS, push, voice) | → NextActivity |
| WAIT | Wait for a duration (time-based) or until an event (event-based, with optional timeout) | → NextActivity (or event-conditional) |
| CONDITIONAL_SPLIT | Yes/No branch on event or attribute | → TrueActivity / FalseActivity |
| MULTIVARIATE_SPLIT | Percentage-based A/B/C/... branches | → N branches (each with percentage) |
| RANDOM_SPLIT | Equal percentage split (simplified multivariate) | → N branches (equal percentages) |
| CONTROL | Holds endpoint out of messaging (holdout, used in A/B tests inside journeys) | → NextActivity |
| END | Terminal | (none) |

## Journey DAG validation

Pinpoint validates the journey at create-time. The validation rules:

1. **At least one ENTRY activity.** A journey without an ENTRY has
   no way for endpoints to enter.
2. **Every activity (except END) has a `NextActivity`.** Activities
   without `NextActivity` trap endpoints.
3. **No cycles.** The activity graph must be a DAG. Loops cause
   infinite journeys.
4. **At least one END activity.** Without END, all paths are open.
5. **CONDITIONAL_SPLIT has both `TrueActivity` and `FalseActivity`.**
   Missing either side traps endpoints.
6. **MULTIVARIATE_SPLIT branch percentages sum to 100.** Otherwise
   create-journey errors.

## CONDITIONAL_SPLIT — the WaitTime requirement

The `CONDITIONAL_SPLIT` evaluates an event or attribute and routes
endpoints down the YES or NO branch. The most common failure mode
is missing `WaitTime` on event conditions.

```json
{
  "Identifier": "purchase-split",
  "Type": "CONDITIONAL_SPLIT",
  "CONDITIONAL_SPLIT": {
    "Condition": {
      "Conditions": [{
        "EventCondition": {
          "Dimensions": {
            "Event": {"EventType": {"DimensionType": "INCLUSIVE", "Values": ["purchase"]}}
          },
          "MessageActivity": "purchase-thanks"
        }
      }],
      "Operator": "ALL"
    },
    "FalseActivity": "still-interested",
    "TrueActivity": "purchase-thanks"
  }
}
```

**Without `WaitTime` (or `evaluateLater`):** the split evaluates
once at the moment the endpoint reaches the activity. If the event
has not occurred yet, the endpoint routes to NO immediately. This
is rarely what the designer wants.

**With `WaitTime`:** the journey waits for the event up to the
specified duration. If the event occurs within the wait window,
the endpoint routes to YES. If the event does not occur, the
endpoint times out and routes to NO.

```json
"WAIT": {
  "WaitFor": "PT7D",
  "NextActivity": "purchase-split"
}
```

(Put a WAIT activity before the CONDITIONAL_SPLIT to gate the
evaluation window.)

## MULTIVARIATE_SPLIT — A/B/C branches inside journeys

`MULTIVARIATE_SPLIT` divides endpoints across branches by
percentage. Useful for A/B/C testing inside journeys.

```json
{
  "Identifier": "ab-test",
  "Type": "MULTIVARIATE_SPLIT",
  "MULTIVARIATE_SPLIT": {
    "Branches": [
      {"Percentage": 50, "NextActivity": "discount-email"},
      {"Percentage": 30, "NextActivity": "nudge-email"},
      {"Percentage": 20, "NextActivity": "control-group"}
    ]
  }
}
```

Branch percentages must sum to 100. The CONTROL branch holds
endpoints out of messaging — useful for measuring the treatment
effect vs no-message baseline.

## RANDOM_SPLIT — equal-percentage split

`RANDOM_SPLIT` is a simplified `MULTIVARIATE_SPLIT` with equal
percentages. Useful for holdouts.

```json
{
  "Identifier": "holdout",
  "Type": "RANDOM_SPLIT",
  "RANDOM_SPLIT": {
    "Branches": [
      {"Percentage": 80, "NextActivity": "send-message"},
      {"Percentage": 20, "NextActivity": "control"}
    ]
  }
}
```

## A/B testing in campaigns (AdditionalTreatments + HoldoutPercent)

Campaign-level A/B tests use `AdditionalTreatments` (additional
message configs) and `HoldoutPercent` (control group).

| Element | Purpose | Constraint |
|---|---|---|
| Default message | Treatment A | Implicit (the campaign's MessageConfiguration) |
| `AdditionalTreatments` | Treatments B, C, ... | Each has distinct template + SizePercent |
| `HoldoutPercent` | Control group | 0-100; SizePercent for control |

**Sum rule:** DefaultTreatment SizePercent (implicit) +
AdditionalTreatments SizePercents + HoldoutPercent = 100.

```json
{
  "Name": "subject-line-ab",
  "HoldoutPercent": 20,
  "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-a"}}},
  "AdditionalTreatments": [
    {"Id": "treatment-b", "SizePercent": 40, "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-b"}}}},
    {"Id": "treatment-c", "SizePercent": 20, "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-c"}}}},
    {"Id": "treatment-d", "SizePercent": 20, "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-d"}}}}
  ]
}
```

Default 20 + treatment-b 40 + treatment-c 20 + treatment-d 20 +
holdout 20 = 100. (Wait, that's 120 — incorrect. Let me recalculate:
default is implicit; with holdout 20, additional treatments
40+20+20 = 80, plus default = 100, so default = 0... that doesn't
work either. Let me clarify: the default SizePercent is the
remainder: 100 - holdout - sum(AdditionalTreatments). So with
holdout 20 + additional 40+20+20 = 100, default = -20, which is
invalid. Correct example below.)

**Correct example:**

```json
{
  "Name": "subject-line-ab",
  "HoldoutPercent": 20,
  "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-a"}}},
  "AdditionalTreatments": [
    {"Id": "treatment-b", "SizePercent": 40, "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-b"}}}},
    {"Id": "treatment-c", "SizePercent": 20, "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-c"}}}}
  ]
}
```

Default 20 (implicit: 100 - 20 - 60) + treatment-b 40 + treatment-c
20 + holdout 20 = 100. Valid.

## Sample-size heuristic for MDE

The sample size must support the minimum detectable effect (MDE).
Underpowered tests produce noise.

| MDE | Endpoints per treatment (rule of thumb) |
|---|---|
| 1% or less | ≥ 10,000 |
| 2-3% | ≥ 5,000 |
| 5% or more | ≥ 1,000 |
| 10%+ | ≥ 300 |

Rule-of-thumb basis: α=0.05, β=0.20 (80% power), two-sided test.
For rigorous power analysis, use a sample-size calculator.

**Gate logic (apply before emitting create-campaign):**

```text
segment_size = get-segment-estimate(segment_id)
treatment_count = 1 + len(AdditionalTreatments)  # default + treatments
endpoints_per_treatment = segment_size * (1 - holdout_percent/100) / treatment_count

if MDE ≤ 1% and endpoints_per_treatment < 10000: FAIL
elif MDE 2-3% and endpoints_per_treatment < 5000: FAIL
elif MDE ≥ 5% and endpoints_per_treatment < 1000: FAIL
else: PASS
```

**On failure:** emit PREREQUISITES_MISSING with a recommendation to
either (a) reduce the number of treatments, (b) accept a higher
MDE, or (c) hold out a smaller control group.

## Terraform journey example

```hcl
resource "aws_pinpoint_journey" "onboarding" {
  application_id    = aws_pinpoint_app.main.application_id
  name              = "onboarding-7d"
  state_machine {
    start_activity = "entry"
    activities {
      identifier   = "entry"
      entry {}
      next_activity = "send-welcome"
    }
    activities {
      identifier   = "send-welcome"
      send {
        message_config {
          email_config {
            template_information { name = "welcome-email" }
          }
        }
      }
      next_activity = "wait-3d"
    }
    activities {
      identifier   = "wait-3d"
      wait { wait_for = "PT3D" }
      next_activity = "purchase-split"
    }
    activities {
      identifier   = "purchase-split"
      conditional_split {
        condition { /* purchase event */ }
        true_activity  = "purchase-thanks"
        false_activity = "still-interested"
      }
    }
    activities {
      identifier = "end"
      end {}
    }
  }
}
```

## Common journey pitfalls

1. **CONDITIONAL_SPLIT without WaitTime on event conditions.**
   Endpoints route to NO immediately if the event has not yet
   occurred. Always put a WAIT activity before the split to gate the
   evaluation window.

2. **MULTIVARIATE_SPLIT percentages don't sum to 100.** create-
   journey errors. Verify the sum before emitting the CLI.

3. **Open paths (no END).** Every path must reach END. The journey
   validator catches this at create-time, but it's worth pre-
   validating.

4. **Same template across A/B treatments.** Identical templates
   produce identical results — the test measures noise. Each
   treatment MUST have a distinct template.

5. **Underpowered A/B test.** Sample size below the MDE threshold
   produces noise. Apply the sample-size gate before creating the
   campaign.

6. **CONTROL branch treated as a treatment.** CONTROL holds
   endpoints out of messaging. It's the baseline, not a treatment.
   Measure treatment effect against CONTROL.
