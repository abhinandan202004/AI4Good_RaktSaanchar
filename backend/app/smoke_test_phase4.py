import time
import uuid
import httpx

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    print("\n" + "=" * 60)
    print(f" {title.upper()}")
    print("=" * 60)

def main():
    # 1. Generate unique email suffixes
    suffix = str(uuid.uuid4())[:8]
    coord_email = f"coord_{suffix}@test.com"
    bank_email = f"bank_{suffix}@test.com"
    donor_email = f"donor_{suffix}@test.com"
    patient_email = f"patient_{suffix}@test.com"
    password = "SecurePassword123"

    print(f"Generated user emails for test run: {suffix}")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # ──────────────────────────────────────────────────────────────────────
        # 1. REGISTRATION & LOGIN
        # ──────────────────────────────────────────────────────────────────────
        print_section("1. User Registration & Login")
        
        # Registration payloads
        users_to_register = [
            {"email": coord_email, "full_name": "Coordinator Alpha", "role": "coordinator"},
            {"email": bank_email, "full_name": "City Blood Bank", "role": "blood_bank"},
            {"email": donor_email, "full_name": "Jane Donor", "role": "donor"},
            {"email": patient_email, "full_name": "John Patient", "role": "patient"},
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
            if reg_resp.status_code != 201:
                print(f"Failed to register {user['email']}: {reg_resp.status_code} - {reg_resp.text}")
                return
            reg_data = reg_resp.json()
            user_ids[user["role"]] = reg_data["id"]
            print(f"Registered {user['role']} (ID: {reg_data['id']}) successfully.")

            # Login
            login_resp = client.post("/auth/login", json={
                "email": user["email"],
                "password": password
            })
            if login_resp.status_code != 200:
                print(f"Failed to login {user['email']}: {login_resp.status_code} - {login_resp.text}")
                return
            tokens[user["role"]] = login_resp.json()["access_token"]
            print(f"Logged in {user['role']} successfully. Token retrieved.")

        # ──────────────────────────────────────────────────────────────────────
        # 2. PROFILE CREATION
        # ──────────────────────────────────────────────────────────────────────
        print_section("2. Profile Creation")

        # Donor Profile
        donor_headers = {"Authorization": f"Bearer {tokens['donor']}"}
        donor_profile_resp = client.post("/donors/me", json={
            "blood_group": "A+",
            "age": 30,
            "weight": 70.0,
            "city": "Mumbai",
            "state": "Maharashtra"
        }, headers=donor_headers)
        
        if donor_profile_resp.status_code != 201:
            print(f"Failed to create Donor profile: {donor_profile_resp.status_code} - {donor_profile_resp.text}")
            return
        donor_id = donor_profile_resp.json()["id"]
        print(f"Donor profile created. Donor ID: {donor_id}")

        # Patient Profile
        patient_headers = {"Authorization": f"Bearer {tokens['patient']}"}
        patient_profile_resp = client.post("/patients/me", json={
            "blood_group_required": "A+",
            "units_required": 2,
            "urgency": "high",
            "hospital_name": "City General Hospital",
            "city": "Mumbai",
            "state": "Maharashtra"
        }, headers=patient_headers)

        if patient_profile_resp.status_code != 201:
            print(f"Failed to create Patient profile: {patient_profile_resp.status_code} - {patient_profile_resp.text}")
            return
        patient_id = patient_profile_resp.json()["id"]
        print(f"Patient profile created. Patient ID: {patient_id}")

        # ──────────────────────────────────────────────────────────────────────
        # 3. ML DONOR RANKING
        # ──────────────────────────────────────────────────────────────────────
        print_section("3. ML Donor Ranking")

        coord_headers = {"Authorization": f"Bearer {tokens['coordinator']}"}
        ml_resp = client.post("/ml/rank-donors", json={
            "patient_blood_group": "A+",
            "urgency": "high",
            "units_required": 2,
            "patient_city": "Mumbai",
            "limit": 1000
        }, headers=coord_headers)

        if ml_resp.status_code != 200:
            print(f"ML Donor Ranking endpoint failed: {ml_resp.status_code} - {ml_resp.text}")
            return
        
        ranked_donors = ml_resp.json()
        print(f"Ranked donors returned: {len(ranked_donors)}")
        for rank, r_donor in enumerate(ranked_donors, 1):
            print(f"  #{rank} Donor ID: {r_donor['donor_id']} | Match Prob: {r_donor['match_probability']:.4f} | Group Match: {r_donor['blood_group_match']} | Distance: {r_donor['distance_km']}km")
        
        # Verify our donor is in the list
        matched_donor = next((d for d in ranked_donors if d["donor_id"] == donor_id), None)
        if matched_donor:
            print(f"Success: Our donor {donor_id} is in the ranked list!")
        else:
            print(f"Warning: Our donor {donor_id} was not in the ranked list.")

        # ──────────────────────────────────────────────────────────────────────
        # 4. LEADERBOARD & BADGES (BEFORE DONATION)
        # ──────────────────────────────────────────────────────────────────────
        print_section("4. Leaderboard & Badges (Initial)")

        # List badges
        badges_resp = client.get("/leaderboard/badges")
        assert badges_resp.status_code == 200
        all_badges = badges_resp.json()
        print(f"Available badges in system:")
        for b in all_badges:
            print(f"  - {b['name']} ({b['icon_url']}): {b['description']} (Requires {b['required_donations']} donations)")

        # List my badges (Donor)
        my_badges_resp = client.get("/leaderboard/badges/me", headers=donor_headers)
        assert my_badges_resp.status_code == 200
        print(f"Jane Donor's initial badges: {my_badges_resp.json()}")

        # Get my rank (Donor)
        my_rank_resp = client.get("/leaderboard/me", headers=donor_headers)
        assert my_rank_resp.status_code == 200
        print(f"Jane Donor's initial rank: {my_rank_resp.json()}")

        # ──────────────────────────────────────────────────────────────────────
        # 5. BLOOD REQUEST CREATION & WORKFLOW
        # ──────────────────────────────────────────────────────────────────────
        print_section("5. Blood Request Flow & Chat Validation")

        # Patient creates request
        req_resp = client.post("/requests/", json={
            "blood_group": "A+",
            "units_required": 2,
            "urgency": "high"
        }, headers=patient_headers)
        
        if req_resp.status_code != 201:
            print(f"Failed to create blood request: {req_resp.status_code} - {req_resp.text}")
            return
        
        req_id = req_resp.json()["id"]
        print(f"Blood request created successfully. Request ID: {req_id}")

        # Coordinator assigns Donor
        assign_resp = client.patch(f"/requests/{req_id}/assign", json={
            "donor_id": donor_id,
            "note": "Assigned to test Phase 4 auto-chat wiring."
        }, headers=coord_headers)

        if assign_resp.status_code != 200:
            print(f"Failed to assign donor: {assign_resp.status_code} - {assign_resp.text}")
            return
        print(f"Coordinator assigned Donor {donor_id} to Request {req_id}.")

        # Donor accepts
        accept_resp = client.patch(f"/requests/{req_id}/accept", headers=donor_headers)
        if accept_resp.status_code != 200:
            print(f"Failed to accept request: {accept_resp.status_code} - {accept_resp.text}")
            return
        print(f"Donor accepted request. Status: {accept_resp.json()['status']}")

        # ──────────────────────────────────────────────────────────────────────
        # 6. VERIFY CHAT ROOM AUTO-CREATION
        # ──────────────────────────────────────────────────────────────────────
        print_section("6. Verify Chat Room Auto-Creation")
        
        # Get rooms as donor
        rooms_resp = client.get("/chat/rooms", headers=donor_headers)
        if rooms_resp.status_code != 200:
            print(f"Failed to fetch chat rooms: {rooms_resp.status_code} - {rooms_resp.text}")
            return
        
        rooms = rooms_resp.json()
        print(f"Donor chat rooms: {rooms}")
        
        active_room = next((r for r in rooms if r["donor_id"] == donor_id and r["patient_id"] == patient_id), None)
        if active_room:
            print(f"Success: Chat room auto-created successfully! Room ID: {active_room['id']}")
        else:
            print("ERROR: No chat room was auto-created after donor accepted.")
            return

        # ──────────────────────────────────────────────────────────────────────
        # 7. INVENTORY UPSERT & BLOOD UNIT CHECK-IN
        # ──────────────────────────────────────────────────────────────────────
        print_section("7. Blood Bank Check-In & QC")

        bank_headers = {"Authorization": f"Bearer {tokens['blood_bank']}"}
        
        # Set inventory stock
        inv_resp = client.post("/blood-bank/inventory", json={
            "blood_group": "A+",
            "quantity_ml": 500.0
        }, headers=bank_headers)
        
        if inv_resp.status_code != 201:
            print(f"Failed to upsert inventory: {inv_resp.status_code} - {inv_resp.text}")
            return
        inv_id = inv_resp.json()["id"]
        print(f"Inventory upserted. Inventory ID: {inv_id}, Quantity: {inv_resp.json()['quantity_ml']}ml")

        # Check-in unit
        checkin_resp = client.post("/blood-bank/units/check-in", json={
            "inventory_id": inv_id,
            "donor_id": donor_id,
            "blood_group": "A+",
            "volume_ml": 450.0,
            "notes": "Healthy donor unit"
        }, headers=bank_headers)

        if checkin_resp.status_code != 201:
            print(f"Failed to check-in unit: {checkin_resp.status_code} - {checkin_resp.text}")
            return
        unit_id = checkin_resp.json()["id"]
        print(f"Blood bag checked in. Unit ID: {unit_id}, is_safe: {checkin_resp.json()['is_safe']}, Status: {checkin_resp.json()['status']}")

        # QC Approval
        qc_resp = client.patch(f"/blood-bank/units/{unit_id}/quality", json={
            "is_safe": True,
            "notes": "Passed all QC screens"
        }, headers=bank_headers)
        
        if qc_resp.status_code != 200:
            print(f"Failed to update quality: {qc_resp.status_code} - {qc_resp.text}")
            return
        print(f"QC passed for Unit {unit_id}. is_safe: {qc_resp.json()['is_safe']}")

        # Dispatch unit
        dispatch_resp = client.patch(f"/blood-bank/units/{unit_id}/dispatch", json={
            "request_id": req_id
        }, headers=bank_headers)

        if dispatch_resp.status_code != 200:
            print(f"Failed to dispatch unit: {dispatch_resp.status_code} - {dispatch_resp.text}")
            return
        print(f"Unit {unit_id} dispatched. Unit status: {dispatch_resp.json()['status']}")

        # ──────────────────────────────────────────────────────────────────────
        # 8. FULFILMENT & BADGE AWARDING
        # ──────────────────────────────────────────────────────────────────────
        print_section("8. Request Fulfilment & Gamification Verification")

        fulfil_resp = client.patch(f"/requests/{req_id}/fulfil", headers=bank_headers)
        if fulfil_resp.status_code != 200:
            print(f"Failed to fulfil request: {fulfil_resp.status_code} - {fulfil_resp.text}")
            return
        print(f"Request marked fulfilled. Request status: {fulfil_resp.json()['status']}")

        # Now check if donor earned the "First Drop" badge!
        my_badges_after = client.get("/leaderboard/badges/me", headers=donor_headers)
        assert my_badges_after.status_code == 200
        earned_badges = my_badges_after.json()
        print(f"Jane Donor's badges after donation: {earned_badges}")
        
        first_drop = next((b for b in earned_badges if b["badge"]["name"] == "First Drop"), None)
        if first_drop:
            print(f"Success: 'First Drop' badge earned successfully!")
        else:
            print("ERROR: 'First Drop' badge was not awarded after fulfilling donation.")
            return

        # Check leaderboard again
        leaderboard_after = client.get("/leaderboard")
        assert leaderboard_after.status_code == 200
        print(f"Public Leaderboard after donation: {leaderboard_after.json()}")

        # Check donor's rank
        rank_after = client.get("/leaderboard/me", headers=donor_headers)
        assert rank_after.status_code == 200
        print(f"Jane Donor's rank after donation: {rank_after.json()}")

        # ──────────────────────────────────────────────────────────────────────
        # 9. REDIS SHORTAGE PUBLISH
        # ──────────────────────────────────────────────────────────────────────
        print_section("9. Redis Shortage Alert Publish")

        shortage_resp = client.post("/blood-bank/alerts/shortage", json={
            "blood_group": "A+",
            "message": "Critical A+ shortage in Mumbai region!"
        }, headers=bank_headers)

        if shortage_resp.status_code != 200:
            print(f"Failed to broadcast shortage alert: {shortage_resp.status_code} - {shortage_resp.text}")
            return
        
        print(f"Shortage alert response: {shortage_resp.json()}")
        print("Success: Shortage alert triggered successfully!")

        # ──────────────────────────────────────────────────────────────────────
        # 10. BLOOD VALIDATION REPORT & DONOR FEEDBACK
        # ──────────────────────────────────────────────────────────────────────
        print_section("10. Blood Validation Report & Health Feedback")

        # Check in a new unit to validate (with issues)
        checkin_issue_resp = client.post("/blood-bank/units/check-in", json={
            "inventory_id": inv_id,
            "donor_id": donor_id,
            "blood_group": "A+",
            "volume_ml": 450.0,
            "notes": "Validation test unit (will be rejected)"
        }, headers=bank_headers)

        assert checkin_issue_resp.status_code == 201
        issue_unit_id = checkin_issue_resp.json()["id"]
        print(f"Checked in new unit {issue_unit_id} for validation testing.")

        # Submit validation report (Blood Bank)
        report_payload = {
            "hemoglobin_g_dl": 11.2,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "pulse_bpm": 72,
            "status": "rejected",
            "issue_category": "low_hemoglobin",
            "feedback_notes": "Hemoglobin is 11.2 g/dL, which is below the safe threshold of 12.5 g/dL.",
            "improvement_recommendations": "Please increase your intake of iron-rich foods like spinach, beetroot, beans, and red meat. Pair with vitamin C. Wait at least 3 months before your next attempt."
        }

        report_resp = client.post(f"/blood-bank/units/{issue_unit_id}/validation-report", json=report_payload, headers=bank_headers)
        if report_resp.status_code != 201:
            print(f"Failed to submit validation report: {report_resp.status_code} - {report_resp.text}")
            return
        
        print("Submitted validation report. Report status: rejected, issue: low_hemoglobin.")

        # Verify unit status updated to quarantined and is_safe is False
        unit_after_resp = client.get(f"/blood-bank/units?inventory_id={inv_id}", headers=bank_headers)
        assert unit_after_resp.status_code == 200
        issue_unit = next((u for u in unit_after_resp.json() if u["id"] == issue_unit_id), None)
        assert issue_unit is not None
        print(f"Verified Unit {issue_unit_id} status: {issue_unit['status']} | is_safe: {issue_unit['is_safe']}")
        assert issue_unit["status"] == "quarantined"
        assert issue_unit["is_safe"] is False

        # Retrieve validation report as Blood Bank
        get_report_resp = client.get(f"/blood-bank/units/{issue_unit_id}/validation-report", headers=bank_headers)
        assert get_report_resp.status_code == 200
        print("Successfully retrieved validation report from Blood Bank endpoint.")

        # Log in as Donor and retrieve report & improvement recommendations
        donor_reports_resp = client.get("/donors/me/validation-reports", headers=donor_headers)
        if donor_reports_resp.status_code != 200:
            print(f"Donor failed to get validation reports: {donor_reports_resp.status_code} - {donor_reports_resp.text}")
            return
        
        donor_reports = donor_reports_resp.json()
        print(f"Donor validation reports retrieved: {len(donor_reports)}")
        assert len(donor_reports) >= 1
        
        latest_report = donor_reports[0]
        print(f"  Latest Report ID: {latest_report['id']} | Status: {latest_report['status']}")
        print(f"  Recommendations: {latest_report['improvement_recommendations']}")
        assert latest_report["status"] == "rejected"
        assert latest_report["issue_category"] == "low_hemoglobin"
        assert "spinach" in latest_report["improvement_recommendations"]

        # Fetch donor's notifications to verify alert was received
        notif_resp = client.get("/notifications/", headers=donor_headers)
        print(f"Notifications response status: {notif_resp.status_code}")
        print(f"Notifications response text: {notif_resp.text}")
        assert notif_resp.status_code == 200
        notifs = notif_resp.json()
        health_notif = next((n for n in notifs if "Donation Report & Action Items" in n["title"]), None)
        if health_notif:
            print(f"Success: Donor received health feedback notification! Title: {health_notif['title']}")
        else:
            print("ERROR: Donor did not receive health feedback notification.")
            return

        # ──────────────────────────────────────────────────────────────────────
        # 11. PDF UPLOAD & DOWNLOAD TESTING
        # ──────────────────────────────────────────────────────────────────────
        print_section("11. PDF Report Upload & Download (Security Guards)")

        report_id = latest_report["id"]
        pdf_content = b"%PDF-1.4 dummy pdf content for smoke testing validation reports"
        
        # Upload PDF (as Blood Bank)
        files = {"file": ("report.pdf", pdf_content, "application/pdf")}
        upload_resp = client.post(f"/blood-bank/validation-reports/{report_id}/pdf", files=files, headers=bank_headers)
        if upload_resp.status_code != 200:
            print(f"Failed to upload report PDF: {upload_resp.status_code} - {upload_resp.text}")
            return
        
        print(f"PDF uploaded successfully. Download URL: {upload_resp.json()['download_url']}")
        
        # Download PDF (as Donor)
        download_resp = client.get(f"/blood-bank/validation-reports/{report_id}/pdf", headers=donor_headers)
        if download_resp.status_code != 200:
            print(f"Donor failed to download PDF: {download_resp.status_code} - {download_resp.text}")
            return
        assert download_resp.content == pdf_content
        print("Success: Donor downloaded the correct PDF report.")

        # Download PDF (as Patient - unauthorized)
        unauth_resp = client.get(f"/blood-bank/validation-reports/{report_id}/pdf", headers=patient_headers)
        print(f"Unauthorized access check status: {unauth_resp.status_code}")
        assert unauth_resp.status_code == 403
        print("Success: Unauthorized access to report PDF was correctly blocked (403 Forbidden).")

        print_section("ALL TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
