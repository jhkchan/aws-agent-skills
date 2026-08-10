# Eval prompt: document-script-error

Diagnose the following SSM association document execution failure.
Emit the standard DIAGNOSIS block.

Diagnosis reference: document-script-error
Account: 111111111111
Region: us-east-1
Association-id: 345678901abcdef345678901abcdef345678901abcdef3
Association name: nightly-config-apply
Instance-id: i-0bbb222ddd333eee4
Execution-id: 11112222-3333-4444-5555-666677778888
Symptom: DocumentError (script fails mid-run)

Recent diagnostic output:
- describe-association-executions Status=Success (orchestration
  succeeded)
- describe-association-execution-targets: per-target
  Status=Failed, StatusMessage="Plugin errors occurred",
  OutputSource.S3Url=s3://ssm-output-prod/i-0bbb222ddd333eee4/...
- S3 output stderr excerpt: "line 42: jq: command not found"
- describe-document: PlatformTypes=[Linux,macOS],
  DefaultVersion=3, association pinned to DefaultVersion=2
- Instance has jq NOT installed (verified via Run Command).

Emit the standard DIAGNOSIS block. Identify the root cause via
the document-level drill-down (Step 6).
