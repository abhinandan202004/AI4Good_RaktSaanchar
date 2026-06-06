import json
import os
import logging
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)

class SnsService:
    @staticmethod
    def _get_tracker_path() -> str:
        # Create upload dir if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        return os.path.join(settings.UPLOAD_DIR, "sns_budget_tracker.json")

    @classmethod
    def get_spent_budget(cls) -> float:
        path = cls._get_tracker_path()
        if not os.path.exists(path):
            return 0.0
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return float(data.get("spent", 0.0))
        except Exception as e:
            logger.warning(f"Failed to read SNS budget tracker: {e}")
            return 0.0

    @classmethod
    def reset_tracker(cls):
        path = cls._get_tracker_path()
        try:
            with open(path, "w") as f:
                json.dump({"spent": 0.0}, f)
        except Exception as e:
            logger.warning(f"Failed to reset SNS budget tracker: {e}")

    @classmethod
    def _add_to_spent_budget(cls, amount: float):
        path = cls._get_tracker_path()
        spent = cls.get_spent_budget()
        spent += amount
        try:
            with open(path, "w") as f:
                json.dump({"spent": spent}, f)
        except Exception as e:
            logger.warning(f"Failed to write to SNS budget tracker: {e}")

    @classmethod
    def send_sns_notification(
        cls,
        phone: str = None,
        email: str = None,
        subject: str = "",
        message: str = "",
        sms_message: str = None,
        email_body: str = None
    ) -> bool:
        """
        Sends a notification using AWS (SMS and/or Email).
        Applies a cost-safeguard check.
        Returns True if sent (or logged under mock), False if blocked by budget.
        """
        if not settings.AWS_SNS_ENABLED:
            logger.info("AWS notifications are disabled in settings.")
            return True

        # Resolve SMS and email content
        sms_content = sms_message if sms_message is not None else message
        email_content = email_body if email_body is not None else message

        # 1. Budget safety check
        cost_per_sms = settings.AWS_SNS_ESTIMATED_COST_PER_SMS
        current_spent = cls.get_spent_budget()
        estimated_cost = 0.0
        if phone:
            estimated_cost += cost_per_sms
        if email:
            estimated_cost += 0.0001  # email is very cheap

        if current_spent + estimated_cost > settings.AWS_SNS_BUDGET_LIMIT:
            logger.warning(
                f"AWS dispatch BLOCKED. Current Spent: ${current_spent:.4f}, "
                f"Estimated Cost: ${estimated_cost:.4f}, Limit: ${settings.AWS_SNS_BUDGET_LIMIT:.2f}"
            )
            return False

        # 2. Decide if mock or live
        is_mock = (
            settings.AWS_ACCESS_KEY_ID in ("", "mock", "test")
            or settings.AWS_SECRET_ACCESS_KEY in ("", "mock", "test")
        )

        if is_mock:
            logger.info(
                f"[MOCK AWS DISPATCH] Phone: {phone}, Email: {email}\n"
                f"  SMS Content: '{sms_content}'\n"
                f"  Email Subject: '{subject}'\n"
                f"  Email Body: '{email_content}'"
            )
            cls._add_to_spent_budget(estimated_cost)
            return True

        # 3. Live AWS publish
        sent_any = False
        try:
            # Send Email via SES if provided
            if email:
                try:
                    ses_client = boto3.client(
                        "ses",
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_REGION
                    )
                    # Use custom sender or fallback
                    sender = getattr(settings, "AWS_SES_SENDER", "no-reply@raktsaanchar.org")
                    response = ses_client.send_email(
                        Source=sender,
                        Destination={"ToAddresses": [email]},
                        Message={
                            "Subject": {"Data": subject},
                            "Body": {"Text": {"Data": email_content}}
                        }
                    )
                    logger.info(f"SES Email sent to {email}. MessageId: {response.get('MessageId')}")
                    cls._add_to_spent_budget(0.0001)
                    sent_any = True
                except Exception as ses_err:
                    logger.warning(f"Failed to send SES email directly: {ses_err}. Trying SNS topic publish...")
                    if settings.AWS_SNS_TOPIC_ARN:
                        sns_client = boto3.client(
                            "sns",
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                            region_name=settings.AWS_REGION
                        )
                        response = sns_client.publish(
                            TopicArn=settings.AWS_SNS_TOPIC_ARN,
                            Subject=subject,
                            Message=f"To: {email}\n\n{email_content}"
                        )
                        logger.info(f"SNS Topic fallback sent for email. MessageId: {response.get('MessageId')}")
                        cls._add_to_spent_budget(0.0001)
                        sent_any = True

            # Send SMS via SNS if phone is provided
            if phone:
                sns_client = boto3.client(
                    "sns",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                response = sns_client.publish(
                    PhoneNumber=phone,
                    Message=sms_content
                )
                logger.info(f"SNS SMS sent to {phone}. MessageId: {response.get('MessageId')}")
                cls._add_to_spent_budget(cost_per_sms)
                sent_any = True

            if not sent_any:
                logger.info("AWS Dispatch skipped: No phone or email target provided.")
            return True
        except ClientError as e:
            logger.error(f"AWS publish ClientError: {e}")
            return False
        except Exception as e:
            logger.error(f"AWS publish unexpected error: {e}")
            return False
