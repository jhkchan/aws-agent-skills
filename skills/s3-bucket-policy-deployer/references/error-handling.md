# Error Handling — S3 Bucket Policy Deployer

Load-on-demand failure scenarios moved verbatim from SKILL.md.

## Error handling

**`MalformedPolicy` at put-bucket-policy:** policy JSON is invalid
or exceeds 20 KB. Validate with `python3 -m json.tool` and
`wc -c`. If over 20 KB, use Access Points to delegate per-team
policies.

**Policy applied but access still denied:** check Block Public
Access (`RestrictPublicBuckets` silently blocks public policies).
Check the IAM policy of the caller — a Deny there overrides any
bucket policy Allow. Verify the `Resource` includes both bucket and
object ARNs.

**`aws:SourceVpce` condition not matching:** the request is not
going through the specified VPC endpoint. Verify the endpoint ID.
Direct internet requests do NOT have `aws:SourceVpce` set.

**CloudFront OAC returning 403:** the `AWS:SourceArn` condition
does not match the distribution ARN. Verify the distribution ID.
Ensure the OAC config exists in CloudFront.

**Cross-account access denied despite policy:** the foreign
account's IAM role must ALSO have an Allow policy. Both sides must
allow. Verify the role's trust policy and permissions.
