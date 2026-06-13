import httpx
import time

GATEWAY_URL = "http://localhost"

def test_gateway_routing():
    print("--- 1. Registering a new test user through API Gateway ---")
    email = f"test-donor-{int(time.time())}@example.com"
    register_data = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "E2E Microservice Tester",
        "role": "donor",
        "blood_group": "O+"
    }
    
    try:
        r_register = httpx.post(f"{GATEWAY_URL}/api/v1/auth/register", json=register_data, timeout=10.0)
        print(f"Register status: {r_register.status_code}")
        print(f"Register response: {r_register.text}")
        
        if r_register.status_code != 200:
            print("❌ Registration failed. Exiting.")
            return

        print("\n✅ Registration completed successfully!")
        print("👉 Next step: Check the logs of 'notification-service' to get the OTP code:")
        print("   docker compose logs notification-service")
        print("\nOnce you get the OTP code, verify the user with:")
        print(f"   curl -X POST {GATEWAY_URL}/api/v1/auth/verify -H \"Content-Type: application/json\" -d '{{\"email\": \"{email}\", \"code\": \"<OTP_CODE>\"}}'")
    except Exception as e:
        print(f"Connection to Gateway failed: {e}")

if __name__ == "__main__":
    test_gateway_routing()
