# Error Handling — VPC Endpoint Policy Troubleshooter

Symptom-to-layer error-handling playbook moved out of the SKILL.md body. Loaded on demand.

## Error handling — symptom to layer playbook

### Connection timeout (no response from endpoint)
- Layer 1: Check the endpoint's security group for inbound rules from
  the client subnet on the service port. This is the #1 cause.
- Layer 6: If SG is correct, check the NLB target health (for custom
  endpoint services). Unhealthy targets cause timeouts.
- Layer 9: Verify the endpoint state is `available` (not
  `pending-waiting` or `failed`).

### HTTP 403 Access Denied from endpoint
- Layer 2: Check the endpoint policy. It may deny the requested action
  or principal. The policy is a SEPARATE layer from IAM.
- IAM: Verify the caller's IAM policy also allows the action. Both IAM
  and endpoint policy must allow.
- Layer 5: For cross-account, check the provider's endpoint service
  resource policy. The consumer account must be in the allowed
  principals.

### DNS does not resolve endpoint name
- Layer 3: Check if private DNS is enabled for the endpoint (AWS
  services). If not, enable it.
- Layer 3: For non-AWS services, check if a Route 53 private hosted zone
  is associated with the VPC.
- Verify the VPC has `enableDnsSupport` and `enableDnsHostnames` set to
  true.

### S3/DynamoDB traffic not using Gateway endpoint
- Layer 4: Check if the Gateway endpoint is in the route table for the
  affected subnet(s). Add it if missing.
- Verify the endpoint state is `available`.

### Endpoint policy update fails
- Layer 8: Validate the JSON syntax. Common errors are trailing commas,
  missing brackets, and invalid principal values.
- Use `python3 -m json.tool` or `jq` to validate before applying.
