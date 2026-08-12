# Baseline (no-skill) response: visibility-timeout-exceeded

---

Your SQS DLQ is filling with messages. Since the Lambda has zero errors
and the messages are valid, the issue might be with the queue
configuration. The visibility timeout is 30 seconds, which might be too
short. Try increasing it. Also check if there are duplicate messages in
the DLQ — that could indicate the messages are being received multiple
times.

You might also want to increase the Lambda timeout or optimize the
image processing to be faster.
