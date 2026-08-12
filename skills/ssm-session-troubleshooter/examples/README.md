# Example usage: ssm-session-troubleshooter

A walkthrough showing the skill diagnosing a Session Manager session
timeout that mimics an IAM failure, demonstrating the symptom-to-layer
triage, the "Online but sessions fail" decision (the data channel is
a separate plane from the control channel), the evidence-backed
ROOT_CAUSE_IDENTIFIED verdict, and the missing `ssmmessages` VPC
endpoint root cause.

## Input (user prompt)

> Our EC2 instance `i-private-1` in a private subnet is Online in
> SSM, but every Session Manager session times out within 10 seconds.
> We've been debugging this as an IAM issue for an hour — please
> help us find the actual root cause.

```text
InstanceId: i-private-1
PlatformName: Amazon Linux
AgentVersion: 3.2.1546.0 (newer than 3.0.196)
PingStatus: Online
LastPingDateTime: 2026-08-11T20:55:00Z (current)

InstanceProfile role EC2-SSM-Role has:
  - AmazonSSMManagedInstanceCore (attached)
  - Inline policy grants s3:PutObject on the session bucket
simulate-principal-policy on EC2-SSM-Role for
  ssmmessages:OpenDataChannel: Decision: allowed
  ssmmessages:CreateDataChannel: Decision: allowed
  ssm:StartSession: Decision: allowed

VPC: vpc-priv (no internet gateway, no NAT gateway). The instance
  is in a private subnet only.
VPC endpoints configured in vpc-priv:
  - com.amazonaws.us-east-1.ssm (Interface, State: Available)
  - com.amazonaws.us-east-1.ec2messages (Interface, Available)
VPC endpoints MISSING:
  - com.amazonaws.us-east-1.ssmmessages (NOT FOUND)

Endpoint security groups: allow 443 inbound from the instance
  subnet CIDR. Egress on the instance SG: 443 to the subnet CIDR.
Private DNS on the existing endpoints: Enabled.

Agent log (on-instance):
  "TimeoutError: failed to open data channel on
  ssmmessages.us-east-1.amazonaws.com after 10s retries"
  "408 RequestTimeout dialing
  ssmmessages.us-east-1.amazonaws.com"

Session document: SSM-SessionManagerRunShell (default,
  DocumentType: Session, SchemaVersion: 1.0).
```

## Skill output

