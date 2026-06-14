import urllib.request
import urllib.parse
import json
import jwt
from datetime import datetime, timezone, timedelta

SECRET_KEY = "mock_secret_key_long_enough_32_chars_minimum"

# 1. Manually craft a token for User ID 6 (Patient)
payload = {
    "sub": "6",
    "role": "patient",
    "type": "access",
    "exp": datetime.now(timezone.utc) + timedelta(days=1)
}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"Crafted patient token: {token}")

# 1.5 Create Patient Profile
profile_payload = {
    "blood_group_required": "A+",
    "units_required": 2,
    "urgency": "high",
    "hospital_name": "Sion Hospital",
    "city": "Mumbai",
    "state": "Maharashtra",
    "latitude": 19.040,
    "longitude": 72.850
}

prof_data = json.dumps(profile_payload).encode("utf-8")
prof_req = urllib.request.Request(
    "http://localhost/api/v1/patients/me",
    data=prof_data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)
try:
    urllib.request.urlopen(prof_req)
    print("Patient Profile Created (or already exists)!")
except Exception as e:
    print(f"Profile creation returned: {e}")
    if hasattr(e, 'read'):
        print(e.read())

# 2. Create Blood Request
request_payload = {
    "blood_group": "A+",
    "urgency": "high",
    "units_required": 2,
    "patient_city": "Mumbai",
    "patient_latitude": 19.076,
    "patient_longitude": 72.877
}

req_data = json.dumps(request_payload).encode("utf-8")
post_req = urllib.request.Request(
    "http://localhost/api/v1/requests/",
    data=req_data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)

try:
    res = urllib.request.urlopen(post_req)
    print("Blood Request Created!")
    print(json.loads(res.read()))
except Exception as e:
    print(f"Failed to create Blood Request: {e}")
    if hasattr(e, 'read'):
        print(e.read())
