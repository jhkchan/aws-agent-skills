# Baseline (no-skill) response: multi-region-olap-ready

This file captures what a generic assistant produces WITHOUT the
s3-object-lambda-deployer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, per-region prerequisite
verification, concurrency per region, post-deploy verification per
region, WriteGetObjectResponse check per Lambda).

---

Here's how to set up multi-region Object Lambda:

```bash
for REGION in us-east-1 eu-west-1 ap-southeast-2; do
  aws s3control create-access-point-for-object-lambda \
    --account-id 111111111111 --name global-pii-olap --region $REGION \
    --configuration SupportingAccessPoint=arn:aws:s3:$REGION:111111111111:accesspoint/dlake-ap-$REGION

  aws s3control put-access-point-configuration-for-object-lambda \
    --account-id 111111111111 --name global-pii-olap --region $REGION \
    --configuration '{"TransformationConfigurations":[{"Actions":["GetObject"],"ContentTransformation":{"AwsLambda":{"FunctionArn":"arn:aws:lambda:'"$REGION"':111111111111:function:pii-redact-'"$REGION"'"}}}]}'
done
```

Set up Route 53 latency-based routing to direct clients to the nearest
OLAP ARN. Each region handles its own data independently.
