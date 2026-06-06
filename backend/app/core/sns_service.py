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
    def send_sns_notification(cls, phone: str = None, email: str = None, subject: str = "", message: str = "") -> bool:
        """
        Sends a notification using AWS SNS (SMS or Email).
        Applies a cost-safeguard check.
        Returns True if sent (or logged under mock), False if blocked by budget.
        """
        if not settings.AWS_SNS_ENABLED:
            logger.info("AWS SNS notifications are disabled in settings.")
            return True

        # 1. Budget safety check
        cost_per_sms = settings.AWS_SNS_ESTIMATED_COST_PER_SMS
        current_spent = cls.get_spent_budget()

        if current_spent + cost_per_sms > settings.AWS_SNS_BUDGET_LIMIT:
            logger.warning(
                f"SNS dispatch BLOCKED. Current Spent: ${current_spent:.4f}, "
                f"Estimated Cost: ${cost_per_sms:.4f}, Limit: ${settings.AWS_SNS_BUDGET_LIMIT:.2f}"
            )
            return False

        # 2. Decide if mock or live
        is_mock = (
            settings.AWS_ACCESS_KEY_ID in ("", "mock", "test")
            or settings.AWS_SECRET_ACCESS_KEY in ("", "mock", "test")
        )

        if is_mock:
            logger.info(
                f"[MOCK SNS DISPATCH] Phone: {phone}, Email: {email}, "
                f"Subject: '{subject}', Message: '{message}'"
            )
            cls._add_to_spent_budget(cost_per_sms)
            return True

        # 3. Live AWS publish
        try:
            sns_client = boto3.client(
                "sns",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            if phone:
                # Publish direct SMS
                response = sns_client.publish(
                    PhoneNumber=phone,
                    Message=f"{subject}\n{message}"
                )
                logger.info(f"SNS SMS sent to {phone}. MessageId: {response.get('MessageId')}")
                cls._add_to_spent_budget(cost_per_sms)
            elif settings.AWS_SNS_TOPIC_ARN:
                # Publish to a general SNS Topic
                response = sns_client.publish(
                    TopicArn=settings.AWS_SNS_TOPIC_ARN,
                    Subject=subject,
                    Message=message
                )
                logger.info(f"SNS Topic message sent. MessageId: {response.get('MessageId')}")
                cls._add_to_spent_budget(0.0001)  # topic mail is very cheap
            else:
                logger.info(f"SNS Dispatch skipped: No phone provided and no Topic ARN configured.")
            return True
        except ClientError as e:
            logger.error(f"AWS SNS publish ClientError: {e}")
            return False
        except Exception as e:
            logger.error(f"AWS SNS publish unexpected error: {e}")
            return False