```text
TARGET: i-private-1 (session document: SSM-SessionManagerRunShell)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The instance is Online (control channel works via the ssm
  endpoint) but the session data channel cannot reach
  ssmmessages.us-east-1.amazonaws.com because the VPC is missing
  the com.amazonaws.us-east-1.ssmmessages interface endpoint. The
  agent log shows "408 RequestTimeout dialing
  ssmmessages.us-east-1.amazonaws.com" and the instance resolves
  the public IP (no private DNS override for ssmmessages because
  the endpoint does not exist). IAM is correct — all ssmmessages:*
  actions are allowed on the instance role (Step 3).
LAYER: VPC_ENDPOINT_MISSING
EVIDENCE:
  - Symptom: every session starts on the caller side ("Starting
    session with SessionId: botocore-...") then times out within
    10 seconds with "Your session started, but then timed out
    while waiting for the instance to start streaming."
  - Probe: aws ec2 describe-vpc-endpoints --filters
    Name=vpc-id,Values=vpc-priv returns endpoints for ssm and
    ec2messages but NO entry for ssmmessages. The ssmmessages
    endpoint is absent.
  - Probe: agent log shows "408 RequestTimeout dialing
    ssmmessages.us-east-1.amazonaws.com after 10s retries" — the
    data-channel DNS resolves to the public IP (no private DNS
    override without the endpoint), and the no-egress VPC cannot
    reach it.
  - Passing: aws iam simulate-principal-policy on EC2-SSM-Role
    returns Decision: allowed for ssmmessages:OpenDataChannel,
    ssmmessages:CreateDataChannel, ssm:StartSession (IAM is not
    the cause).
  - Passing: PingStatus: Online with current LastPingDateTime
    confirms the ssm endpoint works (control channel is healthy).
  - Passing: AgentVersion 3.2.1546.0 is above the 3.0.196
    threshold for Session Manager and port forwarding (agent is
    not outdated).
  - Passing: endpoint security groups allow 443 inbound from the
    instance subnet CIDR (the existing endpoints are reachable;
    the ssmmessages endpoint simply does not exist).
REMEDIATION:
  1. Create the missing ssmmessages interface endpoint:

     aws ec2 create-vpc-endpoint --vpc-id vpc-priv \
       --vpc-endpoint-type Interface \
       --service-name com.amazonaws.us-east-1.ssmmessages \
       --subnet-ids <private-subnet-id> \
       --security-group-ids <endpoint-sg-id> \
       --private-dns-enabled --output json

  2. Verify the endpoint's security group allows 443 inbound from
     the instance subnet CIDR (same SG as the ssm/ec2messages
     endpoints).

  3. Verify private DNS is enabled on the new endpoint so the
     instance resolves ssmmessages.us-east-1.amazonaws.com to the
     private endpoint IP.

  4. Wait ~30 seconds for the agent to re-attempt the data channel,
     then start a new session:

     aws ssm start-session --target i-private-1

CONFIRM: Before creating the endpoint, emit and await:
  "CONFIRM: About to create an ssmmessages interface VPC endpoint
   in vpc-priv (~$0.01/hour). Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished data-channel failure from IAM failure.** A
   generic assistant says "check the IAM role permissions." The
   skill recognises that the instance is Online (control channel
   works) and that the session starts on the caller side (caller's
   `ssm:StartSession` is fine) — the failure is on the data channel,
   which is a separate plane carried over `ssmmessages`.

2. **Identified the specific missing endpoint.** The skill probes
   `describe-vpc-endpoints` and identifies that `ssm` and
   `ec2messages` are present but `ssmmessages` is absent. The
   "added the SSM endpoint" reflex most operators have adds only
   the `ssm` endpoint and misses the data-channel endpoint.

3. **Confirmed via the agent log signature.** The "408
   RequestTimeout dialing ssmmessages.us-east-1.amazonaws.com" log
   line is the smoking gun for a missing `ssmmessages` endpoint in
   a no-egress VPC. A generic assistant does not know to look for
   this specific log line.

4. **Ruled out IAM with an authoritative probe.**
   `simulate-principal-policy` returns `allowed` for all
   `ssmmessages:*` actions. The skill uses the simulation result
   rather than eyeballing the JSON.

5. **Recommended the endpoint creation, not a role-policy edit.**
   The primary remediation is creating the `ssmmessages` interface
   endpoint. Editing the role (a common reflex) would not help
   because IAM is already correct.

## Slash-command invocation

```
/aws:troubleshoot-ssm-session
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why i-private-1 SSM sessions time out"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: ssm-session-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate that sessions succeed:

```bash
# Confirm the new endpoint is Available
aws ec2 describe-vpc-endpoints --filters \
  Name=vpc-id,Values=vpc-priv Name=service-name,Values=com.amazonaws.us-east-1.ssmmessages \
  --query 'VpcEndpoints[0].[State,PrivateDnsEnabled]' --output text \
  --profile default

# Start a test session
aws ssm start-session --target i-private-1 --profile default

# Confirm the agent no longer logs ssmmessages timeouts
aws logs filter-log-events \
  --log-group-name /aws/ssm/i-private-1/amazon-ssm-agent \
  --start-time $(date -d '-5 minutes' +%s)000 \
  --filter-pattern '"ssmmessages" OR "RequestTimeout"' \
  --profile default --output json
```

Then monitor the instance's `PingStatus` for 1-2 hours to confirm
the instance stays Online and sessions remain stable.
