# Baseline (no-skill) response: sequence-token-collision-shared-stream

---

You're getting `InvalidSequenceTokenException` because CloudWatch Logs
requires the correct sequence token on each PutLogEvents call. The
token comes from the previous successful write to the same log
stream. You may be caching an old token or have multiple writers
sharing a stream.

Try refreshing the token before each write by calling
`DescribeLogStreams` to get the current `uploadSequenceToken`. If you
have multiple processes writing to the same stream, give each one its
own stream name.
