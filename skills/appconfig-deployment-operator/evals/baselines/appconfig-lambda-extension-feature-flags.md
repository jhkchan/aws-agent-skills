# Baseline (no-skill) response: appconfig-lambda-extension-feature-flags

This file captures what a generic assistant produces WITHOUT the
appconfig-deployment-operator skill loaded.

---

You can use the AWS SDK in your Lambda function to call
`GetConfiguration` from AppConfig. Here's roughly what the code
looks like:

```python
import boto3
client = boto3.client('appconfig')
response = client.get_configuration(
    Application='checkout-service',
    Environment='prod',
    Configuration='checkout-flags',
    ClientId='checkout-handler'
)
config = response['Configuration'].read()
```

Add the AppConfig extension layer to your function if you want
caching. You'll also need to set some environment variables for
the application and environment names.
