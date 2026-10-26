import os, logging
from pathlib import Path

logger = logging.getLogger("civicsentinel.aws")

class AWSService:
    """
    AWS Adapter for CivicSentinel:
    - S3 evidence storage with local filesystem fallback
    - SES operational incident dispatch
    - CloudWatch metrics logging
    - Status reporting (LOCAL_MODE, CONFIGURED, CONNECTED)
    """
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_bucket = os.getenv("S3_BUCKET", "")
        self.ses_sender = os.getenv("SES_SENDER_EMAIL", "")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    def get_status(self) -> dict:
        has_creds = bool(self.access_key and self.secret_key) or bool(os.getenv("AWS_PROFILE"))
        
        s3_status = "NOT_CONFIGURED"
        ses_status = "NOT_CONFIGURED"
        cw_status = "NOT_CONFIGURED"
        overall_mode = "LOCAL"

        if not has_creds:
            return {
                "mode": "LOCAL",
                "aws_connected": False,
                "region": self.region,
                "s3": {"status": "LOCAL_STORAGE", "bucket": self.s3_bucket or "local://data/evidence"},
                "ses": {"status": "LOCAL_MOCK_OR_SMTP", "sender": self.ses_sender or "local://mock"},
                "cloudwatch": {"status": "LOCAL_STDOUT_LOGGING"},
                "iam_policy_recommended": self.get_iam_policy_template(),
                "notice": "Operating safely in zero-cost local mode. No AWS credentials detected."
            }

        # If credentials exist, test connectivity safely
        overall_mode = "CONFIGURED"
        try:
            import boto3
            # Check S3
            if self.s3_bucket:
                s3 = boto3.client("s3", region_name=self.region)
                s3.head_bucket(Bucket=self.s3_bucket)
                s3_status = "CONNECTED"
            else:
                s3_status = "MISSING_BUCKET_CONFIG"

            # Check SES
            if self.ses_sender:
                ses = boto3.client("ses", region_name=self.region)
                ses.get_send_quota()
                ses_status = "CONNECTED"
            else:
                ses_status = "MISSING_SES_SENDER"

            # Check CloudWatch
            cw = boto3.client("cloudwatch", region_name=self.region)
            cw.list_metrics(Namespace="CivicSentinel", RecentlyActive="PT3H")
            cw_status = "CONNECTED"

            connected = s3_status == "CONNECTED" or ses_status == "CONNECTED"
            return {
                "mode": "AWS_CONNECTED" if connected else "CONFIGURED",
                "aws_connected": connected,
                "region": self.region,
                "s3": {"status": s3_status, "bucket": self.s3_bucket},
                "ses": {"status": ses_status, "sender": self.ses_sender},
                "cloudwatch": {"status": cw_status},
                "iam_policy_recommended": self.get_iam_policy_template()
            }
        except Exception as e:
            return {
                "mode": "CONFIGURED_BUT_UNREACHABLE",
                "aws_connected": False,
                "region": self.region,
                "error": str(e),
                "s3": {"status": s3_status},
                "ses": {"status": ses_status},
                "cloudwatch": {"status": cw_status},
                "iam_policy_recommended": self.get_iam_policy_template()
            }

    def upload_evidence(self, local_path: Path, remote_key: str) -> str:
        """Upload evidence to S3 if configured; returns URL or local relative path."""
        if self.s3_bucket and self.access_key:
            try:
                import boto3
                s3 = boto3.client("s3", region_name=self.region)
                s3.upload_file(str(local_path), self.s3_bucket, remote_key)
                return f"https://{self.s3_bucket}.s3.{self.region}.amazonaws.com/{remote_key}"
            except Exception as e:
                logger.warning(f"S3 upload failed: {e}. Falling back to local evidence store.")
        return f"/api/evidence/{local_path.name}"

    def emit_metric(self, metric_name: str, value: float, unit: str = "Count", dimensions: list = None):
        """Send operational metric to AWS CloudWatch if configured."""
        if self.access_key:
            try:
                import boto3
                cw = boto3.client("cloudwatch", region_name=self.region)
                cw.put_metric_data(
                    Namespace="CivicSentinel/Infrastructure",
                    MetricData=[{
                        "MetricName": metric_name,
                        "Value": value,
                        "Unit": unit,
                        "Dimensions": dimensions or []
                    }]
                )
            except Exception as e:
                logger.debug(f"CloudWatch metric put skipped: {e}")

    @staticmethod
    def get_iam_policy_template() -> dict:
        """Minimum required IAM least-privilege policy for CivicSentinel AWS deployment."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "CivicSentinelEvidenceS3",
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject"
                    ],
                    "Resource": "arn:aws:s3:::YOUR_CIVICSENTINEL_BUCKET/*"
                },
                {
                    "Sid": "CivicSentinelIncidentSES",
                    "Effect": "Allow",
                    "Action": [
                        "ses:SendEmail",
                        "ses:SendRawEmail"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "CivicSentinelMonitoringCW",
                    "Effect": "Allow",
                    "Action": [
                        "cloudwatch:PutMetricData"
                    ],
                    "Resource": "*"
                }
            ]
        }

aws_service = AWSService()
