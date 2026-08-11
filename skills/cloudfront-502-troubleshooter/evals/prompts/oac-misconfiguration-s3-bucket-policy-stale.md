# Eval prompt: oac-misconfiguration-s3-bucket-policy-stale

Diagnose the CloudFront 502 failure for the following distribution. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `d333333cdefgh0.cloudfront.net` returns HTTP 502 to all
viewers fetching `/assets/*` since 11:00 UTC. The team migrated from
Origin Access Identity (OAI) to Origin Access Control (OAC) yesterday.

```text
DistributionId: E3QW3R4Y5Z6A7C
DomainName: d333333cdefgh0.cloudfront.net
Origin: oac-misconfiguration-s3-bucket-policy-stale.s3.us-east-1.amazonaws.com
OriginAccessControlId: E3A4B5C6D7E8F9
SigningBehavior: always

curl https://d333333cdefgh0.cloudfront.net/assets/logo.png
  HTTP/2 502
  x-cache: Error from origin
  x-amz-cf-id: <redacted>

aws cloudfront list-origin-access-controls output:
  - Id: E3A4B5C6D7E8F9
    OriginAccessControlConfig:
      Name: oac-misconfiguration-s3-bucket-policy-stale
      OriginAccessControlOriginType: s3
      SigningBehavior: always
      SigningProtocol: sigv4

aws s3api get-bucket-policy --bucket \
  oac-misconfiguration-s3-bucket-policy-stale:
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "OldOAI",
        "Effect": "Allow",
        "Principal": {
          "CanonicalUser":
            "a1b2c3d4e5f6...legacy-oai-canonical-user-id..."
        },
        "Action": "s3:GetObject",
        "Resource":
          "arn:aws:s3:::oac-misconfiguration-s3-bucket-policy-stale/*"
      }
    ]
  }

Note: The bucket policy still references the legacy OAI CanonicalUser
principal; it does NOT include the cloudfront.amazonaws.com service
principal or the AWS:SourceArn condition required for OAC.

aws s3api head-object --bucket \
  oac-misconfiguration-s3-bucket-policy-stale --key assets/logo.png
  → 200 OK (object exists)
```

S3 returns 403 to CloudFront's OAC-signed request (bucket policy
principal mismatch); the viewer sees a 502 because the integration
expects a 200-range response for object GETs.
