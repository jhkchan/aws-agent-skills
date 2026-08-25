# Worked Examples — Lambda Runtime Deprecation Auditor

Formal input schema and output examples moved verbatim from SKILL.md.
Load on demand.

### Input schema (formal) — live-account and offline-classification modes


The auditor accepts either a function name/ARN (live-account mode) or a
configuration object (offline-classification mode).

**Live-account mode** — provide the function identifier:

```json
{
  "function_identifier": "my-lambda-function",
  "account_id": "123456789012",
  "region": "us-east-1"
}
```

**Offline-classification mode** — provide the configuration object as
returned by `aws lambda get-function-configuration --output json`:

```json
{
  "function_name": "my-lambda-function",
  "runtime": "python3.9",
  "package_type": "Zip",
  "architectures": ["x86_64"],
  "role_arn": "arn:aws:iam::123456789012:role/my-exec-role",
  "attached_policies": [
    {"type": "managed", "name": "AWSLambdaBasicExecutionRole"},
    {"type": "inline", "name": "my-inline", "document": {"Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}}
  ],
  "tracing_config": {"Mode": "PassThrough"},
  "dead_letter_config": null,
  "reserved_concurrent_executions": null,
  "function_url_config": {"AuthType": "NONE"},
  "resource_based_policy": null,
  "last_modified": "2025-03-15T10:00:00.000Z",
  "event_source_mappings": [],
  "triggers": ["eventbridge"]
}
```

**Required fields for offline mode:** `function_name`, `runtime`,
`package_type`, `role_arn`, `attached_policies`, `tracing_config`.
All others are optional but recommended for a complete audit.
