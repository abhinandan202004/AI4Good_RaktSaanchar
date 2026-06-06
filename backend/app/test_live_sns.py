import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.sns_service import SnsService

# Force SNS Enabled
settings.AWS_SNS_ENABLED = True

print("================================================================================")
print(" LIVE AWS SNS SENDER TEST")
print("================================================================================")
print(f"AWS ACCESS KEY ID: {settings.AWS_ACCESS_KEY_ID[:6]}... (Length: {len(settings.AWS_ACCESS_KEY_ID)})")
print(f"AWS REGION       : {settings.AWS_REGION}")
print(f"BUDGET LIMIT     : ${settings.AWS_SNS_BUDGET_LIMIT:.2f}")

is_mock = (
    settings.AWS_ACCESS_KEY_ID in ("", "mock", "test")
    or settings.AWS_SECRET_ACCESS_KEY in ("", "mock", "test")
)
if is_mock:
    print("\n❌ WARNING: Your configuration is still in MOCK mode!")
    print("Please make sure you have updated the .env file with real keys.")
    sys.exit(1)

if len(sys.argv) < 2:
    print("\n❌ Error: Missing phone number argument.")
    print("Usage: python app/test_live_sns.py +[countrycode][number] (e.g. +919876543210)")
    sys.exit(1)

phone_number = sys.argv[1].strip()
if not phone_number.startswith("+"):
    print("❌ Error: Phone number must start with '+' followed by country code (e.g., +91 for India).")
    sys.exit(1)

print(f"\nSending live SMS to {phone_number}...")
success = SnsService.send_sns_notification(
    phone=phone_number,
    subject="RaktaSanchaar Live SMS",
    message="This is a live test message from the RaktaSanchaar platform. If you received this, your AWS SNS integration is fully functional!"
)

if success:
    print("✅ SMS publish call succeeded! Please check your phone for the message.")
else:
    print("❌ SMS publish call failed. Check your console logs or verify if your phone number is verified in the AWS SNS SMS Sandbox.")
