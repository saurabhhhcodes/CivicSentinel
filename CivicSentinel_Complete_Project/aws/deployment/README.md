# AWS deployment notes
Local mode requires no AWS credentials. This package does not implement S3 or CloudWatch integration and does not provision AWS resources. For a real deployment, configure private S3 storage, IAM least privilege, HTTPS, monitoring, and a persistent database, then implement and test those integrations before claiming AWS processing. Do not commit secrets.
