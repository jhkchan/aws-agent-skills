# Error Handling — ALB 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

### For TARGET_HEALTH_CHECK — wrong health check configuration

1. Identify the correct health check endpoint (an application route that
   returns 200 when healthy):
   ```bash
   ssh <bastion> "curl -v http://<target-ip>:<port><candidate-path>"
   # Test multiple paths: /health, /healthz, /ready, /status
   ```
2. Update the health check configuration:
   ```bash
   aws elbv2 modify-target-group --target-group-arn <tg-arn> \
     --health-check-path /healthz \
     --matcher HttpCode=200,204 \
     --profile <p>
   ```
3. Wait for `healthy_threshold_count` consecutive successful checks.
4. Verify: `describe-target-health` shows `healthy`.

### For TARGET_SG_BLOCKED — target SG does not allow ALB SG

1. Add an inbound rule to the target SG:
   ```bash
   aws ec2 authorize-security-group-ingress --group-id <sg-target> \
     --protocol tcp --port <target-port> \
     --source-security-group-id <sg-alb> --profile <p>
   ```
2. Verify: `curl` from the ALB subnet to the target on the target port.

### For TARGET_NONE_HEALTHY — no registered targets

1. Register targets:
   ```bash
   aws elbv2 register-targets --target-group-arn <tg-arn> \
     --targets Id=<i-id>,Port=<port> --profile <p>
   ```
2. Wait for health checks to pass.
3. Verify: `describe-target-health` shows `healthy`.

### For TARGET_TIMEOUT — target exceeding idle timeout

1. Raise the idle timeout (if the workload legitimately needs it):
   ```bash
   aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
     --attributes Key=idle_timeout.timeout_seconds,Value=120 \
     --profile <p>
   ```
2. Or migrate to an async pattern for long-running requests.

### For TARGET_INVALID_RESPONSE — target returning malformed HTTP

1. Test the target directly to identify the malformed response:
   ```bash
   ssh <bastion> "curl -v http://<target-ip>:<port>/"
   ```
2. Fix the target application (HTTP server crash, wrong port, SSL
   configuration).
3. Verify: the target returns a valid HTTP response.

### For DEREGISTRATION_STUCK — targets stuck in draining

1. Register new targets to replace the draining ones.
2. Optionally reduce the deregistration delay:
   ```bash
   aws elbv2 modify-target-group-attributes --target-group-arn <tg-arn> \
     --attributes Key=deregistration_delay.timeout_seconds,Value=30 \
     --profile <p>
   ```

### For WAF_BLOCKED — WAF false positive

1. Identify the blocking rule in WAF logs.
2. Add an exemption or tune the rule:
   ```bash
   aws wafv2 update-web-acl --web-acl-arn <acl-arn> \
     --rules file://updated-rules.json --profile <p>
   ```

### For LISTENER_MISCONFIGURED — wrong target group or priority

1. Update the listener rule:
   ```bash
   aws elbv2 modify-rule --rule-arn <rule-arn> \
     --actions Type=forward,TargetGroupArn=<correct-tg-arn> --profile <p>
   ```

### For ESCALATE — AWS-side incident

1. Surface the AWS Health event ARN and load balancer ARN.
2. Open a Support case with the time window and access-log evidence.
