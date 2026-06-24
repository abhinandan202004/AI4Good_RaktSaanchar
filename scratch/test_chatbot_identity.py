import httpx
import time

GATEWAY_URL = "http://localhost"

def run_test():
    timestamp = int(time.time())
    email = f"chatbot-tester-{timestamp}@test.com"
    full_name = "Abhinandan Test"
    password = "SecurePassword123!"
    
    print(f"--- 1. Registering user {email} ---")
    register_data = {
        "email": email,
        "password": password,
        "full_name": full_name,
        "role": "donor",
        "blood_group": "O+"
    }
    
    r = httpx.post(f"{GATEWAY_URL}/api/v1/auth/register", json=register_data, timeout=10.0)
    print(f"Register status: {r.status_code}")
    if r.status_code != 200 and r.status_code != 201:
        print("Registration failed: " + r.text)
        return
        
    print(f"--- 2. Verifying user {email} with test OTP ---")
    verify_data = {
        "email": email,
        "code": "123456"
    }
    r = httpx.post(f"{GATEWAY_URL}/api/v1/auth/verify", json=verify_data, timeout=10.0)
    print(f"Verify status: {r.status_code}")
    if r.status_code != 200:
        print("Verification failed: " + r.text)
        return

    print("--- 3. Logging in ---")
    login_data = {
        "email": email,
        "password": password
    }
    r = httpx.post(f"{GATEWAY_URL}/api/v1/auth/login", json=login_data, timeout=10.0)
    print(f"Login status: {r.status_code}")
    if r.status_code != 200:
        print("Login failed: " + r.text)
        return
        
    token_info = r.json()
    access_token = token_info["access_token"]
    print("Success: Got JWT Access Token")

    print("--- 4. Querying Chatbot: 'What is my name' ---")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    chat_payload = {
        "message": "What is my name"
    }
    r = httpx.post(f"{GATEWAY_URL}/api/v1/chatbot/", json=chat_payload, headers=headers, timeout=15.0)
    print(f"Chatbot response status: {r.status_code}")
    if r.status_code != 200:
        print("Chatbot call failed: " + r.text)
        return
        
    response_data = r.json()
    print("Chatbot Response:")
    print("====================================")
    print(response_data["response"])
    print("====================================")
    
    if full_name.lower() in response_data["response"].lower():
        print("SUCCESS! The chatbot correctly identified the user's name!")
    else:
        print("FAILURE: The chatbot did not return the correct user name.")

if __name__ == "__main__":
    run_test()
