# Eval prompt: ec2-propagation-gap

Design a tag compliance audit for the following setup and identify any
gaps. Emit the standard COMPLIANCE block.

Design reference: ec2-propagation-gap
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Account: 111111111111
Region: us-east-1

Required tags: Environment, Owner, Project.
Target resource types: EC2 instances.
Auto-tagger: deployed on RunInstances, stamps Environment and Owner on
the instance only.
Propagation: NOT configured (EBS volumes and ENIs remain untagged).
Cost allocation tags: active.
