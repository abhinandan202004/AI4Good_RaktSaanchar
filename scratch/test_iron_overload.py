import urllib.request
import urllib.parse
import json
import jwt
from datetime import datetime, timezone, timedelta

SECRET_KEY = "mock_secret_key_long_enough_32_chars_minimum"

# Sample MRI Report Text
sample_report = """
MRI Iron Assessment:
Heart T2*: 14.5 ms
Liver T2*: 5.2 ms
Liver Iron Concentration: 8.3 mg/g
Ferritin: 2500
"""

# Helper to test endpoints
def test_endpoint(role, expected_status):
    payload = {
        "sub": "6" if role == "patient" else "5",
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    
    # Analyze text request
    url = f"http://localhost/api/v1/iron-overload/analyze/text?text={urllib.parse.quote(sample_report)}"
    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    
    print(f"Testing role: '{role}'...")
    try:
        res = urllib.request.urlopen(req)
        body = json.loads(res.read())
        print(f"Result (Status {res.status}):")
        print(json.dumps(body, indent=2))
        if expected_status == 200:
            print("[SUCCESS] Patient role allowed and returned correct results.")
        else:
            print("[FAILURE] Expected error status but succeeded.")
    except Exception as e:
        status_code = getattr(e, 'code', 500)
        print(f"Returned Status: {status_code}")
        if status_code == expected_status:
            print(f"[SUCCESS] Correctly blocked/returned error status {status_code}.")
            if hasattr(e, 'read'):
                print(f"Error detail: {e.read().decode()}")
        else:
            print(f"[FAILURE] Expected status {expected_status} but got {status_code}.")
            if hasattr(e, 'read'):
                print(f"Error detail: {e.read().decode()}")

# 1. Test Patient role (Should be allowed, status 200)
test_endpoint(role="patient", expected_status=200)

print("-" * 50)

# 2. Test Donor role (Should be blocked, status 403)
test_endpoint(role="donor", expected_status=403)
