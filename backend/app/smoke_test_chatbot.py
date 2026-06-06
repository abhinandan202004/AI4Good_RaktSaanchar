import httpx
import uuid

BASE_URL = "http://backend:8000/api/v1"

def main():
    suffix = str(uuid.uuid4())[:8]
    donor_email = f"chat_donor_{suffix}@test.com"
    password = "SecurePassword123"

    print(f"Testing Chatbot Integration with user: {donor_email}")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Register Donor User
        reg_payload = {
            "email": donor_email,
            "password": password,
            "full_name": "Chatbot Tester",
            "role": "donor"
        }
        reg_resp = client.post("/auth/register", json=reg_payload)
        assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"
        user_id = reg_resp.json()["id"]
        print(f"Registered user with ID: {user_id}")

        # Login to get JWT
        login_resp = client.post("/auth/login", json={
            "email": donor_email,
            "password": password
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        print("Logged in successfully. Token retrieved.")

        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test basic chat message
        print("\nTest Case 1: Sending basic greeting...")
        chat_resp = client.post("/chat/", json={"message": "Hello! How can you help me?"}, headers=headers)
        print(f"Response status: {chat_resp.status_code}")
        print(f"Response JSON: {chat_resp.json()}")
        assert chat_resp.status_code == 200

        # 2. Test multilingual translation translation to English and back (Hindi)
        print("\nTest Case 2: Sending query in Hindi...")
        chat_resp_hi = client.post("/chat/", json={"message": "नमस्ते, रक्त दान करने के क्या फायदे हैं?"}, headers=headers)
        print(f"Response status: {chat_resp_hi.status_code}")
        print(f"Response JSON: {chat_resp_hi.json()}")
        assert chat_resp_hi.status_code == 200

        # 3. Test RAG response for medical/Thalassemia query
        print("\nTest Case 3: Sending medical query for RAG...")
        chat_resp_rag = client.post("/chat/", json={"message": "What is thalassemia?"}, headers=headers)
        print(f"Response status: {chat_resp_rag.status_code}")
        print(f"Response JSON: {chat_resp_rag.json()}")
        assert chat_resp_rag.status_code == 200

        # 4. Test platform adapter action routing
        print("\nTest Case 4: Requesting donor profile (Platform Action)...")
        chat_resp_plat = client.post("/chat/", json={"message": "Show me my donor profile details please"}, headers=headers)
        print(f"Response status: {chat_resp_plat.status_code}")
        print(f"Response JSON: {chat_resp_plat.json()}")
        assert chat_resp_plat.status_code == 200

        print("\nAll Chatbot tests passed successfully!")

if __name__ == "__main__":
    main()
