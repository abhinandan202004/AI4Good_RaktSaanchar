import urllib.request
import urllib.parse
import json
import jwt
from datetime import datetime, timezone, timedelta

SECRET_KEY = "mock_secret_key_long_enough_32_chars_minimum"

payload = {
    "sub": "6",
    "role": "patient",
    "type": "access",
    "exp": datetime.now(timezone.utc) + timedelta(days=1)
}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"Patient Token: {token}")

# Fetch Notifications
notif_req = urllib.request.Request(
    "http://localhost/api/v1/notifications/",
    headers={
        "accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
)
try:
    res = urllib.request.urlopen(notif_req)
    print("Notifications:")
    print(json.loads(res.read()))
except Exception as e:
    print(f"Failed to fetch notifications: {e}")
    if hasattr(e, 'read'):
        print(e.read())
