# Step Actions and Branching — SSM Automation Deployer

Deep reference on SSM Automation step action types, output chaining,
aws:branch conditional routing, and nested runbook invocation. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Action type reference

### aws:executeAwsApi

Calls any AWS API. The most versatile action type.

```yaml
- name: DescribeInstances
  action: aws:executeAwsApi
  inputs:
    Service: ec2
    Api: DescribeInstances
    InstanceIds:
      - "{{ InstanceId }}"
  outputs:
    - Name: CurrentState
      Selector: "$.Reservations[0].Instances[0].State.Name"
      Type: String
    - Name: InstanceCount
      Selector: "$.Reservations[0].Instances | length(@)"
      Type: Integer
```

**Output chaining:** outputs from prior steps are referenced via
`{{ StepName.OutputName }}`. The Selector uses JSONPath syntax.

### aws:invokeLambdaFunction

Invokes a Lambda function with a payload.

```yaml
- name: InvokeRemediation
  action: aws:invokeLambdaFunction
  inputs:
    FunctionName: remediation-handler
    Payload: '{"instanceId": "{{ InstanceId }}", "action": "stop"}'
  outputs:
    - Name: RemediationResult
      Selector: "$.result"
      Type: String
    - Name: StatusCode
      Selector: "$.statusCode"
      Type: Integer
```

**Payload must be valid JSON.** Use JSONPath interpolation for
parameter references within the payload string.

### aws:runInstances

Launches EC2 instances.

```yaml
- name: LaunchInstance
  action: aws:runInstances
  inputs:
    ImageId: "{{ ImageId }}"
    InstanceType: "{{ InstanceType }}"
    MinInstanceCount: 1
    MaxInstanceCount: 1
    IamInstanceProfileName: "EC2-SSM-Profile"
  outputs:
    - Name: InstanceId
      Selector: "$.InstanceIds[0]"
      Type: String
```

**Requires `iam:PassRole` in the execution role** to pass the
instance profile.

### aws:changeInstanceState

Changes the state of EC2 instances.

```yaml
- name: StopInstance
  action: aws:changeInstanceState
  inputs:
    InstanceIds:
      - "{{ InstanceId }}"
    DesiredState: stopped
```

DesiredState values: `running`, `stopped`, `terminated`.

### aws:sleep

Pauses execution for a duration.

```yaml
- name: WaitForStop
  action: aws:sleep
  inputs:
    Duration: "PT30S"  # ISO 8601 (30 seconds)
```

Duration uses ISO 8601 format: `PT30S` (30s), `PT5M` (5m),
`PT1H` (1h).

### aws:assertAwsResourceProperty

Asserts that a resource property matches an expected value. Fails the
automation if the assertion does not hold.

```yaml
- name: AssertInstanceStopped
  action: aws:assertAwsResourceProperty
  inputs:
    Service: ec2
    Api: DescribeInstances
    InstanceIds:
      - "{{ InstanceId }}"
    PropertySelector: "$.Reservations[0].Instances[0].State.Name"
    DesiredValues:
      - "stopped"
```

### aws:waitForResourceProperty

Waits until a resource property matches, with polling.

```yaml
- name: WaitForRunning
  action: aws:waitForResourceProperty
  inputs:
    Service: ec2
    Api: DescribeInstances
    InstanceIds:
      - "{{ InstanceId }}"
    PropertySelector: "$.Reservations[0].Instances[0].State.Name"
    DesiredValues:
      - "running"
    PollIntervalSeconds: 10
```

## aws:branch conditional routing

`aws:branch` evaluates conditions and routes to different steps. This
is the ONLY way to implement conditional branching.

### Simple branching

```yaml
- name: BranchOnState
  action: aws:branch
  inputs:
    Choices:
      - NextStep: StopStep
        Condition: "{{ CheckState.CurrentState == 'running' }}"
      - NextStep: StartStep
        Condition: "{{ CheckState.CurrentState == 'stopped' }}"
    Default: NoActionStep
```

### Multi-condition branching with LogicalOperator (2023-2024 feature)

```yaml
- name: BranchOnMultipleConditions
  action: aws:branch
  inputs:
    Choices:
      - NextStep: RemediateStep
        LogicalOperator: And
        Conditions:
          - "{{ CheckState.CurrentState == 'running' }}"
          - "{{ CheckMetrics.CpuUtilization > 90 }}"
      - NextStep: ScaleStep
        LogicalOperator: Or
        Conditions:
          - "{{ CheckState.CurrentState == 'running' }}"
          - "{{ CheckMetrics.MemoryUtilization > 85 }}"
    Default: NoActionStep
```

### Branch routing rules

1. Each Choice must have a `NextStep` that matches a step name in
   `mainSteps`.
2. The `Default` step is taken if no Choice condition matches.
3. A step reached via branch can set `isEnd: true` to terminate.
4. If a branch step is reached without the `nextStep` field, the
   automation continues to the next sequential step after the branch.
5. Conditions use JSONPath interpolation: `{{ StepName.OutputName }}`
   with comparators: `==`, `!=`, `<`, `>`, `<=`, `>=`.

## Nested runbook invocation (aws:executeAutomation)

A runbook can invoke another runbook using `aws:executeAutomation`.

```yaml
- name: InvokeChildRunbook
  action: aws:executeAutomation
  inputs:
    DocumentName: "ChildRemediation"
    RuntimeParameters:
      InstanceId: "{{ InstanceId }}"
      ActionType: "Stop"
  outputs:
    - Name: ChildExecutionId
      Selector: "$.AutomationExecutionId"
      Type: String
```

**Use cases:**
- Decompose large runbooks into reusable components.
- Share common logic across multiple parent runbooks.
- Enable team-specific runbooks that compose shared operations.

## Output chaining rules

Outputs from a step can be referenced by later steps:

```text
Step A:
  outputs:
    - Name: InstanceState
      Selector: "$.State.Name"
      Type: String

Step B (later step):
  inputs:
    SomeField: "{{ A.InstanceState }}"
```

**Rules:**
- Reference format: `{{ StepName.OutputName }}` (no `$` prefix).
- Outputs are available to all subsequent steps, not just the next one.
- Output types: String, Integer, Boolean, StringList, Map.
- Selector uses JSONPath to extract values from the API response.
