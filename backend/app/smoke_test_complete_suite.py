import time
import uuid
import httpx

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)

def fetch_notifications(client, token):
    resp = client.get("/notifications/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    return resp.json()

def main():
    suffix = str(uuid.uuid4())[:8]
    patient_email = f"pat_{suffix}@test.com"
    donor_near_email = f"don_near_{suffix}@test.com"
    donor_far_email = f"don_far_{suffix}@test.com"
    donor_incompat_email = f"don_inc_{suffix}@test.com"
    bank_email = f"bank_{suffix}@test.com"
    coord_email = f"coord_{suffix}@test.com"
    password = "SecurePassword123"

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

    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        # ──────────────────────────────────────────────────────────────────────
        # 1. USER REGISTRATION & AUTHENTICATION
        # ──────────────────────────────────────────────────────────────────────
        print_section("1. User Registration & Login")
        
        users_to_register = [
            {"email": patient_email, "full_name": "Mumbai Patient", "role": "patient"},
            {"email": donor_near_email, "full_name": "Navi Mumbai Donor (Near)", "role": "donor"},
            {"email": donor_far_email, "full_name": "Pune Donor (Far)", "role": "donor"},
            {"email": donor_incompat_email, "full_name": "Mumbai Incompatible Donor", "role": "donor"},
            {"email": bank_email, "full_name": "Mumbai Blood Bank", "role": "blood_bank"},
            {"email": coord_email, "full_name": "Coordinator User", "role": "coordinator"},
        ]

        tokens = {}
        user_ids = {}

        for user in users_to_register:
            reg_resp = client.post("/auth/register", json={
                "email": user["email"],
                "password": password,
                "full_name": user["full_name"],
                "role": user["role"]
            })
            assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"
            reg_data = reg_resp.json()
            user_ids[user["email"]] = reg_data["id"]

            login_resp = client.post("/auth/login", json={
                "email": user["email"],
                "password": password
            })
            assert login_resp.status_code == 200
            tokens[user["email"]] = login_resp.json()["access_token"]
            print(f"Registered & Logged in {user['full_name']} ({user['role']})")

        # Set headers
        pat_headers = {"Authorization": f"Bearer {tokens[patient_email]}"}
        don_near_headers = {"Authorization": f"Bearer {tokens[donor_near_email]}"}
        don_far_headers = {"Authorization": f"Bearer {tokens[donor_far_email]}"}
        don_inc_headers = {"Authorization": f"Bearer {tokens[donor_incompat_email]}"}
        bank_headers = {"Authorization": f"Bearer {tokens[bank_email]}"}
        coord_headers = {"Authorization": f"Bearer {tokens[coord_email]}"}

        # ──────────────────────────────────────────────────────────────────────
        # 2. PROFILE CREATION WITH GEOLOCATION
        # ──────────────────────────────────────────────────────────────────────
        print_section("2. Creating Profiles (Geolocation)")

        # Patient: Mumbai (19.0760, 72.8777) - O+
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
        print("Mumbai Patient profile created successfully.")

        # Compatible Donor (Near): Navi Mumbai (19.0330, 73.0297) - O- (compatible with O+)
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

        # Compatible Donor (Far): Pune (18.5204, 73.8567) - O- (~120 Km away)
        don_far_prof = client.post("/donors/me", json={
            "blood_group": "O-",
            "age": 32,
            "weight": 82.0,
            "city": "Pune",
            "state": "Maharashtra",
            "latitude": 18.5204,
            "longitude": 73.8567
        }, headers=don_far_headers)
        assert don_far_prof.status_code == 201
        don_far_id = don_far_prof.json()["id"]
        print(f"Compatible Far Donor profile created. Donor ID: {don_far_id}")

        # Incompatible Donor (Near): Mumbai (19.0760, 72.8777) - AB+ (incompatible with O+)
        don_inc_prof = client.post("/donors/me", json={
            "blood_group": "AB+",
            "age": 27,
            "weight": 65.0,
            "city": "Mumbai",
            "state": "Maharashtra",
            "latitude": 19.0760,
            "longitude": 72.8777
        }, headers=don_inc_headers)
        assert don_inc_prof.status_code == 201
        print("Incompatible Near Donor profile created.")

        # Blood Bank Profile: Mumbai (19.0760, 72.8777)
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
        # 3. BLOOD BANK INVENTORY & QUALITY CONTROLS
        # ──────────────────────────────────────────────────────────────────────
        print_section("3. Inventory, Units and Lab Quality controls")

        # Set stock/inventory
        set_stock_resp = client.post("/blood-bank/inventory", json={
            "blood_group": "O-",
            "quantity_ml": 1000.0
        }, headers=bank_headers)
        assert set_stock_resp.status_code == 201
        inventory_id = set_stock_resp.json()["id"]
        print(f"Inventory set successfully (ID: {inventory_id}, Qty: 1000ml O-).")

        # Check-in a blood unit
        unit_checkin = client.post("/blood-bank/units/check-in", json={
            "inventory_id": inventory_id,
            "donor_id": don_near_id,
            "blood_group": "O-",
            "volume_ml": 450.0,
            "notes": "Healthy donor unit"
        }, headers=bank_headers)
        assert unit_checkin.status_code == 201
        unit_id = unit_checkin.json()["id"]
        print(f"Blood unit checked in successfully (ID: {unit_id}).")

        # Quality Update (Lab check-in approval)
        quality_update = client.patch(f"/blood-bank/units/{unit_id}/quality", json={
            "status": "available",
            "is_safe": True
        }, headers=bank_headers)
        assert quality_update.status_code == 200
        assert quality_update.json()["is_safe"] == True
        print("Blood unit quality validated (marked as safe/available).")

        # ──────────────────────────────────────────────────────────────────────
        # 4. VALIDATION REPORTS & PDF SECURITY GUARD
        # ──────────────────────────────────────────────────────────────────────
        print_section("4. Validation Reports & PDF Security Guard")

        # Submit lab report details
        report_resp = client.post(f"/blood-bank/units/{unit_id}/validation-report", json={
            "hemoglobin_g_dl": 14.5,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "pulse_bpm": 72,
            "status": "approved",
            "feedback_notes": "Perfect vitals",
            "improvement_recommendations": "Keep doing regular cardios"
        }, headers=bank_headers)
        assert report_resp.status_code == 201
        report_id = report_resp.json()["id"]
        print(f"Validation report submitted successfully (ID: {report_id}).")

        # Upload dummy PDF file
        pdf_data = b"%PDF-1.4 mock pdf validation report data"
        upload_resp = client.post(
            f"/blood-bank/validation-reports/{report_id}/pdf",
            files={"file": ("report.pdf", pdf_data, "application/pdf")},
            headers=bank_headers
        )
        assert upload_resp.status_code == 200
        print("PDF Lab report uploaded successfully by Blood Bank.")

        # Download PDF:
        # a) Authorized Donor (Near Donor who donated the unit) -> Should succeed
        dl_donor = client.get(f"/blood-bank/validation-reports/{report_id}/pdf", headers=don_near_headers)
        assert dl_donor.status_code == 200
        assert dl_donor.content == pdf_data
        print("Success: Authorized donor successfully downloaded PDF.")

        # b) Authorized Blood Bank -> Should succeed
        dl_bank = client.get(f"/blood-bank/validation-reports/{report_id}/pdf", headers=bank_headers)
        assert dl_bank.status_code == 200
        print("Success: Authorized Blood Bank successfully downloaded PDF.")

        # c) Unauthorized User (Incompatible Donor) -> Should be 403 Forbidden
        dl_fail = client.get(f"/blood-bank/validation-reports/{report_id}/pdf", headers=don_inc_headers)
        assert dl_fail.status_code == 403
        print("Success: Security Guard blocked unauthorized download attempt with 403.")

        # ──────────────────────────────────────────────────────────────────────
        # 5. NEAREST BLOOD BANK LOCATOR
        # ──────────────────────────────────────────────────────────────────────
        print_section("5. Nearest Blood Bank Locator")

        nearest = client.get("/blood-bank/nearest?latitude=19.0760&longitude=72.8777&limit=100", headers=pat_headers)
        assert nearest.status_code == 200
        nearest_banks = nearest.json()
        print("Nearest Blood Banks returned:")
        for nb in nearest_banks:
            print(nb)
        assert len(nearest_banks) > 0
        assert any(b["hospital_name"] == "Mumbai Central Blood Bank" for b in nearest_banks)
        assert any(b["distance_km"] == 0.0 for b in nearest_banks)
        print("Success: Found nearest blood bank Mumbai Central at 0.0 Km distance.")

        # ──────────────────────────────────────────────────────────────────────
        # 6. ML RANKING & GEOJSON MAP DATA
        # ──────────────────────────────────────────────────────────────────────
        print_section("6. ML Ranking & GeoJSON Map Data")

        # Create request first to use its ID
        req_for_ml = client.post("/requests/", json={
            "blood_group": "O+",
            "units_required": 1,
            "urgency": "medium"
        }, headers=pat_headers)
        assert req_for_ml.status_code == 201
        ml_req_id = req_for_ml.json()["id"]

        # Run ranker
        ml_rank = client.post("/ml/rank-donors", json={
            "request_id": ml_req_id,
            "limit": 1000
        }, headers=coord_headers)
        assert ml_rank.status_code == 200
        ranked_list = ml_rank.json()
        # Verify distance calculations
        near_ranked = next((rd for rd in ranked_list if rd["donor_id"] == don_near_id), None)
        assert near_ranked is not None
        assert abs(near_ranked["distance_km"] - 16.68) < 0.5
        print(f"Success: ML Ranking predicted near donor with exact distance {near_ranked['distance_km']} km (match prob: {near_ranked['match_probability']}).")

        # GeoJSON Map Export
        geojson = client.get("/ml/map-data", headers=coord_headers)
        assert geojson.status_code == 200
        assert geojson.json()["type"] == "FeatureCollection"
        print("Success: GeoJSON Coordinator Map feature collection exported successfully.")

        # ──────────────────────────────────────────────────────────────────────
        # 7. URGENT BROADCASTING (100 KM RADIUS FILTER & ACCEPTANCE LIMITS)
        # ──────────────────────────────────────────────────────────────────────
        print_section("7. Urgent Request (100 Km Radius Filter & Accepts)")

        # Create urgent critical request (O+, 2 units)
        urg_resp = client.post("/requests/", json={
            "blood_group": "O+",
            "units_required": 2,
            "urgency": "critical"
        }, headers=pat_headers)
        assert urg_resp.status_code == 201
        urg_req_id = urg_resp.json()["id"]
        print(f"Created critical urgent request (ID: {urg_req_id}).")

        time.sleep(1)

        # Check notifications for all actors
        notif_near = fetch_notifications(client, tokens[donor_near_email])
        notif_far = fetch_notifications(client, tokens[donor_far_email])
        notif_inc = fetch_notifications(client, tokens[donor_incompat_email])
        notif_bank = fetch_notifications(client, tokens[bank_email])

        # Assertions
        assert any("URGENT" in n["title"] for n in notif_near), "Near compatible donor missed urgent broadcast!"
        assert not any("URGENT" in n["title"] for n in notif_far), "Far compatible donor (>100 Km) received urgent broadcast!"
        assert not any("URGENT" in n["title"] for n in notif_inc), "Incompatible donor received urgent broadcast!"
        assert any("URGENT" in n["title"] for n in notif_bank), "Nearby blood bank missed urgent broadcast!"
        print("Success: Radius broadcast logic correctly filtered notifications (Near Donor/Bank got alerts, Far/Incompatible did not).")

        # Claim request checks
        # Far donor (Pune, >100 Km) accepts -> Should be rejected with 400 Bad Request
        accept_far = client.patch(f"/requests/{urg_req_id}/accept-open", headers=don_far_headers)
        assert accept_far.status_code == 400
        print("Success: Far donor acceptance rejected by radius filter.")

        # Near donor accepts -> Should succeed
        accept_near = client.patch(f"/requests/{urg_req_id}/accept-open", headers=don_near_headers)
        assert accept_near.status_code == 200
        assert accept_near.json()["status"] == "accepted"
        assert accept_near.json()["assigned_donor_id"] == don_near_id
        print("Success: Near compatible donor accepted request (status changed to accepted).")

        # ──────────────────────────────────────────────────────────────────────
        # 8. NON-URGENT CHECKS & FALLBACK SCHEDULING
        # ──────────────────────────────────────────────────────────────────────
        print_section("8. Non-Urgent Routing (Inventory Checks & ML Fallback)")

        # Case A: Inventory is available (We set O- inventory to 1000ml earlier)
        # Create medium request for O+ (O- matches O+ compatibility)
        print("Test Case A: Stock is available in local blood bank...")
        req_bank_stock = client.post("/requests/", json={
            "blood_group": "O+",
            "units_required": 1,
            "urgency": "medium"
        }, headers=pat_headers)
        assert req_bank_stock.status_code == 201
        print("Success: Non-urgent request created when stock exists.")

        # Verify patient notification alerts about available stock
        time.sleep(1)
        pat_notifs = fetch_notifications(client, tokens[patient_email])
        assert any("🏥 Blood Available" in n["title"] for n in pat_notifs), "Patient missed available blood bank stock alert!"
        print("Success: Patient received notification of available stock at nearby blood bank.")

        # Case B: Inventory is NOT available (let's request B- which has 0ml in stock)
        print("Test Case B: Stock is empty...")
        req_no_stock = client.post("/requests/", json={
            "blood_group": "B-",
            "units_required": 1,
            "urgency": "medium"
        }, headers=pat_headers)
        assert req_no_stock.status_code == 201
        no_stock_req_id = req_no_stock.json()["id"]
        print(f"Success: Non-urgent request B- created (ID: {no_stock_req_id}).")

        # Let the Blood Bank accept this request directly (Uber-style)
        bank_accept = client.patch(f"/requests/{no_stock_req_id}/accept-bank", headers=bank_headers)
        assert bank_accept.status_code == 200
        assert bank_accept.json()["status"] == "accepted"
        assert bank_accept.json()["assigned_blood_bank_id"] == user_ids[bank_email]
        print("Success: Blood Bank claimed the empty stock request successfully via accept-bank API.")

        print_section("ALL SYSTEM FUNCTIONAL TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
