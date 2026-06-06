import time
import uuid
import httpx

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    print("\n" + "=" * 60)
    print(f" {title.upper()}")
    print("=" * 60)

def fetch_notifications(client, token):
    resp = client.get("/notifications/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    return resp.json()

def main():
    # Wait for API to be ready
    print("Waiting for API server on port 8000 to be ready...")
    for _ in range(15):
        try:
            r = httpx.get("http://localhost:8000/health")
            if r.status_code == 200:
                print("API is ready!")
                break
        except Exception:
            pass
        time.sleep(1)

    suffix = str(uuid.uuid4())[:8]
    patient_email = f"pat_{suffix}@test.com"
    donor_near_email = f"don_near_{suffix}@test.com"
    donor_far_email = f"don_far_{suffix}@test.com"
    donor_incompat_email = f"don_inc_{suffix}@test.com"
    bank_email = f"bank_{suffix}@test.com"
    password = "SecurePassword123"

    print(f"Generated user emails for Uber test run: {suffix}")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # ──────────────────────────────────────────────────────────────────────
        # 1. REGISTER USERS & CREATE PROFILES
        # ──────────────────────────────────────────────────────────────────────
        print_section("1. User Registration")
        
        users_to_register = [
            {"email": patient_email, "full_name": "Mumbai Patient", "role": "patient"},
            {"email": donor_near_email, "full_name": "Navi Mumbai Donor (Near)", "role": "donor"},
            {"email": donor_far_email, "full_name": "Pune Donor (Far)", "role": "donor"},
            {"email": donor_incompat_email, "full_name": "Mumbai Incompatible Donor", "role": "donor"},
            {"email": bank_email, "full_name": "Mumbai Blood Bank", "role": "blood_bank"},
        ]

        tokens = {}
        user_ids = {}

        for user in users_to_register:
            payload = {
                "email": user["email"],
                "password": password,
                "full_name": user["full_name"],
                "role": user["role"]
            }
            if user["role"] == "patient":
                payload["blood_group"] = "O+"
            reg_resp = client.post("/auth/register", json=payload)
            assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"
            reg_data = reg_resp.json()
            user_ids[user["email"]] = reg_data["id"]

            # Login
            login_resp = client.post("/auth/login", json={
                "email": user["email"],
                "password": password
            })
            assert login_resp.status_code == 200
            tokens[user["email"]] = login_resp.json()["access_token"]
            print(f"Registered & Logged in {user['full_name']} ({user['role']})")

        print_section("2. Creating Profiles & Setting Geolocation Coordinates")

        # Patient: Mumbai (19.0760, 72.8777) - Needs O+
        pat_headers = {"Authorization": f"Bearer {tokens[patient_email]}"}
        pat_prof = client.post("/patients/me", json={
            "blood_group_required": "O+",
            "units_required": 1,
            "urgency": "medium",
            "hospital_name": "Mumbai Central Hospital",
            "city": "Mumbai",
            "state": "Maharashtra",
            "latitude": 19.0760,
            "longitude": 72.8777
        }, headers=pat_headers)
        assert pat_prof.status_code == 201
        print("Mumbai Patient profile created.")

        # Compatible Donor 1 (Near): Navi Mumbai (19.0330, 73.0297) - Blood Group O- (compatible with O+)
        don_near_headers = {"Authorization": f"Bearer {tokens[donor_near_email]}"}
        don_near_prof = client.post("/donors/me", json={
            "blood_group": "O-",
            "age": 25,
            "weight": 70.0,
            "city": "Navi Mumbai",
            "state": "Maharashtra",
            "latitude": 19.0330,
            "longitude": 73.0297
        }, headers=don_near_headers)
        assert don_near_prof.status_code == 201
        don_near_id = don_near_prof.json()["id"]
        print(f"Compatible Near Donor profile created. Donor ID: {don_near_id}")

        # Compatible Donor 2 (Far): Pune (18.5204, 73.8567) - Blood Group O- (compatible but ~120 Km away)
        don_far_headers = {"Authorization": f"Bearer {tokens[donor_far_email]}"}
        don_far_prof = client.post("/donors/me", json={
            "blood_group": "O-",
            "age": 30,
            "weight": 80.0,
            "city": "Pune",
            "state": "Maharashtra",
            "latitude": 18.5204,
            "longitude": 73.8567
        }, headers=don_far_headers)
        assert don_far_prof.status_code == 201
        don_far_id = don_far_prof.json()["id"]
        print(f"Compatible Far Donor profile created. Donor ID: {don_far_id}")

        # Incompatible Donor 3 (Near but incompatible): Mumbai (19.0760, 72.8777) - Blood Group AB+ (cannot donate to O+)
        don_inc_headers = {"Authorization": f"Bearer {tokens[donor_incompat_email]}"}
        don_inc_prof = client.post("/donors/me", json={
            "blood_group": "AB+",
            "age": 28,
            "weight": 68.0,
            "city": "Mumbai",
            "state": "Maharashtra",
            "latitude": 19.0760,
            "longitude": 72.8777
        }, headers=don_inc_headers)
        assert don_inc_prof.status_code == 201
        print("Incompatible Donor profile created.")

        # Blood Bank: Mumbai (19.0760, 72.8777) - Distance 0 Km
        bank_headers = {"Authorization": f"Bearer {tokens[bank_email]}"}
        bank_prof = client.post("/blood-bank/profile", json={
            "hospital_name": "Mumbai Central Blood Bank",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "contact_phone": "022-9876543",
            "address": "Mumbai Central, Mumbai"
        }, headers=bank_headers)
        assert bank_prof.status_code == 201
        print("Blood Bank profile created.")

        # ──────────────────────────────────────────────────────────────────────
        # 3. URGENT BROADCAST VERIFICATION (CRITICAL URGENCY)
        # ──────────────────────────────────────────────────────────────────────
        print_section("3. Urgent Critical Request Broadcast (100 Km Radius Filter)")

        # Create critical blood request (O+, 1 unit)
        req_resp = client.post("/requests/", json={
            "blood_group": "O+",
            "units_required": 1,
            "urgency": "critical"
        }, headers=pat_headers)
        assert req_resp.status_code == 201
        urgent_req_id = req_resp.json()["id"]
        print(f"Urgent critical blood request created. Request ID: {urgent_req_id}")

        # Fetch notifications to verify broadcast logic
        print("Fetching notifications for all parties...")
        time.sleep(1) # wait for DB transaction commit and notification inserts

        near_notifs = fetch_notifications(client, tokens[donor_near_email])
        far_notifs = fetch_notifications(client, tokens[donor_far_email])
        inc_notifs = fetch_notifications(client, tokens[donor_incompat_email])
        bank_notifs = fetch_notifications(client, tokens[bank_email])

        # Assertions:
        # Near Donor (Navi Mumbai, O-, ~30 Km) -> Should have urgent alert
        assert any("URGENT" in n["title"] for n in near_notifs), "Near compatible donor did not receive urgent alert!"
        print("Success: Navi Mumbai donor (30 Km away) received the alert.")

        # Far Donor (Pune, O-, ~120 Km) -> Should NOT have urgent alert (outside 100 Km)
        assert not any("URGENT" in n["title"] for n in far_notifs), "Far compatible donor received alert but is >100 Km away!"
        print("Success: Pune donor (120 Km away) did not receive the alert.")

        # Incompatible Donor (Mumbai, AB+) -> Should NOT have urgent alert (not compatible)
        assert not any("URGENT" in n["title"] for n in inc_notifs), "Incompatible donor received alert!"
        print("Success: Incompatible donor did not receive the alert.")

        # Blood Bank (Mumbai, ~0 Km) -> Should have urgent alert
        assert any("URGENT" in n["title"] for n in bank_notifs), "Blood Bank did not receive urgent alert!"
        print("Success: Blood Bank (within 100 Km) received the alert.")

        # ──────────────────────────────────────────────────────────────────────
        # 4. UBER-STYLE ACCEPT-OPEN ENDPOINT FOR DONORS
        # ──────────────────────────────────────────────────────────────────────
        print_section("4. Uber-Style Acceptance Endpoint for Donors")

        # Let Pune donor (incompatible/far or incompatible group) try to accept -> should fail
        fail_accept_resp = client.patch(f"/requests/{urgent_req_id}/accept-open", headers=don_far_headers)
        assert fail_accept_resp.status_code == 400, f"Expected 400 for Pune donor accept, got {fail_accept_resp.status_code}"
        print("Success: Pune donor acceptance rejected due to incompatible blood group/distance restrictions.")

        # Let Navi Mumbai donor (compatible, near) accept the request
        accept_resp = client.patch(f"/requests/{urgent_req_id}/accept-open", headers=don_near_headers)
        assert accept_resp.status_code == 200, f"Accept failed: {accept_resp.text}"
        accepted_req = accept_resp.json()
        assert accepted_req["status"] == "accepted"
        assert accepted_req["assigned_donor_id"] == don_near_id
        print("Success: Navi Mumbai donor successfully accepted the request (status changed to accepted).")

        # Patient check notification
        pat_notifs = fetch_notifications(client, tokens[patient_email])
        assert any("Donor Accepted" in n["title"] for n in pat_notifs), "Patient did not receive Donor Accepted notification!"
        print("Success: Patient received notification of donor acceptance.")

        # ──────────────────────────────────────────────────────────────────────
        # 5. NON-URGENT INVENTORY MATCHING & UBER-STYLE ACCEPT-BANK
        # ──────────────────────────────────────────────────────────────────────
        print_section("5. Non-Urgent Request & Blood Bank Acceptance")

        # Update Blood Bank inventory to hold O- blood (500 ml)
        print("Crediting O- blood inventory for Mumbai Blood Bank...")
        inv_update = client.post("/blood-bank/inventory", json={
            "blood_group": "O-",
            "quantity_ml": 500.0
        }, headers=bank_headers)
        assert inv_update.status_code == 201
        print("Stock credited successfully.")

        # Let's create another pending request (O+, 1 unit, urgency = medium)
        req_resp2 = client.post("/requests/", json={
            "blood_group": "O+",
            "units_required": 1,
            "urgency": "medium"
        }, headers=pat_headers)
        assert req_resp2.status_code == 201
        medium_req_id = req_resp2.json()["id"]
        print(f"Created medium request. Request ID: {medium_req_id}")

        # Check that patient received "Blood Available" notification
        time.sleep(1)
        pat_notifs_avail = fetch_notifications(client, tokens[patient_email])
        assert any("Blood Available" in n["title"] for n in pat_notifs_avail), "Patient did not receive Blood Available notification!"
        print("Success: Patient received notification of available inventory in nearby blood bank.")

        # Let the Blood Bank accept this request directly (Uber-style)
        accept_bank_resp = client.patch(f"/requests/{medium_req_id}/accept-bank", headers=bank_headers)
        assert accept_bank_resp.status_code == 200, f"Accept bank failed: {accept_bank_resp.text}"
        accepted_req_bank = accept_bank_resp.json()
        assert accepted_req_bank["status"] == "accepted"
        assert accepted_req_bank["assigned_blood_bank_id"] == user_ids[bank_email]
        print("Success: Blood Bank successfully accepted the request (status changed to accepted, assigned_blood_bank_id set).")

        # Patient check notification
        pat_notifs2 = fetch_notifications(client, tokens[patient_email])
        assert any("Blood Bank Accepted" in n["title"] for n in pat_notifs2), "Patient did not receive Blood Bank Accepted notification!"
        print("Success: Patient received notification of Blood Bank acceptance.")

        print_section("ALL UBER BLOOD ROUTING & ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
