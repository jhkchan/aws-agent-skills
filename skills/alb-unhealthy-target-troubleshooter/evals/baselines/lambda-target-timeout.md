# Baseline (no-skill) response: lambda-target-timeout

---

Your Lambda target group is unhealthy. The Lambda function is timing
out. Check if the function is working correctly by looking at its
CloudWatch logs. The function has a 3-second timeout which might be
too short.

Try increasing the Lambda timeout to 10 or 15 seconds. Also check if
the database query inside the function is optimized. If the health
check is hitting the same code path as real requests, you might want
to create a separate lightweight health check endpoint.

Make sure the Lambda function returns a 200 status code for health
check requests.
