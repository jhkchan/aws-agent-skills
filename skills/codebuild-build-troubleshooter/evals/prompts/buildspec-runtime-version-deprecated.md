# Eval prompt: buildspec-runtime-version-deprecated

Diagnose the CodeBuild build failure for the following project. Walk
the phase-status-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE,
REMEDIATION).

Symptom: project `cb-data-pipeline` started failing after a routine
dependency update. The INSTALL phase fails with YAML_FILE_ERROR before
any buildspec command runs. The buildspec references Python 3.7 which
was deprecated and removed from CodeBuild managed images.

```text
ProjectName: cb-data-pipeline
BuildId: cb-data-pipeline:mno34567
Environment:
  Image: aws/codebuild/amazonlinux2-x86_64-standard:5.0
  PrivilegedMode: false
Buildspec:
  version: 0.2
  phases:
    install:
      runtime-versions:
        python: 3.7
      commands:
        - pip install -r requirements.txt
    build:
      commands:
        - python main.py
Phase details:
  phaseType: INSTALL
  phaseStatus: FAILED
  contexts[0].statusCode: YAML_FILE_ERROR
  contexts[0].message: "Phase context status code: YAML_FILE_ERROR
    Message: Unknown runtime version"
```

The buildspec YAML is structurally valid (correct indentation, valid
structure). The issue is that Python 3.7 has been removed from
CodeBuild managed images and is no longer a supported runtime version.
