# Eval prompt: ecr-image-cross-account-policy

Diagnose the Lambda invocation failure for the following function. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-ecr-image-cross-account-policy` fails to initialise on
every cold start. Logs show `ImagePullFailure: Image
111111111111.dkr.ecr.us-east-1.amazonaws.com/fn-images:latest not
found` — but the image EXISTS in the source account. The function is
in account `222222222222`; the ECR repo is in account `111111111111`.

```text
FunctionName: fn-ecr-image-cross-account-policy
Qualifier: prod (version 3)
PackageType: Image
Code:
  ImageUri: 111111111111.dkr.ecr.us-east-1.amazonaws.com/fn-images:latest
ImageConfig:
  Command: [app.handler]
Timeout: 30
MemorySize: 1024
Execution role: includes AWSLambdaBasicExecutionRole and a
  cross-account assume-role permission
LastUpdateStatus: Successful (image-config update applied 1 hour ago)

ECR context:
  - Repository: 111111111111.dkr.ecr.us-east-1.amazonaws.com/fn-images
  - Image tag latest exists, image size 450 MB compressed
  - Repository policy:
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Sid": "SameAccountLambda",
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": ["ecr:BatchGetImage",
                       "ecr:GetDownloadUrlForLayer"]
          }
        ]
      }
  - Note: Principal is the Lambda service principal without an
    account condition; cross-account pulls fail.

Recent log pattern (each cold start):
  ImagePullFailure: Image
    111111111111.dkr.ecr.us-east-1.amazonaws.com/fn-images:latest
    not found
  Runtime.ExitError
```

The image exists, the size is under the 10 GB cap, and the
`ImageConfig.Command` matches the image's entry point. The
cross-account ECR repo policy is the cause.
